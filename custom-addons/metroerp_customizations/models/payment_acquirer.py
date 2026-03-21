# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    module_to_buy = fields.Boolean(string='ERP Enterprise Module', related='module_id.to_buy', readonly=True, store=False)
    capture_manually = fields.Boolean(string="Capture Amount Manually",
        help="Capture the amount from ERP, when the delivery is completed.")
    payment_flow = fields.Selection(selection=[('form', 'Redirection to the acquirer website'),
        ('s2s','Payment from ERP')],
        default='form', required=True, string='Payment Flow',
        help="""Note: Subscriptions does not take this field in account, it uses server to server by default.""")