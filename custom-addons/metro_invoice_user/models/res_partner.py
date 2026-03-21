from odoo import models,fields,api,_
from odoo.osv import expression

class ResPartnerInherit(models.Model):
    _inherit ="res.partner"

    total_invoiced = fields.Monetary(
            groups="account.group_account_invoice,account.group_account_readonly,metro_invoice_user.group_account_invoice_user,metro_invoice_user.group_invoice_own_only"
    )


    def _apply_salesperson_contact_filter(self, domain):
        user = self.env.user
        ctx = self._context

        # Superuser should see everything
        if user._is_superuser():
            return domain

        # Apply filter ONLY when opening Contacts menu
        if not ctx.get('from_contact_menu'):
            return domain

        # Apply only for Salesperson with "Own Documents Only"
        if user.has_group('sales_team.group_sale_salesman') \
        and not user.has_group('sales_team.group_sale_salesman_all_leads') \
        and not user.has_group('sales_team.group_sale_manager'):

            own_domain = ['|', ('user_id', '=', user.id), ('user_id', '=', False)]
            domain = expression.AND([domain, own_domain])

        return domain

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        args = self._apply_salesperson_contact_filter(args)
        return super()._search(args, offset, limit, order, count, access_rights_uid)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = self._apply_salesperson_contact_filter(domain)
        return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)