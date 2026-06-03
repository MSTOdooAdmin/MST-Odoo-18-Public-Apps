# -*- coding: utf-8 -*-

from odoo import models, fields


class ProjectTaskType(models.Model):
    _inherit = "project.task.type"

    is_default_stage = fields.Boolean(
        string="Default Stage",
        help="If enabled, this stage will be shown globally for tasks and can be used as a default project workflow stage.",
    )