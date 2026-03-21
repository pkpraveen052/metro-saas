from odoo import models, fields, api, _


class KsReportConfiguration(models.Model):
    _inherit = 'ks.report.configuration'

    def action_save_onboarding_layout_step(self):
        ctx = dict(self._context or {})
        if ctx.get('default_name', False) == 'Bill':
            self.env.company.sudo().set_onboarding_step_done('purchase_onboarding_bill_state')
        if self.name == 'Sales':
            self.env.company.sudo().set_onboarding_step_done('sale_onboarding_quotation_layout_state')
        if self.name == 'Picking Slip':
            self.env.company.sudo().set_onboarding_step_done('account_onboarding_delivery_layout_state')
        if self.name == 'Invoice':
            self.env.company.sudo().set_onboarding_step_done('account_setup_custom_invoice_layout')
        if self.name == 'Purchase RFQ':
            self.env.company.sudo().set_onboarding_step_done('purchase_onboarding_rfq_layout_state')
        if self.name == 'Purchase Order':
            self.env.company.sudo().set_onboarding_step_done('purchase_onboarding_po_layout_state')

    def action_skip_layout(self):
        ctx = dict(self._context or {})
        if ctx.get('default_name', False) == 'Bill':
            self.env.company.sudo().set_onboarding_step_done('purchase_onboarding_bill_state')
        if self.name == 'Sales':
            self.env.company.sudo().set_onboarding_step_done('sale_onboarding_quotation_layout_state')
        if self.name == 'Picking Slip':
            self.env.company.sudo().set_onboarding_step_done('account_onboarding_delivery_layout_state')
        if self.name == 'Invoice':
            self.env.company.sudo().set_onboarding_step_done('account_setup_custom_invoice_layout')
        if self.name == 'Purchase RFQ':
            self.env.company.sudo().set_onboarding_step_done('purchase_onboarding_rfq_layout_state')
        if self.name == 'Purchase Order':
            self.env.company.sudo().set_onboarding_step_done('purchase_onboarding_po_layout_state')
