import requests
import json
from datetime import datetime as dt
from odoo import models, fields, api,tools
from odoo.exceptions import UserError
from urllib.parse import quote
import urllib.parse
import logging
_logger = logging.getLogger(__name__)


SELECTION_C5_STATE = [
    ('draft', 'Draft'),
    ('initiated_activation', 'Initiated Activation'),
    ('kyc_pending', 'KYC Pending'),
    ('activated', 'Activated'),
    ('initiated_deactivation', 'Initiated Deactivation'),
    ('deactivated', 'Deactivated')

]

ERROR_RESPONSES_DIC = {
    400: 'Bad Request',
    401: 'Unauthorized',
    404: 'Not Found',
    403: 'Forbidden',
    405: 'Method not allowed'
}

class C5Activation(models.Model):
    _name = 'c5.activation'
    _inherit = ['mail.activity.mixin','mail.thread','portal.mixin']
    _description = 'C5 Activation'
    _rec_name = "peppol_id"

    peppol_id = fields.Char(string="Peppol ID",tracking=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company)
    status = fields.Selection(SELECTION_C5_STATE, string="Status", default="draft", required=True,tracking=True)
    active = fields.Boolean(string="Active", default=True)
    signer_name = fields.Char(string="Signer Name",tracking=True)
    signer_email = fields.Char(string="Signer Email",tracking=True)
    initiated_date = fields.Char(string="Initiated Date")
    signing_link = fields.Char(string="Signing Link")
    signed_date = fields.Char(string="Signed Date")
    response_status_code = fields.Char(string="Response Status Code")
    response_message = fields.Text(string="Response Message")
    color = fields.Integer('Color Index', default=0)
    signed = fields.Boolean(string="Signed")  
    actual_signer_name = fields.Char(string="Actual Signer Name")  
    actual_signer_email = fields.Char(string="Actual Signer Email")
    last_c5_action = fields.Selection([
        ('activated', 'Activated'),
        ('deactivated', 'Deactivated'),
        ('cancelled', 'Cancelled'),
    ], string="Last C5 Action")
    note  = fields.Text('Note')

    # reg_id = fields.Char(string="Reg ID",required=True,tracking=True)
    # registered_name = fields.Char(string="Registered Name",tracking=True)
    # registration_id = fields.Char(string="Registration ID",tracking=True)
    # registered_from = fields.Date(string="Registered From",tracking=True)
    # registration_status = fields.Selection([
    #     ('registered', 'Registered'),
    #     ('unregistered', 'Unregistered'),
    # ], string="GST Reg Status",tracking=True)
    # remark = fields.Text(string="Remarks",tracking=True)
    # is_registration_via_iras = fields.Boolean(string="GST Reg via IRAS",default=False,tracking=True)
    # return_code = fields.Char(string="Retrun Code",tracking=True)


    @api.model
    def default_get(self, fields_list):
        defaults = super(C5Activation, self).default_get(fields_list)
        company = self.env.company  
        if company.peppol_identifier:
            defaults['peppol_id'] = company.peppol_identifier
            # defaults['reg_id'] = company.vat  

        return defaults
    
    # def check_gst_register(self):
    #     """Check GST Registration using Peppol API"""
    #     peppol_access = self.env['peppol.access.point.sg'].sudo().search(
    #         [('company_id', '=', self.env.company.id)], limit=1
    #     )

    #     if not peppol_access:
    #         raise UserError("Peppol Access Point settings not configured.")

    #     base_url = peppol_access.endpoint
    #     api_version = peppol_access.api_version
    #     access_token = peppol_access.access_token  

    #     url = f"{base_url}/business/{api_version}/iras/gst/search"

    #     headers = {
    #         "Authorization": f"Bearer {access_token}",
    #         "Accept": "application/json",
    #         "Content-Type": "application/json"
    #     }

    #     for record in self:
    #         if not record.reg_id:
    #             raise UserError("GST Registration Number is required.")

    #         payload = {"regID": record.reg_id}

    #         try:
    #             response = requests.post(url, headers=headers, json=payload, timeout=10)

    #             record.message_post(body=f"API Response: {response.text}")

    #             if response.status_code != 200:
    #                 record.message_post(body=f"Error {response.status_code}: {response.text}")
    #                 record.is_registration_via_iras = False  
    #                 return

    #             response_data = response.json()

    #             return_code = response_data.get("returnCode", "")

    #             if return_code == "10" and "data" in response_data:
    #                 gst_data = response_data.get("data", {})

    #                 record.write({
    #                     "return_code": return_code, 
    #                     "reg_id": gst_data.get("gstRegistrationNumber", ""),
    #                     "registered_name": gst_data.get("name", ""), 
    #                     "registration_id": gst_data.get("registrationId", ""),
    #                     "registered_from": gst_data.get("RegisteredFrom", ""),
    #                     "registration_status": 'registered' if gst_data.get("Status") == "Registered" else 'unregistered',
    #                     "remark": gst_data.get("Remarks", ""), 
    #                     "is_registration_via_iras": True
    #                 })
    #                 record.message_post(body=f"GST Check Successful. Return Code: {return_code}")
    #             else:
    #                 record.message_post(body=f"Invalid GST response received. Return Code: {return_code}, Response: {json.dumps(response_data, indent=2)}")
    #                 record.is_registration_via_iras = False  # Set to False if invalid response

    #         except requests.Timeout:
    #             record.message_post(body="Request Timeout")
    #             record.is_registration_via_iras = False  # Set to False on timeout
    #         except requests.ConnectionError:
    #             record.message_post(body="Service unavailable (Connection Error)")
    #             record.is_registration_via_iras = False  # Set to False on connection error
    #         except requests.RequestException as e:
    #             record.message_post(body=f"Request error: {str(e)}")
    #             record.is_registration_via_iras = False  # Set to False on general request error

    def resend_email(self):
        template = self.env.ref('metro_einvoice_datapost.email_template_activate_iras_api_for_c5')
        template.send_mail(self.id, force_send=True)

    def initiated_deactivation(self):
        """Initiate C5 deactivation via Peppol API."""
        peppol_access = self.env['peppol.access.point.sg'].sudo().search([('company_id', '=', self.env.company.id)],
                                                                         limit=1)

        if not peppol_access:
            raise UserError("Peppol Access Point settings not configured.")

        base_url = peppol_access.endpoint
        api_version = peppol_access.api_version
        access_token = peppol_access.access_token

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        for record in self:
            peppol_id = record.peppol_id
            if not peppol_id:
                record.message_post(body="Skipping record due to missing Peppol ID.")
                continue  # Skip records without Peppol ID

            # Ensure peppol_id starts with "0195:"
            if not peppol_id.startswith("0195:"):
                peppol_id = f"0195:{peppol_id}"

            # Properly encode Peppol ID
            encoded_peppol_id = quote(peppol_id, safe='')
            print('\n\nencoded_peppol_id', encoded_peppol_id)
            url = f"{base_url}/api/deactivate/{encoded_peppol_id}"

            payload = {
                "signerEmail": record.signer_email,
                "signerName": record.signer_name
            }

            try:
                response = requests.post(url, headers=headers, json=payload, timeout=10)

                if response.status_code != 200:
                    record.message_post(
                        body=f"C5 API Deactivation Failed: {response.status_code} - {response.text}")
                    record.write({
                        'response_status_code': response.status_code,
                        'response_message': f"Error {response.status_code}: {response.text}",
                    })
                    continue  # Skip further processing if API response is invalid

                try:
                    response_data = response.json()
                except json.JSONDecodeError:
                    record.message_post(body="C5 API returned invalid JSON")
                    record.write({
                        'response_status_code': response.status_code,
                        'response_message': "Invalid JSON response from API",
                    })
                    continue  # Skip further processing if JSON decoding fails

                # Update record with API response data
                if response.status_code == 200:
                    # send email template
                    template = self.env.ref('metro_einvoice_datapost.email_template_deactivate_iras_api_for_c5')
                    template.send_mail(self.id, force_send=True)
                    record.write({
                        'status': 'initiated_deactivation',
                        # 'status': response_data.get("status", record.status),
                        'response_status_code': response.status_code,
                        'response_message': response_data.get("message", "Success"),
                        'last_c5_action': 'deactivated',
                    })
                if self.status == 'initiated_deactivation':
                    peppol_c5_group = self.env.ref('metro_einvoice_datapost.group_c5_submitter',
                                                   raise_if_not_found=False)
                    peppol_group = self.env.ref('metro_einvoice_datapost.group_peppol_submitter',
                                                raise_if_not_found=False)
                    company_users = self.env['res.users'].search([('company_id', '=', self.env.company.id)])
                    for company_user in company_users:
                        company_user.write({
                            'groups_id': [(4, peppol_group.id), (3, peppol_c5_group.id)]
                        })
                record.message_post(body="C5 deactivation successful.")


            except requests.Timeout:
                record.message_post(body="C5 API request timeout")
                record.write({
                    'response_status_code': 408,
                    'response_message': "Request timeout",
                })
            except requests.ConnectionError:
                record.message_post(body="C5 API connection error")
                record.write({
                    'response_status_code': 503,
                    'response_message': "Service unavailable (connection error)",
                })
            except requests.RequestException as e:
                record.message_post(body=f"C5 API request failed: {str(e)}")
                record.write({
                    'response_status_code': 500,
                    'response_message': f"Request error: {str(e)}",
                })

    def initiate_activation(self):
        """Initiate C5 activation for specified participants and organizations."""
        peppol_access = self.env['peppol.access.point.sg'].sudo().search(
            [('company_id', '=', self.env.company.id)], limit=1
        )

        if not peppol_access:
            raise UserError("Peppol Access Point settings not configured.")

        base_url = peppol_access.endpoint
        # api_version = peppol_access.api_version
        access_token = peppol_access.access_token

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        for record in self:
            signer_name = record.signer_name
            signer_email = record.signer_email
            peppol_id = record.peppol_id

            if not peppol_id:
                record.message_post(body="Skipping record due to missing Peppol ID.")
                continue  # Skip records without Peppol ID

            if not peppol_id.startswith("0195:"):
                peppol_id = f"0195:{peppol_id}"

            if not signer_name or not signer_email:
                record.message_post(body="Signer name and email are required.")
                record.write({
                    'response_status_code': 400,
                    'response_message': "Signer name and email are required."
                })
                continue

            encoded_peppol_id = quote(peppol_id, safe='')
            print('\n\nencoded_peppol_id111', encoded_peppol_id)
            url = f"{base_url}/api/activate/{encoded_peppol_id}"

            payload = {
                "signerEmail": signer_email,
                "signerName": signer_name
            }

            update_values = {}

            try:
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                print('\nresponse.json()>>data', response.json())
                print('\nresponse.status_code', response.status_code)

                update_values['response_status_code'] = response.status_code

                if response.status_code != 200:
                    error_msg = f"Error {response.status_code}: {response.text}"
                    record.message_post(body=f"C5 Activation Failed: {error_msg}")
                    update_values['response_message'] = error_msg
                else:
                    try:
                        response_data = response.json()
                        if response.status_code == 200:
                            template = self.env.ref('metro_einvoice_datapost.email_template_activate_iras_api_for_c5')
                            template.send_mail(self.id, force_send=True)
                            update_values.update({
                                # 'status': response_data.get('status', record.status),
                                'status': 'initiated_activation',
                                'response_message': response_data.get('message',
                                                                      "C5 activation initiated successfully"),
                                'last_c5_action': 'activated',
                            })
                            record.message_post(body="C5 activation initiated successfully.")

                            # Add all users of the submitter's company to the C5 group
                            peppol_c5_group = self.env.ref('metro_einvoice_datapost.group_c5_submitter',
                                                           raise_if_not_found=False)
                            peppol_group = self.env.ref('metro_einvoice_datapost.group_peppol_submitter',
                                                        raise_if_not_found=False)
                            if peppol_c5_group:
                                company_users = self.env['res.users'].search(
                                    [('company_id', '=', record.company_id.id)])
                                for company_user in company_users:
                                    company_user.write({
                                        'groups_id': [(4, peppol_c5_group.id), (3, peppol_group.id)]
                                    })
                    except json.JSONDecodeError:
                        record.message_post(body="Invalid JSON response from API")
                        update_values['response_message'] = "Invalid JSON response from API"

            except requests.Timeout:
                record.message_post(body="C5 API request timeout")
                update_values['response_status_code'] = 408
                update_values['response_message'] = "Request timeout"

            except requests.ConnectionError:
                record.message_post(body="C5 API connection error")
                update_values['response_status_code'] = 503
                update_values['response_message'] = "Service unavailable (connection error)"

            except requests.RequestException as e:
                error_msg = f"Request error: {str(e)}"
                record.message_post(body=error_msg)
                update_values['response_status_code'] = 500
                update_values['response_message'] = error_msg

            record.write(update_values)

    def reset_to_draft(self):
        self.write({'status': 'draft'})

    def check_status(self):
        """Fetch and update C5 Activation status from Peppol API."""
        peppol_access = self.env['peppol.access.point.sg'].sudo().search(
            [('company_id', '=', self.env.company.id)], limit=1
        )

        if not peppol_access:
            raise UserError("Peppol Access Point settings not configured.")

        base_url = peppol_access.endpoint.rstrip('/')
        api_version = peppol_access.api_version
        access_token = peppol_access.access_token  

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        for record in self:
            peppol_id = record.peppol_id
            if not peppol_id:
                record.message_post(body="Skipping record due to missing Peppol ID.")
                continue 

            # Ensure peppol_id starts with "0195:"
            if not peppol_id.startswith("0195:"):
                peppol_id = f"0195:{peppol_id}"

            # Properly encode Peppol ID
            encoded_peppol_id = quote(peppol_id, safe='')

            # Construct API URL
            url = f"{base_url}/api/c5status?peppolId={encoded_peppol_id}"

            record.message_post(body=f"Sending request to API: <br/><strong>URL:</strong> {url}")

            try:
                response = requests.get(url, headers=headers, timeout=10)

                # Log API response details
                record.message_post(
                    body=f"API Response:<br/><strong>Status Code:</strong> {response.status_code}<br/>"
                        f"<strong>Response Body:</strong> {response.text}"
                )

                if response.status_code != 200:
                    record.write({
                        'response_status_code': response.status_code,
                        'response_message': f"Error {response.status_code}: {response.text or 'Unknown error'}",
                    })
                    continue  # Continue to the next record

                try:
                    response_data = response.json()
                except json.JSONDecodeError:
                    record.message_post(body="Invalid JSON response from API.")
                    record.write({
                        'response_status_code': response.status_code,
                        'response_message': "Invalid JSON response from API",
                    })
                    continue

                # Ensure 'data' is a dictionary
                data = response_data or {}
                if not isinstance(data, dict):
                    record.message_post(body="Unexpected data format in API response.")
                    record.write({
                        'response_status_code': response.status_code,
                        'response_message': "Unexpected data format in API response",
                    })
                    continue

                # Extract and parse dates safely
                def parse_date(date_str):
                    try:
                        return dt.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ") if date_str else None
                    except ValueError:
                        return None  # Handle invalid date formats safely

                signed_date = parse_date(data.get('signedDate'))
                initiated_date = parse_date(data.get('initiatedDate'))

                # Normalize and map API response state value
                state_value = data.get('state', '').strip().lower().replace(' ', '_')
                state_mapping = {
                    'initiated_activation': 'initiated_activation',
                    'kyc_pending': 'kyc_pending',
                    'initiated_deactivation': 'initiated_deactivation',
                    'activated': 'activated',
                    'cancel/deactivated': 'deactivated',
                }
                mapped_state = state_mapping.get(state_value, record.status)

                # Update record with API response data
                record.write({
                    'status': mapped_state,
                    'actual_signer_name': data.get('actualSignerName', record.actual_signer_name),
                    'actual_signer_email': data.get('actualSignerEmail', record.actual_signer_email),
                    'signed': data.get('signed', record.signed),
                    'signing_link': data.get('signingLink', record.signing_link),
                    'signed_date': signed_date if signed_date else record.signed_date,
                    'initiated_date': initiated_date if initiated_date else record.initiated_date,
                    'response_status_code': response.status_code,
                    'response_message': "Success" if mapped_state else f"Unknown status: {state_value}",
                })
                template = self.env.ref('metro_einvoice_datapost.email_template_activate_iras_api_for_c5')
                template.send_mail(self.id, force_send=True)
                if self.status == 'activated':
                    peppol_c5_group = self.env.ref('metro_einvoice_datapost.group_c5_submitter', raise_if_not_found=False)
                    peppol_group = self.env.ref('metro_einvoice_datapost.group_peppol_submitter',
                                                raise_if_not_found=False)
                    company_users = self.env['res.users'].search([('company_id', '=', self.env.company.id)])
                    for company_user in company_users:
                        company_user.write({
                            'groups_id': [(4, peppol_c5_group.id), (3, peppol_group.id)]
                        })
                record.message_post(
                    body=f"Successfully updated Peppol Activation Status.<br/>"
                        f"<strong>New Status:</strong> {mapped_state}<br/>"
                        f"<strong>Signer Name:</strong> {data.get('actualSignerName')}<br/>"
                        f"<strong>Signer Email:</strong> {data.get('actualSignerEmail')}<br/>"
                        f"<strong>Signing Link:</strong> {data.get('signingLink')}<br/>"
                        f"<strong>Signed Date:</strong> {signed_date}<br/>"
                        f"<strong>Initiated Date:</strong> {initiated_date}"
                )

            except requests.Timeout:
                record.message_post(body="API Request Timeout.")
                record.write({
                    'response_status_code': 408,
                    'response_message': "Request timeout",
                })
            except requests.ConnectionError:
                record.message_post(body="API Service unavailable (connection error).")
                record.write({
                    'response_status_code': 503,
                    'response_message': "Service unavailable (connection error)",
                })
            except requests.RequestException as e:
                record.message_post(body=f"API Request Error: {str(e)}")
                record.write({
                    'response_status_code': 500,
                    'response_message': f"Request error: {str(e)}",
                })

    @api.model
    def cron_update_c5_status(self):
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>cron_update_c5_status called")
        """Cron job to fetch the latest C5 activation status for pending records."""

        # Check if Peppol Access Point is configured for the current company
        peppol_access = self.env['peppol.access.point.sg'].sudo().search([('company_id', '=', self.env.company.id)], limit=1)
        
        print("=======================================peppol_access", peppol_access)

        if peppol_access:
            pending_records = self.search([('last_c5_action', '!=', False)])

            for record in pending_records:
                record.check_status()
                
                # Reset last action after fetching status
                record.write({'last_c5_action': False})
        else:
            print("Peppol Access Point settings not configured. Skipping C5 activation update.")

    

  

