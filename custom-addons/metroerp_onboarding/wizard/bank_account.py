from datetime import date, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SetupBarBankConfigWizard(models.TransientModel):
    _inherit = 'account.setup.bank.manual.config'

    def action_skip_bank_account(self):
        self.env.company.sudo().set_onboarding_step_done('account_setup_bank_data_state')

    # def validate(self):
    #     """ Called by the validation button of this wizard. Serves as an
    #     extension hook in account_bank_statement_import.
    #     """
    #     self.company_id.sudo().set_onboarding_step_done('account_setup_bank_data_state')
    #     self.env.company.sudo().action_close_account_dashboard_onboarding()
