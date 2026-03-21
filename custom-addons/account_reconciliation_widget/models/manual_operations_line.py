from odoo import _, fields, models, api
from odoo.exceptions import UserError


class ManualOperationsReconcileLine(models.Model):
    _name = "manual.operations.reconcile.line"
    _description = "Manual Operations Reconcile Line"

    # statement_line_id = fields.Many2one('account.bank.statement.line')
    account_id = fields.Many2one('account.account')
    name = fields.Char()
    amount = fields.Monetary()
    amount_str = fields.Char()
    account_code = fields.Char()
    currency_id = fields.Many2one('res.currency')
    partner_id = fields.Many2one('res.partner')
    bank_label = fields.Char('Label')