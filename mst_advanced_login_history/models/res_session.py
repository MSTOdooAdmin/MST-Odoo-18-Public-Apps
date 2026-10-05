# -*- coding: utf-8 -*-

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResSession(models.Model):
    _inherit = "res.session"

    def _revoke(self):
        """Keep custom login history aligned with Odoo 20 native session revocation."""
        session_identifiers = list(set(self.mapped("session_identifier")))
        user_ids = self.mapped("user_id").ids

        result = super()._revoke()

        if session_identifiers and user_ids:
            try:
                histories = self.env["login.history"].sudo().search([
                    ("user_id", "in", user_ids),
                    ("session_id", "in", session_identifiers),
                    ("status", "=", "active"),
                ])
                if histories:
                    histories.write({
                        "logout_time": fields.Datetime.now(),
                        "status": "logout",
                    })
            except Exception:
                _logger.exception("Unable to synchronize revoked sessions with login history")

        return result
