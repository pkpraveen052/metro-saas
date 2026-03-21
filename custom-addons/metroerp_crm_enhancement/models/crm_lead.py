from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class CrmLeadCustom(models.Model):
    _inherit = 'crm.lead'

    @api.model
    def default_get(self, fields_list):
        res = super(CrmLeadCustom, self).default_get(fields_list)
        if 'stage_id' not in res:
            default_stage = self.env['crm.stage'].search([('name', '=', 'New')], limit=1)
            if default_stage:
                res['stage_id'] = default_stage.id
        return res