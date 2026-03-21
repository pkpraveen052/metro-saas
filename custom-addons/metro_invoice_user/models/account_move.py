from odoo import models,fields,api,_
from odoo.addons.account_edi_extended.models.account_move import AccountMove
from odoo.exceptions import AccessError,UserError
import logging
from odoo.osv import expression
from lxml import etree


_logger = logging.getLogger(__name__)

class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    invoice_outstanding_credits_debits_widget = fields.Text(
        groups="account.group_account_invoice,account.group_account_readonly,metro_invoice_user.group_account_invoice_user,metro_invoice_user.group_invoice_own_only")
    
    invoice_has_outstanding = fields.Boolean(
        groups="account.group_account_invoice,account.group_account_readonly,metro_invoice_user.group_account_invoice_user,metro_invoice_user.group_invoice_own_only",
    )
    
    invoice_payments_widget = fields.Text(
        groups="account.group_account_invoice,account.group_account_readonly,metro_invoice_user.group_account_invoice_user,metro_invoice_user.group_invoice_own_only",
    )
    invoice_has_matching_suspense_amount = fields.Boolean(
        groups="account.group_account_invoice,account.group_account_readonly,metro_invoice_user.group_account_invoice_user,metro_invoice_user.group_invoice_own_only",
    )

    # def _post(self, soft=True):
    #     print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Method called...")
    #     # Check if user has the custom group or default group access
    #     if self.env.user.has_group('metro_invoice_user.group_account_invoice_user') or self.env.user.has_group('account.group_account_invoice'):
    #         # Allow posting via elevated privileges (sudo) for these users
    #         return super(AccountMoveInherit, self.sudo())._post(soft=soft)
    #     else:
    #         # Fallback to original behavior for other users
    #         return super(AccountMoveInherit, self)._post(soft=soft)


    def action_invoice_print(self):
        """ Print the invoice and mark it as sent, 
            so that we can see more easily the next step of the workflow
        """
        if any(not move.is_invoice(include_receipts=True) for move in self):
            raise UserError(_("Only invoices could be printed."))

        self.filtered(lambda inv: not inv.is_move_sent).write({'is_move_sent': True})

        # Check if the user has either the default group or the custom group
        user = self.env.user
        if (
                user.has_group('account.group_account_invoice')
                or user.has_group('metro_invoice_user.group_account_invoice_user')
                or user.has_group('metro_invoice_user.group_invoice_own_only')
            ):
            return super(AccountMoveInherit, self).action_invoice_print()
        else:
            return self.env.ref('account.account_invoices_without_payment').report_action(self)


    def action_register_payment(self):
        if self.env.user.has_group('metro_invoice_user.group_invoice_own_only'):
            raise UserError(_("You are not allowed to register payments. Please contact your administrator."))
        return super().action_register_payment()



    def _apply_own_document_filter(self, domain):
        user = self.env.user

        if user._is_superuser():
            return domain

        if user.has_group('metro_invoice_user.group_invoice_own_only'):
            own_domain = [
                '&',
                ('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']),
                '|',
                    ('invoice_user_id', '=', user.id),
                    ('create_uid', '=', user.id),
            ]
            domain = expression.AND([domain, own_domain])

        return domain

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        args = self._apply_own_document_filter(args)
        return super()._search(args, offset, limit, order, count, access_rights_uid)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = self._apply_own_document_filter(domain)
        return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)


    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(AccountMoveInherit, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )

        user = self.env.user

        if view_type == 'form':
            if (
                user.has_group('sales_team.group_sale_salesman')
                and user.has_group('metro_invoice_user.group_invoice_own_only')
                and not user.has_group('sales_team.group_sale_salesman_all_leads')
                and not user.has_group('sales_team.group_sale_manager')
            ):

                doc = etree.XML(res['arch'])

                for node in doc.xpath("//field[@name='partner_id'] | //field[@name='partner_shipping_id']"):
                    node.set(
                        'domain',
                        "['|', ('user_id','=',uid), ('user_id','=',False), ('company_id','in',allowed_company_ids)]"
                    )


                res['arch'] = etree.tostring(doc, encoding='unicode')

        return res


    def show_invoice_feature_popup(self):

        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Feature Restricted',
                'res_model': 'invoice.popup.wizard',
                'view_mode': 'form',
                'target': 'new',
            }

    
    def preview_invoice(self):
        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user'):
            return self.show_invoice_feature_popup()

        return super().preview_invoice()


    def copy(self, default=None):
        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user'):
            raise UserError(_(
                "This feature is not available in the free InvoiceNow solution.\n\n"
                "To avail this function:\n"
                "WhatsApp: +65323242342\n"
                "Email: sales@metrogroup.solutions"
            ))

        return super().copy(default)
    


    
