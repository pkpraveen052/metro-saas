# -*- coding: utf-8 -*-
from odoo import api, models, tools, fields, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    officer_id = fields.Many2one('res.company', string='Officer')
    # officer_type = fields.Selection(
    #     [('director', 'Director'), ('shareholder', 'Shareholder'), ('secretary', 'Secretary')], string='Officer Type',
    #     default='director')