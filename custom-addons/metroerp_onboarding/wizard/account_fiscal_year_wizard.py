from odoo import models,api,fields
from datetime import date, datetime, time,timedelta
from dateutil.relativedelta import relativedelta
import calendar
from odoo.exceptions import ValidationError


class FinancialYearOpeningWizard(models.TransientModel):
    _inherit = 'account.financial.year.op'

    def action_skip_onboarding_fiscal_year(self):
        self.env.company.sudo().set_onboarding_step_done('account_setup_fy_data_state')

    def action_save_onboarding_fiscal_year(self):
        print("action_save_onboarding_fiscal_year() >>>>")
        print(self.company_id)
        fiscal_years = self.env['account.fiscal.year']
        fiscal_year_obj = fiscal_years.sudo().search([('company_id','=',self.env.company.id)], limit=1)

        def is_valid_end_day_of_february(year, day):            
            if calendar.isleap(year): # Check if it's a leap year
                return day <= 29
            else:
                return day <= 28

        if fiscal_year_obj:
            if self.opening_date.month <= int(self.fiscalyear_last_month) and self.opening_date.day < self.fiscalyear_last_day:
                if int(self.fiscalyear_last_month) == 2:
                    if not is_valid_end_day_of_february(self.opening_date.year, self.fiscalyear_last_day):
                        raise ValidationError("'Fiscal Year End Day' is not a valid day for the year: " + str(self.opening_date.year))
                date_to = date(self.opening_date.year, int(self.fiscalyear_last_month), self.fiscalyear_last_day)
            else:
                if int(self.fiscalyear_last_month) == 2:
                    if not is_valid_end_day_of_february(self.opening_date.year + 1, self.fiscalyear_last_day):
                        raise ValidationError("'Fiscal Year End Day' is not a valid day for the year: " + str(self.opening_date.year + 1))
                date_to = date(self.opening_date.year + 1, int(self.fiscalyear_last_month), self.fiscalyear_last_day)

            year_vals = {
                'name': self.opening_date.year,
                'date_from': self.opening_date,
                'date_to': date_to,
                'company_id': self.env.company.id,
            }
            print(year_vals)
            fiscal_year_obj.sudo().write(year_vals)
            fiscal_year_obj.generate_lines()
        else:
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
