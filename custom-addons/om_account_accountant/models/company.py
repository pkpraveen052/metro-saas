# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import api, fields, models, _
from datetime import datetime, timedelta

class ResCompany(models.Model):
    _inherit = 'res.company'

    def compute_fiscalyear_dates(self, current_date):
        print("\nINHERITED compute_fiscalyear_dates() >>>>> current_date =",current_date)
        """
        THIS IS AN OVERIDDEN METHOD FROM addons/account/model/company.py TO CALCULATE THE FISCAL YEAR DATES.

        When no fiscal year is configured, this method returns the calendar year.
        :param current_date: A datetime.date/datetime.datetime object.
        :return: A dictionary containing:
            * date_from
            * date_to
        """

        # If the current_date is found in the fiscal year model configuration, get those dates and return.
        fiscal_year_obj = self.env['account.fiscal.year'].sudo().search([('company_id','=',self.id),
('date_from','<=',current_date.strftime('%Y-%m-%d')),
('date_to','>=',current_date.strftime('%Y-%m-%d'))], limit=1)
        if fiscal_year_obj:
            return {'date_from': fiscal_year_obj.date_from,
                'date_to': fiscal_year_obj.date_to}

        # Else just return the calendar year dates which was written in the account/ module.
        return {'date_from': datetime(year=current_date.year, month=1, day=1).date(),
                'date_to': datetime(year=current_date.year, month=12, day=31).date()}


    @api.model
    def create(self, vals):
        obj = super(ResCompany, self).create(vals)
        current_year = datetime.now().year
        self.env['account.fiscal.year'].create({
            'name': current_year,
            'date_from': datetime(current_year, 1, 1),
            'date_to': datetime(current_year, 12, 31),
            'company_id': obj.id,            
            })
        return obj