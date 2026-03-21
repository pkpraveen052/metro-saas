from odoo import models, _
from odoo.addons.crm_iap_lead_website.models import ir
from odoo.exceptions import UserError


class IrActionsActWindow(models.Model):
    _inherit = "ir.actions.act_window"

    def read(self, fields=None, load='_classic_read'):
        res = super(IrActionsActWindow, self).read(fields, load)

        user = self.env.user

        if user.has_group('metro_invoice_user.group_account_invoice_user'):

            restricted_actions = {
                'om_account_followup.action_om_account_followup_print',
                'om_account_followup.action_customer_followup',
                'om_account_followup.action_customer_my_followup',
                'om_account_followup.action_followup_stat',

            }

            for action in self:
                xmlid = action.get_external_id().get(action.id)
                if xmlid in restricted_actions:
                    return [{
                    'type': 'ir.actions.act_window',
                    'name': 'Feature Restricted',
                    'res_model': 'invoice.popup.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                }]


        return res
    
class IrActionsClient(models.Model):
    _inherit = "ir.actions.client"

    def read(self, fields=None, load='_classic_read'):
        res = super(IrActionsClient, self).read(fields, load)

        user = self.env.user

        if user.has_group('metro_invoice_user.group_account_invoice_user'):

            restricted_actions = {
                'ks_dynamic_financial_report.ks_df_tax_report_action',
                'ks_dynamic_financial_report.ks_dynamic_reports_bal_sheet_action',
                'ks_dynamic_financial_report.ks_df_rec_action',
                'ks_dynamic_financial_report.ks_df_pay_action',
                'ks_dynamic_financial_report.ks_df_cj_action',
                'ks_dynamic_financial_report.ks_df_es_action',
                'ks_dynamic_financial_report.ks_df_tb_action',
                'ks_dynamic_financial_report.ks_df_gl_action',
                'ks_dynamic_financial_report.ks_df_pl_action',
                'ks_dynamic_financial_report.ks_dynamic_reports_cash_flow_action',
                'ks_dynamic_financial_report.ks_pnl0',

            }

            for action in self:
                xmlid = action.get_external_id().get(action.id)
                if xmlid in restricted_actions:
                    return [{
                    'type': 'ir.actions.act_window',
                    'name': 'Feature Restricted',
                    'res_model': 'invoice.popup.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                }]


        return res

