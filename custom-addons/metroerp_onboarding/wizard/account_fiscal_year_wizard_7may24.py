from odoo import models,api,fields
from datetime import date, datetime, time,timedelta
from dateutil.relativedelta import relativedelta


class FinancialYearOpeningWizard(models.TransientModel):
    _inherit = 'account.financial.year.op'

    def action_skip_onboarding_fiscal_year(self):
        self.env.company.sudo().set_onboarding_step_done('account_setup_fy_data_state')

    def action_save_onboarding_fiscal_year(self):
        fiscal_years = self.env['account.fiscal.year']
        current_year = datetime.now().year
        start_date = self.opening_date
        end_date = date(current_year, int(self.fiscalyear_last_month), self.fiscalyear_last_day)
        year_vals = {
            'name': current_year,
            'date_from': start_date,
            'date_to': end_date,
            'company_id': self.env.company.id,
        }
        fiscal_years.sudo().create(year_vals)
        self.env.company.sudo().set_onboarding_step_done('account_setup_fy_data_state')
