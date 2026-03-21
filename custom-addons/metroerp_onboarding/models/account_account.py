from odoo import models,fields,_,api


class AccountAccount(models.Model):
    _inherit = "account.account"

    def action_save_onboarding_coa_step(self):
            self.env.company.sudo().set_onboarding_step_done('account_setup_coa_state')

    def action_skip_onboarding_coa_step(self):
        self.env.company.sudo().set_onboarding_step_done('account_setup_coa_state')
