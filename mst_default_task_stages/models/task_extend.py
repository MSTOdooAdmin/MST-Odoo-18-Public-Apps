# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError



class ProjectTask(models.Model):
    _inherit = "project.task"

    # Assignments / Master data


    stage_id = fields.Many2one(
        'project.task.type',
        string='Stage',
        domain="[('is_default_stage', '=', True)]",
        group_expand='_group_expand_stage_id',
        tracking=True,
        ondelete='restrict',
        default=lambda self: self._get_default_custom_stage()
    )

    @api.model
    def _get_default_custom_stage(self):
        return self.env['project.task.type'].search(
            [('is_default_stage', '=', True), ('active', '=', True)],
            order="sequence asc",
            limit=1
        )

    @api.model
    def _group_expand_stage_id(self, stages, domain):
        return self.env['project.task.type'].search(
            [
                ('is_default_stage', '=', True),
                ('active', '=', True)
            ],
            order="sequence asc"
        )

    @api.constrains('project_id')
    def _check_project_id(self):
        for record in self:
            if not record.project_id:
                raise ValidationError(_(
                    "You cannot create a task without selecting a Project. "
                    "Please select a Project."
                ))



