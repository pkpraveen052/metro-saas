# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import api, fields, models, _
from datetime import datetime, timedelta
import calendar
from dateutil.relativedelta import relativedelta


class AccountFiscalYear(models.Model):
    _name = 'account.fiscal.year'
    _description = 'Fiscal Year'

    name = fields.Char(string='Fiscal Year', required=True, size=4) #Metro Code change
    date_from = fields.Date(string='Start Date', required=True,
        help='Start Date, included in the fiscal year.')
    date_to = fields.Date(string='End Date', required=True,
        help='Ending Date, included in the fiscal year.')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    line_ids = fields.One2many('account.fiscal.year.lines', 'parent_id', string="Quarters") #Metro Code change

                    
    def _cron_account_fiscal_year_create(self):
        """Cron Job method that creates a new fiscal year record. """
        current_date = datetime.now().date()

        def last_day_of_month(year, month):
            return calendar.monthrange(year, month)[1]

        for company in self.env['res.company'].sudo().search([]):
            fiscal_obj = self.sudo().search([
                ('company_id', '=', company.id),
                ('date_to', '<=', str(current_date))  # Fetch last closed or due FY
            ], order='date_to desc', limit=1)

            if fiscal_obj:
                next_month_start = (fiscal_obj.date_to + timedelta(days=32 - fiscal_obj.date_to.day)).replace(day=1)
                twelth_month_date = (next_month_start + relativedelta(months=11))
                last_day = last_day_of_month(twelth_month_date.year, twelth_month_date.month)
                last_day_date = datetime(twelth_month_date.year, twelth_month_date.month, last_day)

                # Check if new FY already exists to avoid duplicate creation
                already_exists = self.search([
                    ('company_id', '=', company.id),
                    ('date_from', '=', next_month_start)
                ])

                if not already_exists:
                    self.create({
                        'name': next_month_start.year,
                        'date_from': next_month_start,
                        'date_to': last_day_date,
                        'company_id': company.id
                    })

    @api.model
    def create(self, vals):
        res = super(AccountFiscalYear, self).create(vals)
        res.generate_lines()
        return res

    def write(self, vals):
        res = super(AccountFiscalYear, self).write(vals)
        if vals.get('date_from') or vals.get('date_to'):            
            for obj in self:
                obj.generate_lines()
        return res
        
    @api.constrains('name')
    def _check_name(self):
        if not self.name.isdigit():
            raise ValidationError(_('The Fiscal Year name can accept only numbers. Please enter appropriate year.'))

    @api.constrains('date_from', 'date_to', 'company_id')
    def _check_dates(self):
        '''
        Check interleaving between fiscal years.
        There are 3 cases to consider:

        s1   s2   e1   e2
        (    [----)----]

        s2   s1   e2   e1
        [----(----]    )

        s1   s2   e2   e1
        (    [----]    )
        '''
        for fy in self:
            # Starting date must be prior to the ending date
            date_from = fy.date_from
            date_to = fy.date_to
            if date_to < date_from:
                raise ValidationError(_('The ending date must not be prior to the starting date.'))
            domain = [
                ('id', '!=', fy.id),
                ('company_id', '=', fy.company_id.id),
                '|', '|',
                '&', ('date_from', '<=', fy.date_from), ('date_to', '>=', fy.date_from),
                '&', ('date_from', '<=', fy.date_to), ('date_to', '>=', fy.date_to),
                '&', ('date_from', '<=', fy.date_from), ('date_to', '>=', fy.date_to),
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(_('You can not have an overlap between two fiscal years, '
                                        'please correct the start and/or end dates of your fiscal years.'))

    def generate_lines(self):
        def generate_next_four_quarters(start_date):
            quarters = []
            current_date = start_date

            for _ in range(4):
                quarter_start = current_date.replace(day=1)
                next_month = quarter_start.month + 3 if quarter_start.month + 3 <= 12 else (quarter_start.month + 3) - 12
                next_year = quarter_start.year + 1 if quarter_start.month + 3 > 12 else quarter_start.year
                quarter_end = quarter_start.replace(month=next_month, year=next_year) - timedelta(days=1)
                quarters.append((quarter_start, quarter_end))
                current_date = quarter_end + timedelta(days=1)

            return quarters

        # Example usage:
        # given_date = datetime(2023, 4, 1)
        given_date = self.date_from
        next_quarters = generate_next_four_quarters(given_date)

        line_ids = [(5,)]
        for i, (quarter_start, quarter_end) in enumerate(next_quarters):
            line_ids.append((0,0,{'quarter': f"Q{i+1}", 'date_from':f"{quarter_start.strftime('%Y-%m-%d')}", 'date_to':f"{quarter_end.strftime('%Y-%m-%d')}"}))

        self.write({'line_ids': line_ids})

class AccountFiscalYearLines(models.Model):
    _name = 'account.fiscal.year.lines'

    parent_id = fields.Many2one('account.fiscal.year')
    quarter = fields.Selection([('Q1','Q1'),('Q2','Q2'),('Q3','Q3'),('Q4','Q4')], string="Quarter", required=True)
    date_from = fields.Date(string='Start Date', required=True,
        help='Start Date, included in this Quarter.')
    date_to = fields.Date(string='End Date', required=True,
        help='Ending Date, included in this Quarter.')