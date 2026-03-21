# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_result(self):
        for aml in self:
            aml.result = 0.0
            aml.result = aml.amount_total_signed - aml.credit_amount 

    def _get_credit(self):
        for aml in self:
            aml.credit_amount = 0.0
            aml.credit_amount = aml.amount_total_signed - aml.amount_residual_signed

    def _get_credit_custom(self):
        payment = self.env['account.payment'].search([('partner_id', '=', self.id),('state', '=', 'posted'),('payment_type', '=', 'inbound')])
        total_haber = 0
        for x in payment:
            total_haber = total_haber + x.amount
            
    initial_carry_fwd_balance = fields.Boolean('Initial Carry Forward Balance')
    statement_type = fields.Selection([('customer','Customer'),('supplier','Supplier')], default='customer', string='Type')
    adjust_in_carry_fwd_bal = fields.Boolean(related="payment_id.adjust_in_carry_fwd_bal", string='Adjust in Carry Forward Balance', store=True, track_visibility=True)
    credit_amount = fields.Float(compute ='_get_credit',   string="Credit/paid")
    result = fields.Float(compute ='_get_result',   string="Balance") #'balance' field is not the same
    

    def js_assign_outstanding_line(self, line_id):
        ''' Overidden method
        Called by the 'payment' widget to reconcile a suggested journal item to the present
        invoice.

        :param line_id: The id of the line to reconcile with the current invoice.
        '''
        self.ensure_one()
        res = super(AccountMove, self).js_assign_outstanding_line(line_id)
        # Metro Code
        move_line_obj = self.env['account.move.line'].browse(line_id)
        if move_line_obj.reconciled:
            move_line_obj.payment_id.write({'adjust_in_carry_fwd_bal': False})
        # Ends
        return res