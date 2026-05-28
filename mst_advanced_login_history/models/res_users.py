import logging

from odoo import models
from odoo.exceptions import AccessDenied
from odoo.http import request


_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @classmethod
    def authenticate(cls, db, credential, user_agent_env):
        login = ''

        if isinstance(credential, dict):
            login = credential.get('login') or ''

        try:
            auth_info = super().authenticate(
                db,
                credential,
                user_agent_env
            )

        except AccessDenied:
            try:
                if request and request.env:
                    request.env['login.failed.history'].sudo().create_failed_login_record(
                        login=login,
                        reason='Invalid login credentials'
                    )
            except Exception as error:
                _logger.exception(
                    'Failed login tracking failed: %s',
                    error
                )

            raise

        try:
            uid = False

            if isinstance(auth_info, dict):
                uid = auth_info.get('uid')

            if uid and request and request.env:
                user = request.env['res.users'].sudo().browse(uid)

                if user.exists():
                    request.env['login.history'].sudo().create_login_record(user)

        except Exception as error:
            _logger.exception(
                'Login history tracking failed: %s',
                error
            )

        return auth_info