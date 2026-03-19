# -*- coding: utf-8 -*-
from odoo import fields, models

class UTMSource(models.Model):
    _inherit = "utm.source"

    lead_prefix = fields.Char(string="Lead Prefix",help="Prefix used for CRM Lead numbering (example: FB-, GG-)")
