# -*- coding: utf-8 -*-
from odoo import models
from .res_users import NATIVE_IM_STATUS_MAP


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_im_status(self):
        """Discuss (chat header, member list, DM list) reads presence from
        res.partner.im_status, not from res.users.im_status directly.
        Without this override, setting a custom status on res.users has
        no visible effect in Discuss, even though the field is correctly
        saved -- which is exactly the mismatch this fixes.

        Uses the same NATIVE_IM_STATUS_MAP as res.users so Discuss (which
        only understands online/away/offline) never falls back to
        "No IM status available" for busy/meeting.

        Also mirrors res.users' "only while actually connected" rule:
        once Odoo's own real presence detection says this partner is
        offline (logged out / inactive), that takes priority over
        whatever manual status was last picked, so colleagues correctly
        see Offline instead of a stale Away/Do Not Disturb/In a Meeting.
        """
        super()._compute_im_status()
        for partner in self:
            # sudo(): a regular user must be able to see a colleague's
            # chosen status even without general access to res.users.
            user = partner.sudo().user_ids[:1]
            if not user or not user.custom_presence_status or user.custom_presence_status == 'online':
                continue
            if partner.im_status == 'offline':
                continue
            partner.im_status = NATIVE_IM_STATUS_MAP.get(
                user.custom_presence_status, user.custom_presence_status
            )