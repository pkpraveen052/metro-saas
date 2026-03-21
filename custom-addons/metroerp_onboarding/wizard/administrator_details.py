# -*- coding: utf-8 -*-

from odoo import fields, models, api,_


class AdministratorDetails(models.TransientModel):
    _name = 'administrator.details'
    _description = 'Administrator Details'

    name = fields.Char(string='Name')
    phone_number = fields.Char(stirng='Phone Number')
    email = fields.Char(string='Email')
    company_id = fields.Many2one(comodel_name='res.company',string='Company ID')
    role = fields.Char(string='Role')

    @api.model
    def default_get(self, fields):
        defaults = super(AdministratorDetails, self).default_get(fields)
        # Access the current company
        current_company = self.env.company.id
        # Set the current company as the default company in the product category
        defaults['company_id'] = current_company
        return defaults

    def validate(self):
        self.company_id.sudo().set_onboarding_step_done('account_setup_admin_details_state')


