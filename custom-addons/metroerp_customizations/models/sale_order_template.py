# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"


    @api.model
    def default_get(self, fields):
        defaults = super(SaleOrderTemplate, self).default_get(fields)
        # Access the current company
        current_company = self.env.company.id
        # Set the current company as the default company in the product category
        defaults['company_id'] = current_company
        return defaults
