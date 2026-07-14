# -*- coding: utf-8 -*-
from odoo import models, fields


class AISearchHistory(models.Model):
    _name = "ai.search.history"
    _description = "AI Search History"
    _order = "create_date desc" 

    user_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        readonly=True,
    )
    query = fields.Text(required=True)
    model_name = fields.Char()
    provider_used = fields.Char(string="Provider")
    generated_domain = fields.Text()
    generated_groupby = fields.Text()
    explanation = fields.Text()
    status = fields.Selection(
        selection=[
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        default="success",
    )
    response = fields.Text()
