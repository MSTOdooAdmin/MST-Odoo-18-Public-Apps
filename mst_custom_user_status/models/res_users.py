# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)

# Bump this string every time this file changes. It's returned to the
# frontend and shown in the status-change toast, so a mismatch between
# what you expect and what's on screen immediately proves whether the
# server is actually running the latest code -- no log file needed.
SERVER_BUILD = "server-build-2026-07-06-idle-auto-away"


# Discuss's own presence icon component only recognizes a fixed, small
# set of native status values (online/away/offline/bot/im_partner) --
# anything else falls into its catch-all branch, which is exactly what
# was producing "No IM status available" for busy/meeting. Rather than
# guess at patching that private, version-specific OWL template (a wrong
# guess there risks breaking Discuss for everyone), each custom status is
# mapped onto the closest native value for how OTHER people see you in
# Discuss / avatars / kanban. Your own profile menu and the avatar-corner
# dot still show the exact, precise status either way.
NATIVE_IM_STATUS_MAP = {
    'away': 'away',
    'busy': 'away',      # Do Not Disturb -> shown as "Away" to others
    'meeting': 'away',   # In a Meeting -> shown as "Away" to others
    'offline': 'offline',
}


class ResUsers(models.Model):
    _inherit = 'res.users'

    custom_presence_status = fields.Selection(
        selection=[
            ('online', 'Online'),
            ('away', 'Away'),
            ('busy', 'Do Not Disturb'),
            ('meeting', 'In a Meeting'),
            ('offline', 'Offline'),
        ],
        string='Presence Status',
        default='online',
        help='Manually selected presence status shown in the user profile menu.',
    )

    def action_set_custom_presence_status(self, status):
        """RPC-callable method used by the frontend user-menu widget to
        change the current user's presence status.

        Always applies to the *currently logged in* user (self.env.user),
        regardless of which recordset it is called on, so a regular user
        without write access on res.users can still change their own
        status safely.

        Verifies the write actually persisted by reading it back directly
        from the database with raw SQL (bypassing the ORM cache
        entirely, so this check works the same regardless of Odoo point
        release) and raises a clear, visible error if it didn't --
        instead of silently keeping the old value.
        """
        allowed = dict(self._fields['custom_presence_status'].selection)
        if status not in allowed:
            raise UserError('Invalid presence status: %s' % status)

        user = self.env.user.sudo()
        _logger.info(
            'mst_custom_user_status: user %s (uid=%s) requesting status "%s"',
            user.login, user.id, status,
        )

        # sudo(): a normal user typically doesn't have write access on
        # res.users, but must always be able to set their own status.
        user.write({'custom_presence_status': status})

        # Odoo's ORM buffers write() in memory and only sends the actual
        # SQL UPDATE to the database at certain flush points -- it does
        # NOT happen the instant write() returns. The raw SQL read-back
        # below bypasses the ORM entirely, so without forcing a flush
        # first, it would read the database *before* this write had
        # actually been sent -- making a perfectly successful save look
        # like a failure. This one line was the real bug behind the
        # "keeps showing the previous status" error.
        self.env.flush_all()

        # Read back directly from the database with raw SQL -- bypassing
        # the ORM cache completely -- to be certain the value really
        # persisted. This intentionally avoids any ORM cache-invalidation
        # helper method whose name can differ between Odoo versions.
        self.env.cr.execute(
            "SELECT custom_presence_status FROM res_users WHERE id = %s",
            (user.id,),
        )
        row = self.env.cr.fetchone()
        actual = row[0] if row else None

        _logger.info(
            'mst_custom_user_status: after write, database actually has "%s" '
            'for uid=%s', actual, user.id,
        )

        if actual != status:
            raise UserError(
                'The presence status could not be saved (tried to set "%s" '
                'but the database still has "%s"). Check the Odoo server '
                'log for lines starting with "mst_custom_user_status:" around '
                'this time -- they show exactly what was attempted and '
                'what ended up stored. This pattern usually means either '
                'the module was not upgraded after this field was added, '
                'or another piece of code is overwriting this field.'
                % (status, actual)
            )

        # Commit immediately and independently of the rest of this HTTP
        # request. Without this, if anything ELSE on this same page load
        # (e.g. another widget's data fetch) raises an error later in the
        # same request, Odoo's transaction handling can roll back
        # everything in that transaction -- including this status write --
        # even though it looked successful a moment ago.
        self.env.cr.commit()

        user._broadcast_custom_presence_status()
        return {'status': actual, 'server_build': SERVER_BUILD}

    @api.model
    def get_presence_module_build(self):
        """Lets the frontend prove which server code is actually running,
        by comparing this against the client's own build tag -- the
        single fastest way to catch a "browser refreshed but server
        never restarted" deployment mismatch."""
        return SERVER_BUILD

    def _get_session_info(self):
        """Embed the current status directly into Odoo's session_info
        payload -- the data block already sent synchronously as part of
        the very first HTML response, before any JavaScript runs or any
        RPC call happens. This is what actually eliminates the "briefly
        shows Online on reload" symptom: previously the correct status
        was only known after an async RPC finished, which is a race by
        definition, however small. Now it's already present the instant
        the page starts rendering, so there's no window for a wrong
        value to be shown at all.
        """
        result = super()._get_session_info()
        result['custom_presence_status'] = self.env.user.custom_presence_status
        return result

    def _compute_im_status(self):
        """Extend the core presence computation (used everywhere Odoo
        shows a colored presence dot: avatars, kanban cards, list views,
        Discuss member lists and chat window headers) so a manually-set
        status overrides the automatic online/offline detection --
        but ONLY while the user is actually connected right now.

        super()._compute_im_status() already determined the real,
        activity-based status using Odoo's own heartbeat/presence
        tracking. If that says 'offline' (no active session -- e.g. the
        user logged out, or their browser tab has been closed/inactive
        long enough), that takes priority over whatever manual status
        they last picked. This is what makes "logged out -> shows
        Offline" work correctly, without needing to hook into the
        logout route directly.

        The value is passed through NATIVE_IM_STATUS_MAP so Discuss's
        own display only ever sees a value it actually understands.
        """
        super()._compute_im_status()
        for user in self:
            status = user.custom_presence_status
            if not status or status == 'online':
                continue
            if user.im_status == 'offline':
                # Not actually connected right now -- always show
                # Offline, regardless of the manually-picked status.
                continue
            user.im_status = NATIVE_IM_STATUS_MAP.get(status, status)

    def _broadcast_custom_presence_status(self):
        """Best-effort realtime push so other already-connected users see
        the change immediately without refreshing, using the same bus
        message shape Odoo's own presence system uses to update the
        colored dot live. If a given Odoo build/version uses a different
        internal message shape, this simply won't push live -- the
        status is still correct on next reload, since it's a real,
        persisted field.
        """
        for user in self:
            partner = user.partner_id
            try:
                self.env['bus.bus']._sendone(
                    partner,
                    'bus.bus/im_status_updated',
                    {'partner_id': partner.id, 'im_status': user.im_status},
                )
            except Exception:
                # Never let a best-effort live-update push break the
                # actual status change.
                pass

    @api.model
    def get_custom_presence_status(self):
        """Convenience method to fetch the current user's status in one call."""
        return self.env.user.custom_presence_status
