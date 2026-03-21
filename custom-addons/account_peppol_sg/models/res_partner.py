# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests
import json
import logging
import re
from datetime import date, datetime

logger = logging.getLogger(__name__)

TIMEOUT = 20


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def get_peppol_scheme(self):
        peppol_scheme = self.env['ir.config_parameter'].sudo().get_param('electronic_address_scheme', False)
        return peppol_scheme

    peppol_identifier = fields.Char(string='Peppol Identifer', size=64, tracking=True)
    peppol_scheme = fields.Char(string='Peppol Scheme', size=64, tracking=True, default=get_peppol_scheme)
    peppol_superscheme = fields.Char(string='Peppol Superscheme', default='iso6523-actorid-upis', tracking=True)
    peppol_registered_date = fields.Date(string='Peppol Registered Date', tracking=True)

    def verify_identifier_registered(self):
        """This method gives a message as per peppol API's response."""
        params = self.env['ir.config_parameter'].sudo()
        peppol_endpoint = params.get_param('peppol_endpoint', default=False)
        token = params.get_param('peppol_apikey', default=False)
        url = "{}private/api/search/exist?uen={}".format(peppol_endpoint, self.peppol_identifier)
        headers = {'Content-type': 'application/json;charset=UTF-8', 'Authorization': 'Bearer {}'.format(token)}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                message = 'OK'
            elif response.status_code == 204:
                message = 'Participant exist'
            elif response.status_code == 300:
                message = 'Multiple participants matching the UEN exist (only possible when UEN is provided)'
            elif response.status_code == 400:
                message = 'Bad request'
            elif response.status_code == 404:
                message = 'Participant not found'
            else:
                message = 'Responded with Status Code as '+ str(response.status_code)
            notification = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Result'),
                    'message': message,
                    'sticky': False,
                }
            }
            return notification
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Exception handled Error'),
                    'message': repr(r),
                    'sticky': False,
                }
            }


    @api.constrains('peppol_identifier')
    def _check_peppol_id_schema(self):
        for field in self:
            if field.country_id.code == 'SG' and field.peppol_identifier and not re.search("^sguen[ _]*[A-Za-z0-9 _]*$", field.peppol_identifier, re.IGNORECASE):
                raise UserError(_('Please provide a proper format for Peppol ID'))

    @api.model
    def update_country_regdate(self, country_code,reg_date):
        """this method is used to set conunty and reg date for js dropdown"""
        country = self.env['res.country'].search([('code','=',country_code)])
        reg_date = datetime.strptime(str(reg_date),'%Y-%m-%d').strftime("%Y-%m-%d")
        return {'country_id':country.id,
                'reg_date':reg_date}


    @api.model
    def create(self, vals):
        """overridden for updating  the peppol Identifier with UEN  while creating record"""
        if vals.get("l10n_sg_unique_entity_number"):
            vals['peppol_identifier'] = "SGUEN" + vals.get("l10n_sg_unique_entity_number")
        res = super(ResPartner, self).create(vals)
        return res

    def write(self, values):
        """overridden for updating  the peppol Identifier in the res.partner model when ever peppol id changes in res.partner """
        if "peppol_identifier" in values :
            company_obj=self.env['res.company'].search([('partner_id', '=', self.id)])
            company_obj.write({"peppol_identifier":values['peppol_identifier']})
        if values.get("l10n_sg_unique_entity_number") :
            values['peppol_identifier'] = "SGUEN" + values.get("l10n_sg_unique_entity_number")
        return super(ResPartner, self).write(values)
