from odoo import models,fields,api,_

class AccountJournal(models.Model):
    _inherit = "account.journal"

    show_on_dashboard_invoice_user = fields.Boolean(string="Show on Dashboard for Invoice Users",default=True)


    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        user = self.env.user
        ctx = self.env.context

        if (
            ctx.get('from_dashboard_menu') and
            (
                user.has_group('metro_invoice_user.group_account_invoice_user') or
                user.has_group('metro_invoice_user.group_invoice_own_only')
            )
        ):
            args = args + [
                ('type', 'in', ['sale', 'purchase']),
                ('show_on_dashboard_invoice_user', '=', True)
            ]

        return super().search(args, offset=offset, limit=limit, order=order, count=count)


    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        user = self.env.user
        ctx = self.env.context

        if (
            ctx.get('from_dashboard_menu') and
            (
                user.has_group('metro_invoice_user.group_account_invoice_user') or
                user.has_group('metro_invoice_user.group_invoice_own_only')
            )
        ):
            domain = domain + [
                ('type', 'in', ['sale', 'purchase']),
                ('show_on_dashboard_invoice_user', '=', True)
            ]

        return super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    

   
    def show_layout_invoice_user(self):
        view_id = self.env.ref('metroerp_onboarding.ks_report_configuration_form_custom_popup').id
        ks_report_id = self.env.ref('account.account_invoices').id
        ks_model_id = self.env.ref('account.model_account_move').id
        report_style_id = self.env.ref('ks_custom_report_layouts.ks_sale_styles_1').id
        record_id = self.env['ks.report.configuration'].search([('ks_report_id', '=', ks_report_id), ('company_id', '=', self.env.company.id), ('name', '=', 'Invoice')])
        return {'type': 'ir.actions.act_window',
                'name': _('Invoice Layout'),
                'res_model': 'ks.report.configuration',
                'target': 'new',
                'view_mode': 'form',
                'res_id': record_id.id,
                'views': [[view_id, 'form']],
                'context': {'default_ks_report_id': ks_report_id, 'default_ks_model_id': ks_model_id, 'default_name': 'Invoice', 'default_sale_report_style_id':report_style_id},
                }


   