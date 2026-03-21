# -*- coding: utf-8 -*-
from odoo import fields, models, _
import requests
from datetime import datetime


class PeppolIdentofierSearch(models.TransientModel):
    _name = 'peppol.api.search.wizard'
    _description = 'PEPPOL data Wizard'

    def _default_country(self):
        return self.env['res.country'].search([('code', '=', 'SG')], limit=1).id

    query_terms = fields.Char(string="Query")
    total_result_count = fields.Char(string="Total Result Count", readonly=True)
    result_page_count = fields.Char(string="Result Page Count", readonly=True)
    entity_line_ids = fields.One2many("peppol.api.search.wizard.lines", "entity_id", string="Entity", readonly=True)
    country = fields.Many2one('res.country', string='Country', default=_default_country)

    def action_search_api(self, view_id):
        """this method gives a popup list of mathces as per peppol API's response on search button."""
        if self.country:
            url = "https://directory.peppol.eu/search/1.0/json?q={}&country={}".format(self.query_terms,
                                                                                       self.country.code)
        else:
            url = "https://directory.peppol.eu/search/1.0/json?q={}".format(self.query_terms)
        entity_line_vals = []
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if not data.get('matches'):
                notification = {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Result'),
                        'message': "No records found",
                        'sticky': False,
                    }
                }
                return notification

            for match in data.get('matches'):
                line = (0, 0, {
                    'peppol_identifer': match.get('participantID').get('value').split(":")[-1],
                    'peppol_scheme': match.get('participantID').get('value').split(":")[0],
                    'peppol_super_scheme': match.get('participantID').get('scheme'),
                    'name': match.get('entities')[0].get('name')[0].get('name'),
                    'country_code': match.get('entities')[0].get('countryCode'),
                    'reg_date': datetime.strptime(match.get('entities')[0].get('regDate'), '%Y-%m-%d') if 'regDate' in match.get('entities')[0] else None,
                    'website': match.get('entities')[0].get('websites', [False])[0],
                    'create_bool': 1 if self.env['res.partner'].search(
                        [('name', '=', match.get('entities')[0].get('name')[0].get('name'))]) else 0,
                })
                entity_line_vals.append(line)
            search_vals = {
                'query_terms': self.query_terms,
                'total_result_count': data.get('total-result-count'),
                'result_page_count': data.get('result-page-count'),
                "entity_line_ids": entity_line_vals,
                "country": self.country.id
            }
            search_data_vals = self.create(search_vals)
            return {
                'name': self.sudo().env.ref(view_id).name,
                'view_mode': 'form',
                'view_id': self.sudo().env.ref(view_id).id,
                'res_model': 'peppol.api.search.wizard',
                'res_id': search_data_vals.id,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }

    def action_search_api_customer(self):
        return self.action_search_api('metro_einvoice_datapost.peppol_search_data_wizard_form_view_sales')

    def action_search_api_vendor(self):
        return self.action_search_api('metro_einvoice_datapost.peppol_search_data_wizard_form_view_puchases')


class PeppolIdentofierSearchLine(models.TransientModel):
    _name = 'peppol.api.search.wizard.lines'
    _description = 'PEPPOL data Wizard Lines'

    entity_id = fields.Many2one('peppol.api.search.wizard', string="Entity", readonly=True)
    peppol_identifer = fields.Char(string="Peppol Identifier", readonly=True)
    name = fields.Char(string="Name", readonly=True)
    country_code = fields.Char(string="Country", readonly=True)
    reg_date = fields.Date("Reg Date", readonly=True)
    peppol_scheme = fields.Char("Scheme", readonly=True)
    peppol_super_scheme = fields.Char("Super Scheme", readonly=True)
    website = fields.Char("Website")
    create_bool = fields.Boolean('Contact Created ?')

    def create_customer(self):
        """this method redirdcts to the customer creation page with default fields."""

        country_id = self.env['res.country'].search([('code', '=', self.country_code)])[0].id
        default_context = {'default_peppol_identifier': self.peppol_identifer,
                           'default_peppol_scheme': self.peppol_scheme,
                           'default_name': self.name, 'default_company_type': 'company',
                           'default_peppol_super_scheme': self.peppol_super_scheme,
                           'default_country_id': country_id, 'default_website': self.website,
                           'default_peppol_registered_date': self.reg_date,
                           'search_default_customer': 1, 'res_partner_search_mode': 'customer',
                           'default_is_company': True, 'default_customer_rank': 1,
                           'default_company_id': self.env.company.id}
        if self.country_code and self.country_code == "SG":
            default_context['default_l10n_sg_unique_entity_number'] = self.peppol_identifer.split("sguen", 1)[-1]

        return {
            'name': 'Customer Creation',
            'view_type': 'form',
            'view_mode': 'form',
            # 'target': 'new',
            'res_model': 'res.partner',
            'type': 'ir.actions.act_window',
            'context': default_context,
        }

    def create_vendor(self):
        """this method redirects to the customer creation page with default fields."""

        country_id = self.env['res.country'].search([('code', '=', self.country_code)])[0].id
        default_context = {'default_peppol_identifier': self.peppol_identifer,
                           'default_peppol_scheme': self.peppol_scheme,
                           'default_name': self.name, 'default_company_type': 'company',
                           'default_peppol_super_scheme': self.peppol_super_scheme,
                           'default_country_id': country_id, 'default_website': self.website,
                           'default_peppol_registered_date': self.reg_date,
                           'search_default_supplier': 1, 'res_partner_search_mode': 'supplier',
                           'default_is_company': True, 'default_supplier_rank': 1,
                           'default_company_id': self.env.company.id}

        if self.country_code and self.country_code == "SG":
            default_context['default_l10n_sg_unique_entity_number'] = self.peppol_identifer.split("sguen", 1)[-1]

        return {
            'name': 'Customer Creation',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'res.partner',
            'type': 'ir.actions.act_window',
            'context': default_context,
        }
