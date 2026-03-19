from odoo import models, fields,api
from odoo.osv import expression
import logging

_logger = logging.getLogger(__name__)

class ProjectTaskType(models.Model):
    _inherit = "project.task.type"

    is_default_stage = fields.Boolean(
        string="Default Stage",
        help="If enabled, this stage will be available globally "
             "for all tasks (not project specific).",
    )




