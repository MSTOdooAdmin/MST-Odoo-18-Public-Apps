# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class CrmLead(models.Model):
    _inherit = "crm.lead"

    lead_sequence = fields.Char(string="Sequence",copy=False,readonly=True,index=True,tracking=True,)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("lead_sequence"):
                continue
            source_id = vals.get("source_id")
            if not source_id:
                continue
            source = self.env["utm.source"].browse(source_id)
            if not (source.lead_prefix or "").strip():
                continue
            seq_code = f"crm.lead.source.{source.id}"
            seq = self.env["ir.sequence"].sudo().search([("code", "=", seq_code)], limit=1)
            if not seq:
                seq = self.env["ir.sequence"].sudo().create({
                    "name": f"CRM Lead - {source.name}",
                    "code": seq_code,
                    "implementation": "standard",
                    "prefix": source.lead_prefix.strip(),
                    "padding": 5,
                    "number_next": 1,
                    "number_increment": 1,
                    "company_id": False,
                })
            else:
                if (seq.prefix or "") != source.lead_prefix.strip():
                    seq.sudo().write({"prefix": source.lead_prefix.strip()})
            vals["lead_sequence"] = self.env["ir.sequence"].next_by_code(seq_code) or False
        return super().create(vals_list)


