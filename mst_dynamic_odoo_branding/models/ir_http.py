from odoo import models
from odoo.http import request

URL_PREFIX_PARAM = "mst_dynamic_odoo_branding.url_prefix"
FAVICON_PARAM = "mst_dynamic_odoo_branding.favicon_attachment_id"


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def _mst_powered_by_text(self):
        """Shared footer text; never append the browser title automatically."""
        params = self.env['ir.config_parameter'].sudo()
        prefix = (params.get_param('mst_dynamic_odoo_branding.powered_by_prefix') or '').strip() or 'Powered by'
        name = (params.get_param('mst_dynamic_odoo_branding.powered_by_name') or '').strip()
        return f"{prefix} {name}" if name else prefix

    def _mst_favicon_attachment(self):
        """The uploaded branding favicon (public attachment), or an empty recordset."""
        attachment_id = self.env["ir.config_parameter"].sudo().get_param(FAVICON_PARAM)
        if not attachment_id or not str(attachment_id).isdigit():
            return self.env["ir.attachment"]
        return self.env["ir.attachment"].sudo().browse(int(attachment_id)).exists()

    def _mst_website_has_own_favicon(self, website):
        """True when the website's favicon was changed from Odoo's default icon."""
        if not website or "favicon" not in website._fields:
            return False
        favicon = website.sudo().favicon
        if not favicon:
            return False
        try:
            default = website._default_favicon()
        except Exception:  # noqa: BLE001 - never break page rendering for this check
            return True
        return favicon != default

    def _mst_favicon_url(self, website=None):
        """URL of the branding favicon to show, or False to keep Odoo's / the website's icon.

        A website with its own favicon keeps it (Settings shows a warning about it).
        """
        attachment = self._mst_favicon_attachment()
        if not attachment or self._mst_website_has_own_favicon(website):
            return False
        return "/web/content/%s?unique=%s" % (attachment.id, attachment.checksum or "")

    @classmethod
    def _serve_fallback(cls):
        """Serve /<prefix> and /<prefix>/... (the configured URL prefix).

        Only reached when no controller matched the URL, so the prefix can never
        hide a real page. The request is redirected to the matching /odoo URL
        (no database write on this read-only fallback); the browser then shows
        the URL with the prefix again (static/src/js/url_prefix.js).
        """
        prefix = request.env["ir.config_parameter"].sudo().get_param(URL_PREFIX_PARAM)
        path = request.httprequest.path
        if prefix and (path == f"/{prefix}" or path.startswith(f"/{prefix}/")):
            target = "/odoo" + path[len(prefix) + 1:]
            query = request.httprequest.query_string.decode()
            if query:
                target += "?" + query
            return request.redirect(target, code=302, local=True)
        return super()._serve_fallback()
