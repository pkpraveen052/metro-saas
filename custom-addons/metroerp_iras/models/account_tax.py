# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountTax(models.Model):
    _inherit = "account.tax"

    for_IRAS = fields.Boolean(string="For IRAS")
    iras_supplies_type = fields.Selection(
        [('standard', "Standard-rated Supplies"), ('zerorated', "Zerorated Supplies"), ('exempt', 'Exempt Supplies')],
        default='standard', string='IRAS Supplies Type')
