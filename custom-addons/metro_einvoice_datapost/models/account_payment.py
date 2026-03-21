# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError,UserError



class AccountPayment(models.Model):
    _inherit = "account.payment"

    pcp_outgoing_inv_doc_ref = fields.Many2one('pcp.outgoing.invoices', string="Document Ref(PCP)", copy=False)


    def _peppol_action_manual_send_payment(self):
        already_sent_moves = self.filtered(lambda m: m.outgoing_inv_doc_ref_c5)
        if already_sent_moves:
            names = ', '.join(already_sent_moves.mapped('name'))
            raise UserError(_(
                "The following Payments have already been sent:\n%s\n\n"
                "Please apply filters to choose the correct records."
            ) % names)
        message = 'Send %s payment to GST InvoiceNow' % len(self)
        return {
            'name': 'Send Payments',
            'type': 'ir.actions.act_window',
            'res_model': 'peppol.manual.send.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_message': message, 'active_ids': self.ids},
        }
