# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_marketplace_product = fields.Boolean('Sale in MarketPlace ?')

    @api.constrains('is_marketplace_product')
    def check_invoice_policy_marketplace(self):
        for obj in self:
            if obj.is_marketplace_product and obj.invoice_policy and obj.invoice_policy == 'delivery':
                raise ValidationError("Please select the 'Ordered quantities' for the Invoice Policy while this product is a Marketplace product. Go to Sales tab > Invoice Policy to change.")
