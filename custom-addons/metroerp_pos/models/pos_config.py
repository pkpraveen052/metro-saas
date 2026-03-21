# -*- coding: utf-8 -*-
from odoo import fields, models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'



    @api.onchange('company_id')
    def _get_default_pos_team(self):
        """Overidden method to set the crm_team_id as False by default."""
        self.crm_team_id = False

    @api.model
    def create(self, values):
        if not values.get('company_id', False):
            values['company_id'] = self.env.company.id

        IrSequence = self.env['ir.sequence'].sudo()
        if not IrSequence.search([('company_id','=',values.get('company_id')),('code','=','pos.session')]):
            val = {
                'name': "POS Session",
                'padding': 5,
                'prefix': "POS/",
                'code': "pos.session",
                'company_id': values.get('company_id'),
            }
            # force sequence_id field to new pos.order sequence
            IrSequence.create(val)

        return super(PosConfig, self).create(values)