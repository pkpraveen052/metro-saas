# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def create(self, vals):
        ''' Overidden to modify the OUtstandng Receipts & Payments account label name. '''
        journal = super(AccountJournal, self).create(vals)

        has_payment_accounts = vals.get('payment_debit_account_id') or vals.get('payment_credit_account_id')
        if has_payment_accounts:
            journal.payment_debit_account_id.write({'name': journal.payment_debit_account_id.name + ' - ' + vals['name']})
            journal.payment_credit_account_id.write({'name': journal.payment_credit_account_id.name + ' - ' + vals['name']})

        return journal
