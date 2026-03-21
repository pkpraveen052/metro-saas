# -*- coding: utf-8 -*-
from email.policy import default

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
    seller_identifier = fields.Char(string='Seller ID/ Bank assigned creditor ID', help="This element is used for both the identification of the Seller, or the unique banking reference identifier of Seller (assigned by the Seller bank.). For seller identification use ICD code list, for SEPA bank assigned creditor reference, use SEPA. In order for the buyer to automatically identify a supplier, the Seller identifier (BT-29), the Seller legal registration identifier (BT-30) and/or the Seller GST identifier (BT-31-GST) shall be present")
    seller_identifier_scheme = fields.Char('Seller ID/ Bank assigned creditor Scheme', help="The identification scheme identifier of the Seller identifier. For bank assigned creditor identifier (BT-90), value MUST be 'SEPA'")

    reg_id = fields.Char(string="Reg ID")
    nric_no = fields.Char(string="NRIC No")
    registered_name = fields.Char(string="Registered Name")
    registration_id = fields.Char(string="Registration ID")
    registered_from = fields.Date(string="Registered From")
    registration_status = fields.Selection([
        ('registered', 'Registered'),
        ('unregistered', 'Unregistered')
    ], string="GST Registration Status")
    remark = fields.Text(string="Remarks")
    return_code = fields.Char(string="Return Code")
    is_peppol_participant = fields.Boolean(string="Is Peppol Participant")
    is_gst_register = fields.Boolean(string="Is GST Register")
    peppol_document_type = fields.Selection([('PINT', 'PINT'), ('BIS', 'BIS')], tracking=1)
    is_sg_government_customer = fields.Boolean(string="Is Govt Customer?")




    def check_peppol_document_type(self):
        print('\nself', self)
        if self.peppol_identifier:
            url = "https://directory.peppol.eu/search/1.0/json?participant=iso6523-actorid-upis::{}:{}".format(self.peppol_scheme,
                                                                                                               self.peppol_identifier)
            try:
                response = requests.get(url)
                print('\nresponse', response)
                if response.status_code == 200:
                    data = response.json()
                    print('\ndata', data)

                    matches = data.get("matches", [])
                    if matches:
                        match = matches[0]
                        print('\nmatch', match)
                        doc_types = match.get("docTypes", [])
                        print('\ndoc_types', doc_types)
                        if doc_types:
                            has_pint = any('urn:peppol:pint:' in d['value'].lower() for d in doc_types)
                            has_bis = any('urn:cen.eu:en16931' in d['value'].lower() for d in doc_types)
                            if has_pint:
                                self.peppol_document_type = 'PINT'
                            elif has_bis:
                                self.peppol_document_type = 'BIS'
                            else:
                                self.peppol_document_type = False
            except requests.exceptions.RequestException as e:
                raise UserError("Failed to connect to PEPPOL directory: %s" % str(e))

    def action_check_peppol_doc_type(self):
        peppol_partners = self.filtered(lambda p: p.peppol_scheme and p.peppol_identifier)
        for rec in peppol_partners:
            rec.check_peppol_document_type()

    def verify_identifier_registered(self):
        """This method gives a message as per peppol API's response."""
        params = self.env['ir.config_parameter'].sudo()
        peppol_endpoint = params.get_param('peppol_endpoint', default=False)
        token = params.get_param('peppol_apikey', default=False)
        electronic_address_scheme = params.get_param('electronic_address_scheme', default="0195")
        url = "{}private/api/search/exist?pid=iso6523-actorid-upis::{}:{}".format(peppol_endpoint, electronic_address_scheme, self.peppol_identifier or '')        
        headers = {'Content-type': 'application/json;charset=UTF-8', 'Authorization': 'Bearer {}'.format(token)}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                message = 'OK'
                self.write({'is_peppol_participant': True})
                # self.is_peppol_participant = True
            elif response.status_code == 204:
                message = 'Participant exist'
                self.write({'is_peppol_participant': True})
                # self.is_peppol_participant = True
            elif response.status_code == 300:
                message = 'Multiple participants matching the UEN exist (only possible when UEN is provided)'
            elif response.status_code == 400:
                message = 'Bad request'
            elif response.status_code == 404:
                message = 'Participant not found'
                self.is_peppol_participant = False
            else:
                message = 'Responded with Status Code as ' + str(response.status_code)
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
                    'message': repr(e),
                    'sticky': False,
                }
            }

    # @api.constrains('peppol_identifier')
    # def _check_peppol_id_schema(self):
    #     for field in self:
    #         if field.country_id.code == 'SG' and field.peppol_identifier and not re.search("^sguen[ _]*[A-Za-z0-9 _]*$", field.peppol_identifier, re.IGNORECASE):
    #             raise UserError(_('Please provide a proper format for Peppol ID'))

    @api.model
    def update_country_regdate(self, country_code, reg_date):
        """this method is used to set conunty and reg date for js dropdown"""
        country = self.env['res.country'].search([('code', '=', country_code)])
        reg_date = datetime.strptime(str(reg_date), '%Y-%m-%d').strftime("%Y-%m-%d")
        return {'country_id': country.id,
                'reg_date': reg_date}

    @api.model
    def create(self, vals):
        """overridden for updating  the peppol Identifier with UEN  while creating record"""
        if vals.get("l10n_sg_unique_entity_number"):
            vals['peppol_identifier'] = "SGUEN" + vals.get("l10n_sg_unique_entity_number")
        res = super(ResPartner, self).create(vals)
        return res

    def write(self, values):
        """ overridden for updating  the peppol Identifier in the res.partner model when ever peppol id changes in
        res.partner """
        if "peppol_identifier" in values:
            company_obj = self.env['res.company'].search([('partner_id', '=', self.id)])
            company_obj.write({"peppol_identifier": values['peppol_identifier']})
        if values.get("l10n_sg_unique_entity_number"):
            values['peppol_identifier'] = "SGUEN" + values.get("l10n_sg_unique_entity_number")
        return super(ResPartner, self).write(values)

    def action_send_email_template(self):
        templates = self.env.ref(
        'metro_einvoice_datapost.email_template_res_partner_news'
        )
        for record in self:
            ctx = {
                'default_model': 'res.partner',
                'default_res_id': record.id,
                'default_use_template': True,
                'default_template_id': templates.id,
                'default_composition_mode': 'comment',
                'force_email': True,
                'default_partner_ids': [(6, 0, [record.id])],
            }
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(False, 'form')],
                'view_id': False,
                'target': 'new',
                'context': ctx,
            }

    def cron_auto_check_gst_register(self):
        """Cron job to automatically check GST registration for all records"""
        partners = self.search([
            '|', 
            ('vat', '!=', False), 
            ('nric_no', '!=', False)  # Include partners with NRIC numbers
        ])  

        for partner in partners:
            try:
                partner.check_gst_register()
            except UserError as e:
                partner.message_post(body=f"GST Check Skipped: {str(e)}")
            except Exception as e:
                partner.message_post(body=f"Unexpected Error in GST Check: {str(e)}")

    def check_gst_register(self, partner_obj=False):
        print('\n\npartner_obj', partner_obj)
        if not partner_obj:
            partner_obj = self

        config_params = self.env['ir.config_parameter'].sudo()

        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'X-IBM-Client-Id': config_params.get_param('iras_apikey'),
            'X-IBM-Client-Secret': config_params.get_param('iras_apisecret')
        }

        payload = {
            "clientID": config_params.get_param('iras_apikey'),
            "regID": partner_obj.vat
        }

        url = config_params.get_param('searchgst_registered_endpoint')

        try:
            response = requests.request("POST", url, data=json.dumps(payload), headers=headers, allow_redirects=False)

            res_data = json.loads(response.text)
            if res_data.get('returnCode'):
                if res_data['returnCode'] == "10":
                    partner_obj.message_post(body="GST Registered.\n" + json.dumps(res_data))
                    partner_obj.write({'registration_status': 'registered'})
                else:
                    partner_obj.message_post(body="GST unregistered.\n" + json.dumps(res_data))
                    partner_obj.write({'registration_status': 'unregistered'})
            else:
                partner_obj.message_post(body="GST Check Error.\n" + json.dumps(res_data))
                partner_obj.write({'registration_status': 'unregistered'})

        except requests.Timeout:
            partner_obj.message_post(body="GST Check: Request Timeout")
        except requests.ConnectionError:
            partner_obj.message_post(body="GST Check: Service unavailable (Connection Error)")
        except requests.RequestException as e:
            partner_obj.message_post(body=f"GST Check Request error: {str(e)}")
        except Exception as e:
            partner_obj.message_post(body=f"GST Check: Exception arised: {str(e)}")

    # def check_gst_register(self):
    #     """Check GST Registration using Peppol API"""
    #     peppol_access = self.env['peppol.access.point.sg'].sudo().search(
    #         [('company_id', '=', self.env.company.id)], limit=1
    #     )
    #
    #     if not peppol_access:
    #         raise UserError("Peppol Access Point settings not configured.")
    #
    #     base_url = peppol_access.endpoint
    #     api_version = peppol_access.api_version
    #     access_token = peppol_access.access_token
    #
    #     url = f"{base_url}/business/{api_version}/iras/gst/search"
    #
    #     headers = {
    #         "Authorization": f"Bearer {access_token}",
    #         "Accept": "application/json",
    #         "Content-Type": "application/json"
    #     }
    #
    #     for record in self:
    #         # Check if either vat or nric_no is present
    #         if not record.vat and not record.nric_no:
    #             raise UserError("Either VAT or NRIC Number is required.")
    #
    #         # Use vat if present, otherwise use nric_no
    #         payload = {"regID": record.vat if record.vat else record.nric_no}
    #
    #         try:
    #             response = requests.put(url, headers=headers, json=payload, timeout=10)
    #
    #             # Log the API response for debugging
    #             record.message_post(body=f"API Response: {response.text}")
    #
    #             if response.status_code != 200:
    #                 record.is_gst_register = False
    #                 record.message_post(body=f"Error {response.status_code}: {response.text}")
    #                 return
    #
    #             response_data = response.json()
    #
    #             return_code = response_data.get("returnCode", "")
    #
    #             # Ensure returnCode is 10 and data exists
    #             if response_data.get("returnCode") == "10" and "data" in response_data:
    #                 gst_data = response_data.get("data", {})
    #
    #                 registration_status = 'registered' if gst_data.get("Status") == "Registered" else 'unregistered'
    #
    #                 record.write({
    #                     "return_code": return_code,  # Store returnCode in the record
    #                     "vat": gst_data.get("gstRegistrationNumber", ""),  # Update VAT field
    #                     "registered_name": gst_data.get("name", ""),  # Handle missing 'name'
    #                     "registration_id": gst_data.get("registrationId", ""),  # Handle missing 'registrationId'
    #                     "registered_from": gst_data.get("RegisteredFrom", ""),
    #                     "registration_status": registration_status,
    #                     "remark": gst_data.get("Remarks", ""),  # Fix incorrect key from 'Remark' to 'Remarks'
    #                 })
    #
    #                 # Set is_gst_register=True only if returnCode is "10" and registration_status is "registered"
    #                 record.is_gst_register = (return_code == "10" and registration_status == "registered")
    #                 record.message_post(body="GST Check Successful")
    #             else:
    #                 record.is_gst_register = False
    #                 record.message_post(body=f"Invalid GST response received. Response: {json.dumps(response_data, indent=2)}")
    #
    #         except requests.Timeout:
    #             record.is_gst_register = False
    #             record.message_post(body="Request Timeout")
    #         except requests.ConnectionError:
    #             record.is_gst_register = False
    #             record.message_post(body="Service unavailable (Connection Error)")
    #         except requests.RequestException as e:
    #             record.is_gst_register = False
    #             record.message_post(body=f"Request error: {str(e)}")

    @api.onchange('l10n_sg_unique_entity_number')
    def onchange_l10n_sg_unique_entity_number(self):
        if not self.l10n_sg_unique_entity_number:
            self.peppol_identifier = False
            self.is_peppol_participant = False
