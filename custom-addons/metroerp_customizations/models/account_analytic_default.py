# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAnalyticDefault(models.Model):
    _inherit = "account.analytic.default"

    company_id = fields.Many2one('res.company', string='Company', ondelete='cascade', default=lambda self: self.env.company,
    	help="Select a company which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this company, it will automatically take this as an analytic account)")
