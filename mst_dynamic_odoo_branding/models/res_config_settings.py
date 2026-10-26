import base64
import binascii
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype

FAVICON_PARAM = "mst_dynamic_odoo_branding.favicon_attachment_id"
FAVICON_MAX_BYTES = 1024 * 1024
FAVICON_MIMETYPES = {"image/png", "image/x-icon", "image/vnd.microsoft.icon", "image/svg+xml",
                     "image/jpeg", "image/gif", "image/webp"}

SHOW_MANAGE_DB_PARAM = "mst_dynamic_odoo_branding.show_manage_databases"
URL_PREFIX_PARAM = "mst_dynamic_odoo_branding.url_prefix"
URL_PREFIX_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,39}$")
# Never allowed: Odoo's own client prefixes and common technical paths
RESERVED_URL_PREFIXES = {
    "odoo", "web", "scoped_app", "static", "api", "json", "jsonrpc", "xmlrpc",
    "websocket", "longpolling", "report", "mail", "auth", "login", "logout",
    "my", "portal", "website", "shop", "blog", "forum", "event", "slides",
}



class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mst_dynamic_brand_name = fields.Char(
        string="Dynamic Brand Name",
        config_parameter="mst_dynamic_odoo_branding.brand_name",
        default="MindSpark Technologies",
        help="Name used in the browser tab title.",
    )
    mst_powered_by_prefix = fields.Char(
        string="Powered By Text",
        config_parameter="mst_dynamic_odoo_branding.powered_by_prefix",
        default="Powered by",
        help="Replaces Powered by Odoo on the login page, the website footer and outgoing emails, "
             "Defaults to Powered by. The optional display name is appended to this text.",
    )
    mst_powered_by_name = fields.Char(
        string="Powered By Display Name",
        config_parameter="mst_dynamic_odoo_branding.powered_by_name",
        help="Optional name displayed after Powered By Text, e.g. MindSpark Technologies.",
    )
    mst_url_prefix = fields.Char(
        string="URL Prefix",
        config_parameter=URL_PREFIX_PARAM,
        help="Replaces /odoo in the backend URLs, e.g. 'mindspark' shows "
             "/mindspark/discuss instead of /odoo/discuss. Leave empty to keep /odoo.",
    )
    # Not a config_parameter field on purpose: Odoo deletes a boolean config
    # parameter when it is unticked, and every reader falls back to "True",
    # so the setting could never be switched off. It is stored explicitly as
    # "True"/"False" in get_values()/set_values() below.
    mst_show_manage_databases = fields.Boolean(
        string="Show Manage Databases",
        default=True,
        help="When enabled, the Manage Databases link is visible on Odoo login pages (standard and Website layouts). When disabled, the link is hidden.",
    )

    mst_favicon = fields.Binary(
        string="Favicon",
        help="Browser tab icon for the backend and login page (PNG, ICO, SVG, JPG, GIF or WebP, up to 1 MB). "
             "Also used on websites that still have Odoo's default favicon.",
    )
    mst_favicon_website_warning = fields.Char(compute="_compute_mst_favicon_website_warning")

    def _compute_mst_favicon_website_warning(self):
        """Websites with their own favicon keep it: name them so the admin knows."""
        names = []
        if "website" in self.env:
            ir_http = self.env["ir.http"]
            names = [w.name for w in self.env["website"].sudo().search([]) if ir_http._mst_website_has_own_favicon(w)]
        warning = ""
        if names:
            warning = _("These websites have their own favicon set in Website → Configuration → Settings, so they "
                        "keep it: %s. Your branding favicon is used in the backend, on the login page and on "
                        "websites without their own favicon.", ", ".join(names))
        for settings in self:
            settings.mst_favicon_website_warning = warning

    @api.model
    def get_values(self):
        res = super().get_values()
        value = self.env["ir.config_parameter"].sudo().get_param(SHOW_MANAGE_DB_PARAM, "True")
        res["mst_show_manage_databases"] = value == "True"
        res["mst_powered_by_prefix"] = (res.get("mst_powered_by_prefix") or "").strip() or "Powered by"
        favicon = self.env["ir.http"]._mst_favicon_attachment()
        res["mst_favicon"] = favicon.datas if favicon else False
        return res

    def _mst_save_favicon(self, value):
        """Store the favicon as one public attachment (the login page loads it without a session)."""
        params = self.env["ir.config_parameter"].sudo()
        current = self.env["ir.http"]._mst_favicon_attachment()
        if not value:
            if current:
                current.unlink()
            params.set_param(FAVICON_PARAM, False)
            return
        if current and current.datas == value:
            return  # unchanged: don't rewrite it on every Settings save
        try:
            raw = base64.b64decode(value, validate=False)
        except (binascii.Error, ValueError):
            raise UserError(_("The favicon file couldn't be read. Upload a PNG, ICO or SVG image."))
        if len(raw) > FAVICON_MAX_BYTES:
            raise UserError(_("The favicon is too large (maximum 1 MB). Use a small square image, e.g. 64 × 64 pixels."))
        mimetype = guess_mimetype(raw, default="application/octet-stream")
        if mimetype not in FAVICON_MIMETYPES:
            raise UserError(_("The favicon must be an image (PNG, ICO, SVG, JPG, GIF or WebP), not %s.", mimetype))
        vals = {"name": "branding_favicon", "datas": value, "mimetype": mimetype, "public": True,
                "res_model": False, "res_id": False}
        if current:
            current.write(vals)
        else:
            current = self.env["ir.attachment"].sudo().create(vals)
        params.set_param(FAVICON_PARAM, str(current.id))

    def _mst_check_url_prefix(self, prefix):
        """Return the normalised prefix, or raise if it cannot be used."""
        prefix = (prefix or "").strip().strip("/").lower()
        if not prefix:
            return False
        if not URL_PREFIX_RE.match(prefix):
            raise UserError(_(
                "The URL prefix \"%(prefix)s\" is not valid. Use 2 to 40 lowercase letters, "
                "digits, '-' or '_', starting with a letter or digit.", prefix=prefix,
            ))
        if prefix in RESERVED_URL_PREFIXES:
            raise UserError(_("\"%(prefix)s\" is reserved by Odoo and cannot be used as URL prefix.", prefix=prefix))
        # The prefix is served only when no other route matches, so refuse any
        # prefix that is the first part of an existing route (e.g. "calendar"
        # because of /calendar/view/<id>): those URLs would reach that route
        # instead of the web client.
        for rule in self.env["ir.http"].routing_map().iter_rules():
            first_part = rule.rule.lstrip("/").split("/", 1)[0]
            if first_part == prefix:
                raise UserError(_(
                    "\"/%(prefix)s\" is already used by an existing Odoo page or route (%(route)s). "
                    "Please choose another URL prefix.", prefix=prefix, route=rule.rule,
                ))
        return prefix

    def set_values(self):
        for settings in self:
            normalised = settings._mst_check_url_prefix(settings.mst_url_prefix)
            if normalised != settings.mst_url_prefix:
                settings.mst_url_prefix = normalised
        super().set_values()
        for settings in self:
            settings._mst_save_favicon(settings.mst_favicon)
        # Always store an explicit value so that "False" is kept instead of deleted
        self.env["ir.config_parameter"].sudo().set_param(
            SHOW_MANAGE_DB_PARAM,
            "True" if self.mst_show_manage_databases else "False",
        )
