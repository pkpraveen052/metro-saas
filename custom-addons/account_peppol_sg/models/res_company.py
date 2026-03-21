# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests
import json
import logging
import re
import random

logger = logging.getLogger(__name__)

TIMEOUT = 20


class ResCompany(models.Model):
    _inherit = 'res.company'

    def get_peppol_scheme(self):
        peppol_scheme = self.env['ir.config_parameter'].sudo().get_param('electronic_address_scheme', False)
        return peppol_scheme

    embed_pdf_in_ubl_xml_invoice = fields.Boolean(
        string="Embed PDF in UBL XML Invoice",
        help="If active, the standalone UBL Invoice XML file will include the "
             "PDF of the invoice in base64 under the node "
             "'AdditionalDocumentReference'. For example, to be compliant with the "
             "e-fff standard used in Belgium, you should activate this option.",
    )
    legal_entity_identifier = fields.Char(string='Legal Entity Identifier', copy=False)
    peppol_identifier = fields.Char(string='Peppol Identifer', size=64, copy=False)
    peppol_identifier_old = fields.Char(string='Technical field', size=64, copy=False)
    peppol_scheme = fields.Char(string='Peppol Scheme', size=64, default=get_peppol_scheme, copy=False)
    peppol_superscheme = fields.Char(string='Peppol Superscheme', default='iso6523-actorid-upis', copy=False)
    hide_create_peppol_id_btn = fields.Boolean(string='Technical field', copy=False)
    peppol_id_created = fields.Boolean("Technical field", copy=False)
    hide_update_peppol_id_btn = fields.Boolean(string='Technical field', default=True)

    corppass_enabled = fields.Boolean(string="Enabled",
                                      help="Whether or not to enable the CorpPass flow."
                                           "For now, defaults to false. In the future, will default to true."
                                           " At some other point in the future, the value false will no longer be allowed",
                                      default=True, copy=False)
    corppass_flow_type = fields.Selection(
        [('corppass_flow_redirect', 'Corppass Flow Redirect'), ('corppass_flow_email', 'Corppass Flow Email')],
        default='corppass_flow_email', copy=False)
    corppass_client_redirect_fail_url = fields.Char(string="Client Redirect Fail Url", size=255, copy=False,
                                                    help="The URL the CorpPass system will redirect to in case of a failure to perform identity verfication.")
    corppass_client_redirect_success_url = fields.Char(string="Client Redirect Success Url", size=255, copy=False,
                                                       help="The URL the CorpPass system will redirect to in case of successful identity verfication.")
    corppass_signer_email = fields.Char(string="Signer Email", size=128, copy=False,
                                        help="The email of the person who is going to perform the CorpPass process.")
    corppass_signer_name = fields.Char(string="Signer Name", size=64, copy=False,
                                       help="The name of the person who is going to perform the CorpPass process.")
    corppass_simulate_corppass = fields.Boolean(string="Signer Corppass", default=False, copy=False,
                                                help="Whether or not to simulate CorpPass. Instead of redirecting to a CorpPass URL, you will receive a redirect to a Storecove URL which will show a page with two buttons: success and fail. This makes development without having test CorpPass credentials possible.")
    tenant_id = fields.Char('Tenant ID',
                            help="The id of the tenant, and is used in case of multi-tenant solutions. This property will included in webhook events.",
                            copy=False)

    _sql_constraints = [('tenant_id', 'unique(tenant_id)',
                         'It seems the Tenant ID generated here is not unique. Please retry your current operation.')]

    @api.model
    def create(self, vals):
        """overridden for updating  the peppol Identifier with UEN  while creating record"""
        if vals.get("l10n_sg_unique_entity_number"):
            vals['peppol_identifier'] = "SGUEN" + vals.get("l10n_sg_unique_entity_number")
        vals['hide_update_peppol_id_btn'] = True
        res = super(ResCompany, self).create(vals)
        return res

    @api.constrains('peppol_identifier')
    def _check_peppol_id_schema(self):
        for field in self:
            if field.country_id.code == 'SG' and field.peppol_identifier and not re.search("^sguen[ _]*[A-Za-z0-9 _]*$",
                                                                                           field.peppol_identifier,
                                                                                           re.IGNORECASE):
                raise UserError(_('Please provide a proper format for Peppol Identifier'))

    def create_legal_entity(self):
        peppol_access_point_pool = self.env['peppol.access.point.sg']
        acccess_point_obj = peppol_access_point_pool.search([('company_id', '=', self.id)])
        if not acccess_point_obj:
            raise UserError(
                _('Please define a Peppol Access Point first. Go to Peppol > Configuration > Access Point.'))
        else:
            acccess_point_obj = acccess_point_obj[-1]
        api_key = acccess_point_obj.authorization_key
        endpoint = "{}/legal_entities".format(acccess_point_obj.endpoint)
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(api_key),
            "Content-Type": "application/json"
        }
        tenant_id = random.randint(10000, 99999)
        data = {
            "party_name": self.name,
            "line1": self.street or "none",
            "line2": self.street2 or "none",
            "city": self.city or "none",
            "zip": self.zip or "none",
            "county": self.country_id and self.country_id.name or "none",
            "country": self.country_id and self.country_id.code or "none",
            "public": True,
            "advertisements": [
                "invoice",
                "invoice_response"
            ],
            "tenant_id": tenant_id
        }
        try:
            req = requests.post(endpoint,
                                json=data,
                                headers=headers,
                                timeout=TIMEOUT)
        except requests.exceptions.Timeout:
            raise UserError(_('A timeout occured while trying to reach the Storecove Api.'))
        except requests.exceptions.HTTPError:
            raise UserError(_('HTTP error occurred while trying to reach the Storecove Api.'))
        except Exception:
            raise UserError(_('The Storecove Api is not reachable, please try again later.'))
        try:
            req.raise_for_status()
        except requests.exceptions.HTTPError:
            raise UserError(_('HTTP error occurred while trying to reach the Storecove Api.'))
        response = req.json()

        if req.status_code == 200:
            self.write({'legal_entity_identifier': response['id'],
                        'tenant_id': tenant_id})

    def update_legal_entity(self):
        """ This method is for Updating  of the partner data of the legal entity id in Storecove """
        peppol_access_point_pool = self.env['peppol.access.point.sg']
        acccess_point_obj = peppol_access_point_pool.search([('company_id', '=', self.id)])
        if not acccess_point_obj:
            raise UserError(
                _('Please define a Peppol Access Point for this Company. Go to Peppol > Configuration > Access Point.'))
        else:
            acccess_point_obj = acccess_point_obj[-1]
        api_key = acccess_point_obj.authorization_key
        endpoint = "{base_url}/legal_entities/{lgl_id}".format(base_url=acccess_point_obj.endpoint,
                                                               lgl_id=self.legal_entity_identifier)
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(api_key),
            "Content-Type": "application/json"
        }

        if not self.tenant_id:
            self.tenant_id = random.randint(10000, 99999)

        data = {
            "id": int(self.legal_entity_identifier),
            "party_name": self.name,
            "line1": self.street or "none",
            "line2": self.street2 or "none",
            "city": self.city or "none",
            "zip": self.zip or "none",
            "county": self.country_id and self.country_id.name or "none",
            "country": self.country_id and self.country_id.code or "none",
            "public": True,
            "advertisements": [
                "invoice",
                "invoice_response"
            ],
            "tenant_id": self.tenant_id
        }

        try:
            req = requests.patch(endpoint,
                                 json=data,
                                 headers=headers,
                                 timeout=TIMEOUT)
        except requests.exceptions.Timeout:
            raise UserError(_('A timeout occured while trying to reach the Storecove Api .'))
        except requests.exceptions.HTTPError:
            raise UserError(_('HTTP error occurred while trying to reach the Storecove Api.'))
        except Exception:
            raise UserError(_('The Storecove Api is not reachable, please try again later.'))
        try:
            req.raise_for_status()
        except requests.exceptions.HTTPError:
            raise UserError(_('HTTP error occurred while trying to reach the Storecove Api.'))
        req.json()
        if req.status_code == 200:
            return {
                'name': 'Message',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'peppol.info.message',
                'target': 'new',
                'context': {'default_message': 'Updated Successfully!'}
            }
        elif req.status_code == 401:
            raise UserError(_('%s \n401 Unauthorized') % self.name)
        elif req.status_code == 403:
            raise UserError(_('%s \nForbidden') % self.name)
        elif req.status_code == 422:
            raise UserError(_('%s \nUnprocessable Entity') % self.name)
        else:
            raise UserError(_('%s \nUndefined Error Occured') % self.name)

    def create_peppol_id_api_call(self, data, headers, endpoint, frm_pep_id_crt_mtd=True):
        """This method is used to call create peppol id end point with using params"""
        try:
            req = requests.post(endpoint,
                                json=data,
                                headers=headers,
                                timeout=TIMEOUT)
        except requests.exceptions.Timeout:
            self.hide_create_peppol_id_btn = 0
            if frm_pep_id_crt_mtd:
                raise UserError(_('A timeout occured while trying to reach the Storecove Api.'))
        except requests.exceptions.HTTPError:
            self.hide_create_peppol_id_btn = 0
            if frm_pep_id_crt_mtd:
                raise UserError(_('HTTP error occurred while trying to reach the Storecove Api.'))
        except Exception:
            self.hide_create_peppol_id_btn = 0
            if frm_pep_id_crt_mtd:
                raise UserError(_('The Storecove Api is not reachable, please try again later.'))
        if req.status_code == 401:
            self.hide_create_peppol_id_btn = 0
            if frm_pep_id_crt_mtd:
                raise UserError(_('%s \n401 Unauthorized') % self.name)
        elif req.status_code == 403:
            self.hide_create_peppol_id_btn = 0
            if frm_pep_id_crt_mtd:
                raise UserError(_('%s \nForbidden') % self.name)
        elif req.status_code == 422:
            response = req.json()
            if isinstance(response['errors'], list):
                detailed_info = response['errors'][0].get('details')
            else:
                detailed_info = 'None'
            self.hide_create_peppol_id_btn = 0
            if frm_pep_id_crt_mtd:
                raise UserError(_('%s \nUnprocessable Entity\n\nDetails: %s') % (self.name, detailed_info))
        return req

    def create_peppol_identifier(self):
        peppol_access_point_pool = self.env['peppol.access.point.sg']
        acccess_point_obj = peppol_access_point_pool.search([('company_id', '=', self.id)])
        if not acccess_point_obj:
            raise UserError(
                _('Please define a Peppol Access Point for this Company. Go to Peppol > Configuration > Access Point.'))
        elif not self.peppol_identifier:
            raise UserError(_("Please fill the field 'Peppol Identifier'."))
        else:
            acccess_point_obj = acccess_point_obj[-1]
        api_key = acccess_point_obj.authorization_key
        endpoint = "{}/legal_entities/{}/peppol_identifiers".format(acccess_point_obj.endpoint,
                                                                    self.legal_entity_identifier)

        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(api_key),
            "Content-Type": "application/json"
        }
        data = {
            "identifier": self.peppol_identifier,
            "scheme": self.peppol_scheme,
            "superscheme": self.peppol_superscheme,
        }

        if self.country_id.code == 'SG':
            corppass_dic = {
                "enabled": self.corppass_enabled,
                "flow_type": self.corppass_flow_type,
                "simulate_corppass": self.corppass_simulate_corppass,
            }
            self.corppass_signer_name and corppass_dic.update({"signer_name": self.corppass_signer_name})
            self.corppass_signer_email and corppass_dic.update({"signer_email": self.corppass_signer_email})
            self.corppass_client_redirect_success_url and corppass_dic.update(
                {"client_redirect_success_url": self.corppass_client_redirect_success_url})
            self.corppass_client_redirect_fail_url and corppass_dic.update(
                {"client_redirect_fail_url": self.corppass_client_redirect_fail_url})
            data.update(corppass_dic)

        req = self.create_peppol_id_api_call(data, headers, endpoint)

        if req.status_code == 200:
            self.peppol_id_created = True
            self.hide_create_peppol_id_btn = True
            self.peppol_identifier_old = self.peppol_identifier
            message_id = self.env['peppol.info.message'].create(
                {'message': 'Peppol Identifier tagged to the Legal Entity Successfully!'})
            return {
                'name': 'Message',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'peppol.info.message',
                'res_id': message_id.id,
                'target': 'new'
            }

    def create_another_peppol_identifier(self):
        peppol_access_point_pool = self.env['peppol.access.point.sg']
        acccess_point_obj = peppol_access_point_pool.search([('company_id', '=', self.id)])
        if not acccess_point_obj:
            raise UserError(
                _('Please define a Peppol Access Point for this Company. Go to Peppol > Configuration > Access Point.'))
        elif not self.peppol_identifier:
            raise UserError(_("Please fill the field 'Peppol Identifier'."))
        else:
            acccess_point_obj = acccess_point_obj[-1]
        api_key = acccess_point_obj.authorization_key
        endpoint = "{}/legal_entities/{}/peppol_identifiers".format(acccess_point_obj.endpoint,
                                                                    self.legal_entity_identifier)

        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(api_key),
            "Content-Type": "application/json"
        }
        data = {
            "identifier": self.peppol_identifier,
            "scheme": self.peppol_scheme,
            "superscheme": self.peppol_superscheme,
            "corppass": {
                "enabled": True,
                "flow_type": "corppass_flow_redirect"
            }
        }
        req = self.create_peppol_id_api_call(data, headers, endpoint)

        if req.status_code == 200:
            self.hide_update_peppol_id_btn = True
            self.peppol_identifier_old = self.peppol_identifier
            message_id = self.env['peppol.info.message'].create(
                {'message': 'Peppol Identifier added/created to the Legal Entity Successfully!'})
            return {
                'name': 'Message',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'peppol.info.message',
                'res_id': message_id.id,
                'target': 'new'
            }

    @api.onchange('peppol_identifier')
    def peppol_identifier_onchange(self):
        """ this method to show the update peppol identifier button by setting boolean field"""
        if self.peppol_identifier:
            self.peppol_identifier = self.peppol_identifier.upper()
        if self.peppol_id_created:
            self.hide_update_peppol_id_btn = 0

    def write(self, values):
        """overridden for updating  the peppol Identifier and UEN changes"""
        if values.get("l10n_sg_unique_entity_number"):
            values['peppol_identifier'] = "SGUEN" + values.get("l10n_sg_unique_entity_number")
            if self.peppol_id_created and self.peppol_identifier != values['peppol_identifier']:
                values['hide_update_peppol_id_btn'] = 0
        return super(ResCompany, self).write(values)

    def create_access_point(self):
        pass
