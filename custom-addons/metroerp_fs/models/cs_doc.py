# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import datetime
from datetime import datetime, date
import string


class CSDocument(models.Model):
    _name = 'cs.document'
    _rec_name = 'company_uen'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    company_id = fields.Many2one('res.company', string='Company', required=True, tracking=True)
    passed_on_date = fields.Date("Passed on", default=date.today(), tracking=True, required=True)
    company_uen = fields.Char(string='Company UEN', tracking=True, required=True)
    appointed_person = fields.Char("Appointed Person", tracking=True)
    effective_date = fields.Date('Effective Date', default=date.today(), tracking=True)
    prepared_by = fields.Char('Prepared By', default=lambda self: self.env.user.name, tracking=True)
    role = fields.Char('Role', default='Director', tracking=True)
    type_of_doc = fields.Char(default='DPO Document', string='Type of Doc')

    @api.onchange('company_uen')
    def onchange_uen(self):
        obj = self
        if obj.company_uen:
            cobj = self.env['res.company'].sudo().search([('l10n_sg_unique_entity_number','=',obj.company_uen)], limit=1)
            if cobj:
                obj.company_id = cobj.id
            else:
                obj.company_id = False

    def action_print_report(self):
        log = _("<b>Document downloaded successfully!</b>")
        self.message_post(body=log)
        return self.env.ref('metroerp_fs.ir_actions_report_metro_csdoc').report_action(self)

    def get_effective_date(self):
        def get_ordinal_suffix(day):
            if 11 <= day <= 13:
                return 'th'
            last_digit = day % 10
            if last_digit == 1:
                return 'st'
            elif last_digit == 2:
                return 'nd'
            elif last_digit == 3:
                return 'rd'
            else:
                return 'th'

        def get_date_string():
            now = self.effective_date
            day = now.day
            month = now.strftime("%B")
            year = now.year
            ordinal_suffix = get_ordinal_suffix(day)
            return f"{day}{ordinal_suffix} {month} {year}"

        formatted_date = get_date_string()

        return formatted_date

    def get_passedon_date(self):
        formatted_date = self.passed_on_date.strftime("%d/%m/%Y")
        return formatted_date

    def get_current_date(self):
        formatted_date = datetime.now().strftime("%d/%m/%Y")
        return formatted_date

    def get_company_address(self):
        address = ""
        if self.company_id.street:
            address += self.company_id.street + " "
        if self.company_id.street2:
            address += self.company_id.street2 + " "
        if self.company_id.city:
            address += self.company_id.city + " "
        if self.company_id.country_id:
            address += self.company_id.country_id.name + " "
        if self.company_id.zip:
            address += f"({self.company_id.zip})"
        return address

    def get_current_date1(self):
        def get_ordinal_suffix(day):
            if 11 <= day <= 13:
                return 'th'
            last_digit = day % 10
            if last_digit == 1:
                return 'st'
            elif last_digit == 2:
                return 'nd'
            elif last_digit == 3:
                return 'rd'
            else:
                return 'th'

        def get_current_date_string():
            now = datetime.now()
            day = now.day
            month = now.strftime("%B")
            year = now.year
            ordinal_suffix = get_ordinal_suffix(day)
            return f"{day}{ordinal_suffix} {month} {year}"

        current_date_string = get_current_date_string()
        return current_date_string
