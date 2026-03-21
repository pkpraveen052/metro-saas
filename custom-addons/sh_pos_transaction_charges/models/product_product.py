# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields

class ProductServiceCharge(models.Model):
    _inherit = 'product.template'

    sh_is_credit_card_charge = fields.Boolean(string='Use for Payment Methods Charge')
    