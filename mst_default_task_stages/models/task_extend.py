# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.osv import expression


class ProjectTask(models.Model):
    _inherit = "project.task"

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        """
        Show default task stages in kanban grouping.

        This is mainly required for My Tasks / Private Tasks,
        because Odoo normally groups them by personal_stage_type_id.
        """

        project_id = self.env.context.get("default_project_id")

        if self.env.context.get("active_model") == "project.project" and self.env.context.get("active_id"):
            project_id = self.env.context.get("active_id")

        if project_id:
            stage_domain = expression.OR([
                [("project_ids", "in", [project_id])],
                [("project_ids", "=", False)],
                [("is_default_stage", "=", True)],
            ])
        else:
            stage_domain = expression.OR([
                [("project_ids", "=", False)],
                [("is_default_stage", "=", True)],
            ])

        return self.env["project.task.type"].search(stage_domain, order=order or "sequence, id")


class ProjectProject(models.Model):
    _inherit = "project.project"

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)

        default_stages = self.env["project.task.type"].search(
            [("is_default_stage", "=", True)],
            order="sequence, id"
        )

        for project in projects:
            if default_stages:
                project.type_ids = [(4, stage.id) for stage in default_stages]

        return projects