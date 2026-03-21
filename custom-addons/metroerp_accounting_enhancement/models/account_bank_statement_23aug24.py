# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    def button_sync_statement_lines(self):
        for statement in self:
            if not statement.journal_id:
                raise UserError(_("Please select a journal for the bank statement."))

            outstanding_payment_account = statement.journal_id.payment_debit_account_id
            outstanding_receipt_account = statement.journal_id.payment_credit_account_id

            if not outstanding_payment_account or not outstanding_receipt_account:
                raise UserError(_("The journal must have both outstanding payment and receipt accounts set."))

            unreconciled_moves_outstanding_receipt = self.env['account.move.line'].search([
                ('account_id', 'in', [(outstanding_receipt_account.id),(outstanding_payment_account.id)]),
                ('reconciled', '=', False),
                ('date', '<=', statement.date)
            ])

            for move in unreconciled_moves_outstanding_receipt:
                payment_ref = " ".join(filter(None, [move.name, move.ref]))
                statement_line = self.env['account.bank.statement.line'].with_context(active_test=False).search([('name', '=', move.name), ('partner_id', '=', move.partner_id.id),
                                                                                 ('payment_ref','=',payment_ref)], limit=1)
                if statement_line:
                    statement_line.unlink()
                    self.env['account.bank.statement.line'].create({
                        'statement_id': statement.id,
                        'date': move.date,
                        'name': move.name,
                        'partner_id': move.partner_id.id,
                        'amount': move.debit - move.credit,
                        'payment_ref': " ".join(filter(None, [move.name, move.ref])),
                    })
                else:
                    self.env['account.bank.statement.line'].create({
                        'statement_id': statement.id,
                        'date': move.date,
                        'name': move.name,
                        'partner_id': move.partner_id.id,
                        'amount': move.debit - move.credit,
                        'payment_ref': " ".join(filter(None, [move.name, move.ref])),
                    })

            statement.message_post(body=_("Statement lines synced from journal entries."))
