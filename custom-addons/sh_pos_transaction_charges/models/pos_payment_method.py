# Part of Softhealer Technologies.

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    sh_pos_enable_transaction_cherge = fields.Boolean(string="Enable Transaction Charge ? ")
    sh_pos_transaction_charge = fields.Selection([('percentage','Percentage'), ('fixed', 'Fixed')], string="Select Charge Type", default="percentage")
    sh_pos_card_charge = fields.Float(string="Transaction Charge")

    @api.constrains('sh_pos_enable_transaction_cherge')
    def validate_pos_enable_transaction(self):
        if self.sh_pos_enable_transaction_cherge:
            if not self.env['product.product'].sudo().search([('company_id','=',self.company_id.id),('available_in_pos','=',True),('sh_is_credit_card_charge','=',True),('type','=','service')]):
                raise ValidationError("Please create a Product 'Transaction Charge' for the company %s by enabling the 'Use for credit card Charge' as True and 'Available in POS' as True and 'Type' as 'Service'" % (self.company_id.name))