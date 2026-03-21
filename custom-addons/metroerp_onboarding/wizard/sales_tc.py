# -*- coding: utf-8 -*-

from odoo import fields, models, api,_


class SalesTermsCondition(models.TransientModel):
    _name = 'sales.terms.condition'
    _description = 'Sales Terms and Condition'

    sales_tc_custom = fields.Text(string="Sales Terms and Conditions")

    @api.model
    def default_get(self, default_fields):
        values = super(SalesTermsCondition, self).default_get(default_fields)
        values['sales_tc_custom'] = self.env.company.sales_tc
        return values

    def validate(self):
        self.env.company.sudo().set_onboarding_step_done('sale_onboarding_tc_state')
        resconfig_obj = self.env['res.config.settings']
        default_values_aa = resconfig_obj.default_get(list(resconfig_obj.fields_get()))
        default_values_aa.update({'sales_tc': self.sales_tc_custom})
        resconfig_obj.create(default_values_aa).execute()

    def action_skip_onboarding_sales_tc(self):
        self.env.company.sudo().set_onboarding_step_done('sale_onboarding_tc_state')
