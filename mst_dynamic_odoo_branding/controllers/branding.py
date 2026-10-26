from odoo import http
from odoo.http import request


class DynamicBrandingController(http.Controller):

    @http.route('/mst_dynamic_odoo_branding/config', type='jsonrpc', auth='user')
    def branding_config(self):
        params = request.env['ir.config_parameter'].sudo()
        brand_name = params.get_param(
            'mst_dynamic_odoo_branding.brand_name',
            default=request.env.company.name or 'Odoo',
        )
        powered_by_prefix = params.get_param(
            'mst_dynamic_odoo_branding.powered_by_prefix',
            default='Powered by',
        )
        show_manage_databases = params.get_param(
            'mst_dynamic_odoo_branding.show_manage_databases',
            default='True',
        ) == 'True'
        return {
            'brand_name': brand_name or request.env.company.name or 'Odoo',
            'powered_by_prefix': request.env['ir.http']._mst_powered_by_text(),
            'show_manage_databases': show_manage_databases,
        }
