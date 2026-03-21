# Part of Softhealer Technologies.

from odoo import models, fields

class PosConfig(models.Model):
    _inherit = 'pos.config'

    sh_pos_enable_transaction_cherge = fields.Boolean(string="Enable Transaction Charge ? ")
    sh_pos_transaction_charge = fields.Selection([('percentage','Percentage'), ('fixed', 'Fixed')], string="Select Charge Type", default="percentage")
    sh_pos_card_method_id = fields.Many2one('pos.payment.method', string="Transaction Charge Payment Method")
    sh_pos_card_charge = fields.Float(string="Transaction Charge")
