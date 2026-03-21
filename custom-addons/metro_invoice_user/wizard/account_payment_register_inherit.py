from odoo import models, fields, api, _

class AccountPaymentRegisterInherit(models.TransientModel):
    _inherit = 'account.payment.register'



    def show_invoice_feature_popup(self):

        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Feature Restricted',
                'res_model': 'invoice.popup.wizard',
                'view_mode': 'form',
                'target': 'new',
            }


    def action_create_payments(self):
        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user'):
            return self.show_invoice_feature_popup()

        return super().action_create_payments()
