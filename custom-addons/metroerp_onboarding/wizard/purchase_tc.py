# -*- coding: utf-8 -*-

from odoo import fields, models, api,_


class PurchaseTermsConditions(models.TransientModel):
    _name = 'purchase.terms.conditions'
    _description = 'Purchase Terms and Conditions'

    purchase_tc_custom = fields.Text(string="Purchase Terms and Conditions")

    @api.model
    def default_get(self, default_fields):
        values = super(PurchaseTermsConditions, self).default_get(default_fields)
        values['purchase_tc_custom'] = self.env.company.purchase_tc
        return values

    def validate(self):
        self.env.company.sudo().set_onboarding_step_done('purchase_onboarding_tc_state')
        resconfig_obj = self.env['res.config.settings']
        default_values_aa = resconfig_obj.default_get(list(resconfig_obj.fields_get()))
        default_values_aa.update({'purchase_tc': self.purchase_tc_custom})
        resconfig_obj.create(default_values_aa).execute()

    def action_skip_onboarding_purchase_tc(self):
        self.env.company.sudo().set_onboarding_step_done('purchase_onboarding_tc_state')
