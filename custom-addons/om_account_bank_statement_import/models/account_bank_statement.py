# -*- coding: utf-8 -*-
from dataclasses import fields

from odoo import fields, models, api, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Date
import base64


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    manual_reconciliation = fields.Boolean('Manual Reconciliation')
    manual_reconciliation_type = fields.Selection([
        ('single', 'Single Entry'),
        ('multiple', 'Multiple Entry'),
    ], string="Type", default='single')


    # def action_journal_entries(self):
    #     return {
    #         'name': _('Journal Entries'),
    #         'view_mode': 'tree,form',
    #         'res_model': 'account.move',
    #         'view_id': False,
    #         'type': 'ir.actions.act_window',
    #         'domain': [('statement_id', '=', self.id)],
    #         'context': {
    #             'journal_id': self.journal_id.id,
    #         }
    #     }

    @api.onchange('manual_reconciliation')
    def _onchange_manual_reconciliation(self):
        for rec in self:
            if rec.manual_reconciliation and not rec.line_ids:
                # Clean old manual reconciliation line if needed
                amount = rec.balance_end_real - rec.balance_start
                rec.line_ids += rec.env['account.bank.statement.line'].new({
                    'date': rec.date,
                    'payment_ref': rec.journal_id.name,
                    'amount': amount,
                })
            if not rec.manual_reconciliation and rec.line_ids:
                for line in rec.line_ids:
                    line.amount = 0.0

    @api.onchange('balance_end_real', 'balance_start', 'date')
    def _onchange_balance_end_real_update_amount(self):
        for rec in self:
            if rec.manual_reconciliation and rec.state in ['posted', 'confirm']:  # or use actual state values
                raise ValidationError(
                    "You cannot change the Starting & Ending Balance during this stage."
                    "Please reset to 'New' to make changes."
                )
            if rec.manual_reconciliation:
                # Find the reconciliation line
                for line in rec.line_ids:
                    if line:
                        amount = rec.balance_end_real - rec.balance_start
                        line.amount = amount
                        line.date = rec.date


    def action_confirm(self):
        print('self', self)

    # def button_validate(self):
    #     if self.manual_reconciliation_type == 'multiple':
    #         self._check_balance_end_real_same_as_computed()
    #         # new_bank_st_line = []
    #         for statement in self:
    #             for line in statement.line_ids:
    #                 print('\n\n\nline', line)
    #             # Find the generated account move from reconciliation (if any)
    #                 if len(line.move_id.line_ids) > 2:
    #                     bank_line = line.move_id.line_ids.filtered(
    #                         lambda l: l.account_id == statement.journal_id.default_account_id)
    #                     non_bank_lines = line.move_id.line_ids - bank_line
    #
    #                     # One split_line → one new statement + journal entry
    #                     for split_line in non_bank_lines:
    #                         print('\n\nsplit_line', split_line)
    #                         bank_debit = split_line.credit
    #                         bank_credit = split_line.debit
    #
    #                         # Create new journal entry (account.move)
    #                         new_move_vals = {
    #                             'journal_id': line.move_id.journal_id.id,
    #                             'date': Date.today(),
    #                             'ref': statement.name or '/',
    #                             'statement_id': statement.id,
    #                         }
    #                         new_move = self.env['account.move'].create(new_move_vals)
    #
    #                         # Create statement line linked to that move
    #                         bank_st_line = self.env['account.bank.statement.line'].create({
    #                             'statement_id': statement.id,
    #                             'date': Date.today(),
    #                             'payment_ref': new_move.journal_id.name,
    #                             'move_id': new_move.id,
    #                         })
    #                         # new_bank_st_line.append(bank_st_line)
    #                         if bank_st_line:
    #                             for new_inv_line in bank_st_line.move_id.line_ids:
    #                                 print('\n\nnew_inv_line11111', new_inv_line)
    #                                 if new_inv_line.account_id == bank_line.account_id:
    #                                     new_inv_line.write({
    #                                         'name': bank_line.name,
    #                                         'debit': bank_debit,
    #                                         'credit': bank_credit,
    #                                         'partner_id': bank_line.partner_id.id if bank_line.partner_id else False,
    #                                     })
    #                                 else:
    #                                     print('\n\nnew_inv_line22222', new_inv_line)
    #                                     new_inv_line.write({
    #                                         'name': split_line.name,
    #                                         'account_id': split_line.account_id.id,
    #                                         'debit': split_line.debit,
    #                                         'credit': split_line.credit,
    #                                         'partner_id': split_line.partner_id.id if split_line.partner_id else False,
    #                                     })
    #                         new_move.action_post()
    #                     line.unlink()
                        # bank_line = line.move_id.line_ids.filtered(
                        #         lambda l: l.account_id == statement.journal_id.default_account_id)
                        # non_bank_lines = line.move_id.line_ids - bank_line
                        # print('\n\nnon_bank_lines', non_bank_lines)
                        # for split_line in non_bank_lines:
                        #     bank_debit = split_line.credit
                        #     bank_credit = split_line.debit
                        #     new_move_vals = {
                        #         'journal_id': line.move_id.journal_id.id,
                        #         'date': Date.today(),
                        #         'ref': statement.name or '/',
                        #         'statement_id': statement.id,
                        #         'line_ids': [
                        #             (0, 0, {
                        #                 'name': split_line.name,
                        #                 'account_id': bank_line.account_id.id,
                        #                 'debit': bank_debit,
                        #                 'credit': bank_credit,
                        #                 'partner_id': split_line.partner_id.id if bank_line.partner_id else False,
                        #             }),
                        #             (0, 0, {
                        #                 'name': split_line.name,
                        #                 'account_id': split_line.account_id.id,
                        #                 'debit': split_line.debit,
                        #                 'credit': split_line.credit,
                        #                 'partner_id': split_line.partner_id.id if split_line.partner_id else False,
                        #             }),
                        #         ]
                        #     }

                            # if new_move:
                            #     new_move.line_ids = [
                            #         (0, 0, {
                            #             'name': bank_line.name,
                            #             'account_id': bank_line.account_id.id,
                            #             'debit': bank_debit,
                            #             'credit': bank_credit,
                            #             'partner_id': bank_line.partner_id.id if bank_line.partner_id else False,
                            #         }),
                            #         (0, 0, {
                            #             'name': split_line.name,
                            #             'account_id': split_line.account_id.id,
                            #             'debit': split_line.debit,
                            #             'credit': split_line.credit,
                            #             'partner_id': split_line.partner_id.id if split_line.partner_id else False,
                            #         }),
                            #     ]
                            # new_bank_line = new_move.line_ids.filtered(
                            #                 lambda l: l.account_id == new_move.journal_id.default_account_id
                            #             )
                            # amount = new_bank_line.debit - new_bank_line.credit
                            # print('\n\n\nnew_move', new_move)
                            #
                            # bank_st_line = self.env['account.bank.statement.line'].create({
                            #     'statement_id': statement.id,
                            #     'amount': amount,
                            #     'date': Date.today(),
                            #     'payment_ref': statement.journal_id.name,
                            #     # 'journal_id': statement.journal_id.id,
                            #     'move_id': new_move.id,
                            #     # 'account_id': new_bank_line.account_id.id,
                            # })
                            # # new_move.statement_line_id = bank_st_line.id
                            # new_move.action_post()
                            # print('\n\n\nnew_move_name', new_move.journal_id, new_move.name, new_move.line_ids, new_move.move_type)

                            # print('\n\nbnnk_st_line', bank_st_line)
                        # line.unlink()
            # moves = self.env['account.move'].search([('statement_id', '=', self.id), ('company_id', '=', self.company_id.id)])
            # print('\n\nmoves', moves)
            # if moves:
            #     for move in moves:
            #         new_bank_line = move.line_ids.filtered(
            #             lambda l: l.account_id == move.statement_id.journal_id.default_account_id
            #         )
            #         amount = new_bank_line.debit - new_bank_line.credit
            #         bank_st_line = self.env['account.bank.statement.line'].create({
            #             'statement_id': move.statement_id.id,
            #             'amount': amount,
            #             'date': Date.today(),
            #             'payment_ref': move.journal_id.name,
            #             # 'journal_id': statement.journal_id.id,
            #             'move_id': move.id,
            #             # 'account_id': new_bank_line.account_id.id,
            #         })
            #         print('\n\n\nbank_st_line', bank_st_line)
                        # line.move_id.button_cancel()
                        # line.move_id.unlink()