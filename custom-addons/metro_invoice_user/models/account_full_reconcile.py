from odoo import models,fields,api,_


class AccountFullReconcileInherit(models.Model):
    _inherit = "account.full.reconcile"
    _description = "Full Reconcile"

    name = fields.Char(string='Number', required=True, copy=False, default=lambda self: self.env['ir.sequence'].sudo().next_by_code('account.reconcile'))