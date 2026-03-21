# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAnalyticTag(models.Model):
    _inherit = 'account.analytic.tag'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.constrains('name', 'company_id')
    def _check_unique_name_within_company(self):
        for record in self:
            if self.search_count([('name', '=', record.name), ('company_id', '=', record.company_id.id)]) > 1:
                raise ValidationError('Tag name already exists !')