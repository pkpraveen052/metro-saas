# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    """
    Account move reversal wizard, it cancel an account move by reversing it.
    """
    _inherit = 'account.move.reversal'
    _description = 'Account Move Reversal'

    @api.model
    def default_get(self, fields):
        """
        Method overide for default refund_method when progressive invoice is true.
        """
        res = super(AccountMoveReversal, self).default_get(fields)
        move_ids = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.env['account.move']

        if any(move.state != "posted" for move in move_ids):
            raise UserError(_('You can only reverse posted moves.'))
        if 'company_id' in fields:
            res['company_id'] = move_ids.company_id.id or self.env.company.id
        if 'move_ids' in fields:
            res['move_ids'] = [(6, 0, move_ids.ids)]
        if 'refund_method' in fields:
            res['refund_method'] = (len(move_ids) > 1 or move_ids.move_type == 'entry') and 'cancel' or 'refund'
        if 'refund_method' in fields and self.env.context.get('is_progressive'):
            res['refund_method'] = 'cancel'
            res['is_progressive_invoice'] = True
        return res

    is_progressive_invoice = fields.Boolean('Is Progressive Invoice')

    def reverse_moves(self):
        self.ensure_one()
        # method override by progressive invoice ADD credit note
        for move in self.move_ids:
            if move.is_progressive_invoice:
                for line in move.invoice_line_ids:
                    if move.is_posted:
                        line.progressive_billing_qt_line_id.pending_claim_amount += line.price_total
                        line.progressive_billing_qt_line_id.old_progress = line.old_progress
                        line.progressive_billing_qt_line_id.is_paid = False
                        move.progressive_billing_qt_id.is_fully_paid = False
                        if line.progressive_billing_qt_line_id.claimed_total_without_tax > 0:
                            line.progressive_billing_qt_line_id.claimed_total_without_tax = line.progressive_billing_qt_line_id.claimed_total_without_tax - line.price_subtotal
        res = super(AccountMoveReversal, self).reverse_moves()
        return res