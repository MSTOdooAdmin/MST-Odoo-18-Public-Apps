# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models
from odoo.api import SUPERUSER_ID
from odoo.exceptions import AccessDenied, AccessError
from odoo.http import request
from odoo.addons.base.models.res_users import check_identity

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    login_history_count = fields.Integer(
        string="Login Logs",
        compute="_compute_security_audit_counts",
        groups="base.group_system",
    )
    activity_log_count = fields.Integer(
        string="Audit Logs",
        compute="_compute_security_audit_counts",
        groups="base.group_system",
    )
    active_session_count = fields.Integer(
        string="Active Odoo Sessions",
        compute="_compute_security_audit_counts",
        groups="base.group_system",
    )

    def _ensure_security_audit_admin(self):
        if not self.env.is_system():
            raise AccessError("Only administrators can manage security audit sessions.")

    def _compute_security_audit_counts(self):
        LoginHistory = self.env["login.history"].sudo()
        ActivityLog = self.env["mst.user.activity.log"].sudo()
        for user in self:
            user.login_history_count = LoginHistory.search_count([("user_id", "=", user.id)])
            user.activity_log_count = ActivityLog.search_count([("user_id", "=", user.id)])
            user.active_session_count = len(user.sudo().session_ids)

    def action_view_login_history(self):
        self.ensure_one()
        self._ensure_security_audit_admin()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "mst_advanced_login_history.action_login_history"
        )
        action["domain"] = [("user_id", "=", self.id)]
        action["context"] = {"default_user_id": self.id}
        return action

    def action_view_activity_logs(self):
        self.ensure_one()
        self._ensure_security_audit_admin()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "mst_advanced_login_history.action_mst_user_activity_log"
        )
        action["domain"] = [("user_id", "=", self.id)]
        return action

    def authenticate(self, credential, user_agent_env):
        """Record interactive password failures without committing Odoo's auth transaction."""
        login = credential.get("login", "") if isinstance(credential, dict) else ""
        is_interactive_password = bool(
            isinstance(credential, dict)
            and credential.get("type") == "password"
            and (user_agent_env or {}).get("interactive", True)
        )

        request_values = {}
        if is_interactive_password and request:
            failed_model = self.env["login.failed.history"]
            request_values.update(failed_model._get_request_details())
            request_values.update(failed_model._get_request_geo_location())
            request_values.update(failed_model._get_session_browser_location())

        try:
            return super().authenticate(credential, user_agent_env)
        except AccessDenied:
            if is_interactive_password:
                self._mst_create_failed_login_history(
                    login=login,
                    reason="Invalid login credentials",
                    request_values=request_values,
                )
            raise

    def _after_session_login(self):
        """Mark a successful login only after Odoo finishes MFA/passkey stages."""
        result = super()._after_session_login()
        try:
            if request and request.session and request.session.uid:
                user = self.sudo().browse(request.session.uid)
                if user.exists():
                    self.env["login.history"].sudo().mark_login_pending(user)
        except Exception:
            _logger.exception("Unable to mark successful login for audit registration")
        return result

    def _mst_create_failed_login_history(
        self,
        login="",
        reason="Invalid login credentials",
        request_values=None,
    ):
        """Persist failed login in a separate transaction.

        Authentication failures are rolled back by Odoo. A dedicated cursor keeps the
        audit entry without forcing a commit on the authentication transaction itself.
        """
        try:
            with self.env.registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env["login.failed.history"].create_failed_login_record_from_values(
                    login=login,
                    reason=reason,
                    request_values=request_values or {},
                )
                cr.commit()
        except Exception:
            _logger.exception("Failed login history tracking failed for login=%s", login)
        return True

    @check_identity
    def action_kill_all_sessions(self):
        """Revoke Odoo 20 sessions using the native session model.

        Odoo intentionally keeps the administrator's current session when the
        target user is the current user, matching the native "revoke devices"
        behavior. Other users have all their active sessions revoked.
        """
        self.ensure_one()
        self._ensure_security_audit_admin()
        sessions = self.env["res.session"].sudo().search([
            ("user_id", "=", self.id),
        ])
        sessions_to_revoke = sessions.filtered(lambda session: not session.is_current)
        session_count = len(sessions_to_revoke)

        if sessions_to_revoke:
            sessions_to_revoke._revoke()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Sessions Revoked",
                "message": (
                    f"{session_count} active session(s) revoked for {self.display_name}."
                    if session_count
                    else f"No revocable sessions found for {self.display_name}."
                ),
                "type": "success" if session_count else "info",
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }
