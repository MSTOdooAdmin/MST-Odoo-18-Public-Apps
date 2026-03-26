from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    delivery_challan_seal = fields.Binary("Delivery Challan Seal")
    delivery_challan_seal_name = fields.Char("Seal Filename")
    delivery_challan_sign = fields.Char("Delivery Challan Sign")