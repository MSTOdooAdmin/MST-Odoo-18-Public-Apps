import re

from markupsafe import Markup, escape

from odoo import api, models

POWERED_BY_PARAM = "mst_dynamic_odoo_branding.powered_by_prefix"
# "Powered by <a href="https://www.odoo.com?...">Odoo</a>" as written by Odoo's email
# layouts (mail_notification_layout / mail_notification_light) and by email
# templates of other modules (sign-up, password reset, portal invitations...).
POWERED_BY_ODOO_RE = re.compile(
    r"Powered\s+by\s*<a\b[^>]*\bhref=[\"'][^\"']*odoo\.com[^\"']*[\"'][^>]*>\s*"
    r"(?:Odoo|<img\b[^>]*\balt=[\"']Odoo[\"'][^>]*>)\s*</a>",
    re.IGNORECASE,
)


class MailMail(models.Model):
    _inherit = "mail.mail"

    @api.model
    def _mst_replace_powered_by(self, body):
        """Replace "Powered by Odoo" with the configured Powered By Text.

        Uses Powered by when no custom text is configured.
        """
        if not body or "odoo.com" not in str(body).lower():
            return body
        text = self.env["ir.http"]._mst_powered_by_text()
        replaced = POWERED_BY_ODOO_RE.sub(lambda _match: str(escape(text)), str(body))
        return Markup(replaced) if isinstance(body, Markup) else replaced

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("body_html"):
                vals["body_html"] = self._mst_replace_powered_by(vals["body_html"])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("body_html"):
            vals = dict(vals, body_html=self._mst_replace_powered_by(vals["body_html"]))
        return super().write(vals)
