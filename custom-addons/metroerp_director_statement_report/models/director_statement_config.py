# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class DirectorStatementConfig(models.Model):
    _name = 'director.statement.config'
    _rec_name = 'company_id'

    director_name1 = fields.Char('Director Name', required=True, tracking=True)
    director_name2 = fields.Char('Director Name 2', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    template_id = fields.Many2one('director.statement.template', string='Select Template', tracking=True)
    director_statement_opinion1 = fields.Text('Director statement opinion 1', required=True)
    director_statement_opinion2 = fields.Text('Director statement opinion 2', required=True)
    director_statement_arrangements = fields.Text('Director Statement Arrangement', required=True)
    director_statement_interests = fields.Text('Director Statement Interests', required=True)
    director_statement_share_options = fields.Text('Director Statement Share Options', required=True)
    director_ids = fields.One2many('config.director.names', 'config_id', string='Directors')

    @api.onchange('director_name1')
    def onchange_director_name(self):
        if self.director_name1:
            self.director_ids = [(5,),(0,0,{'name':self.director_name1})]





        
