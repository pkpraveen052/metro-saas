from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountInvoiceSend(models.TransientModel):
    _inherit = 'account.invoice.send'


    def show_invoice_feature_popup(self):

        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Feature Restricted',
                'res_model': 'invoice.popup.wizard',
                'view_mode': 'form',
                'target': 'new',
            }


    def send_and_print_action(self):
        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user'):
            return self.show_invoice_feature_popup()

        return super().send_and_print_action()