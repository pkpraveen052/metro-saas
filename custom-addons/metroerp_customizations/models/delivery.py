# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'delivery.carrier'

    company_id = fields.Many2one('res.company', string='Company',required=True, default=lambda self: self.env.company)
