# -*- coding: utf-8 -*-
import base64
import logging
import uuid
import json
import requests
import datetime
from odoo import api, fields, models, _,tools
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)


class PeppolAccessPointSG(models.Model):
    _name = "peppol.access.point.sg"
    _description = "Access Point Configuration"
    _inherit = "mail.thread"
    _rec_name = "company_id"

    api_key = fields.Char(string='API Key', required=True,tracking=True)
    api_secret = fields.Char(string='API Secret', required=True,tracking=True)
    endpoint = fields.Char(string='BaseURL', required=True,tracking=True)
    api_version = fields.Char(string="API Version", required=True,tracking=True)
    note = fields.Text(string='Note',tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,tracking=True)
    active = fields.Boolean('Active', default=True,tracking=True)
    access_token = fields.Text(string="Access Token")
    refresh_token = fields.Text(string="Refresh Token")


    _sql_constraints = [
        (
            'company_id',
            'unique(company_id)',
            "Company must be unique!.",
        ),
    ]

    @api.model
    def default_get(self, fields):
        res = super(PeppolAccessPointSG, self).default_get(fields)
        res['endpoint'] = self.env['ir.config_parameter'].sudo().get_param('endpoint') or False
        res['api_version'] = self.env['ir.config_parameter'].sudo().get_param('api_version') or False
        return res

    def get_basic_auth_token(self):
        api_key_secret = "%s:%s" % (self.api_key, self.api_secret)
        api_key_secret_bytes = api_key_secret.encode("ascii")
        base64_bytes = base64.b64encode(api_key_secret_bytes)
        base64_string = base64_bytes.decode("ascii")
        return base64_string

    def get_client_ref(self):
        return uuid.uuid4().hex

    def get_access_token(self):
        token_url = self.env['ir.config_parameter'].sudo().get_param('token_url')

        if not token_url:
            raise UserError("Token URL is not configured. Please set Token URL in system parameters.")

        # url = f"{token_url}/app/services/rest/auth/token"
        url = f"{token_url}/api/app/services/rest/auth/token"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = json.dumps({
            "client_id": self.api_key,
            "secret_id": self.api_secret
        })

        try:
            response = requests.post(url, headers=headers, data=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()

                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")

                # Log success message in chatter
                message = (
                    f"Peppol access token retrieved successfully.<br/>"
                    f"New Access Token: {self.access_token}<br/>"
                    f"New Refresh Token: {self.refresh_token}"
                )
                self.message_post(body=message)

                return {"success": True, "message": "Token retrieved successfully"}

            else:
                error_msg = f"Failed to retrieve access token. HTTP {response.status_code}: {response.text}"
                self.message_post(body=error_msg)
                return {"success": False, "message": error_msg}

        except requests.exceptions.RequestException as e:
            error_msg = f"Request error while retrieving token: {str(e)}"
            self.message_post(body=error_msg)
            return {"success": False, "message": error_msg}
        
    def refresh_access_token(self):
        for record in self:
            if not record.refresh_token:
                record.message_post(body="No refresh token found. Please update Peppol settings.")
                return {"success": False, "message": "No refresh token found"}
            # Fetch the token URL from system parameters
            token_url = self.env['ir.config_parameter'].sudo().get_param('token_url')
            if not token_url:
                raise UserError("Token URL is not configured. Please set Token URL in system parameters.")
            # url = f"{token_url}/app/services/rest/auth/refreshToken"
            url = f"{token_url}/api/app/services/rest/auth/refreshToken"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {record.access_token}",  # Use the current access token
            }
            payload = json.dumps({"refresh_token": record.refresh_token})
            try:
                response = requests.post(url, headers=headers, data=payload)
                if response.status_code == 200:
                    data = response.json()
                    new_access_token = data.get("access_token")
                    new_refresh_token = data.get("refresh_token")  # Get the new refresh token
                    # Update record with new tokens
                    record.write({
                        "access_token": new_access_token,
                        "refresh_token": new_refresh_token,  # Save the new refresh token
                    })
                    # Log success in chatter
                    message = (
                        f"Peppol token refreshed successfully.<br/>"
                        f"New Access Token: {new_access_token}<br/>"
                        f"New Refresh Token: {new_refresh_token}"
                    )
                    record.message_post(body=message)
                    return {"success": True, "message": "Token refreshed successfully"}
                elif response.status_code == 401:
                    record.message_post(body="Unauthorized. Check API credentials or token.")
                    return {"success": False, "message": "Unauthorized. Check API credentials or token."}
                else:
                    error_msg = f"Token refresh failed. HTTP {response.status_code}: {response.text}"
                    record.message_post(body=error_msg)
                    return {"success": False, "message": error_msg}
            except Exception as e:
                error_msg = f"Exception during token refresh: {str(e)}"
                record.message_post(body=error_msg)
                return {"success": False, "message": error_msg}                
    
    @api.model
    def cron_refresh_access_token(self):
        _logger.info("Starting cron job: Refresh Peppol Access Token")
        access_point = self.env["peppol.access.point.sg"].sudo().search([])
        if access_point:
            for peppol_access in access_point:
                if not peppol_access.refresh_token:
                    peppol_access.message_post(body="Missing refresh token. Please update Peppol settings.")
                    continue

                # Fetch token URL dynamically from system parameters
                token_url = self.env["ir.config_parameter"].sudo().get_param("token_url")
                if not token_url:
                    peppol_access.message_post(body="Peppol Token URL is not configured in system parameters.")
                    continue

                url = f"{token_url}/api/app/services/rest/auth/refreshToken"
                _logger.info("Refreshing token via URL: %s", url)

                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }
                payload = {"refresh_token": peppol_access.refresh_token}
                # payload = json.dumps({"refresh_token": peppol_access.refresh_token})
                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=10)
                    if response.status_code != 200:
                        error_msg = f"API Error: {response.status_code} - {response.text}"
                        peppol_access.message_post(body=error_msg)
                        continue  # Exit if the request failed

                    response_data = response.json()
                    new_access_token = response_data.get("access_token")
                    new_refresh_token = response_data.get("refresh_token")

                    if new_access_token and new_refresh_token:
                        peppol_access.sudo().write({
                            "access_token": new_access_token,
                            "refresh_token": new_refresh_token,
                        })
                        peppol_access.message_post(body="Peppol token refreshed successfully.")
                    else:
                        peppol_access.message_post(body="Token refresh failed. No valid tokens received.")

                except requests.RequestException as e:
                    error_msg = f"Request Error: {str(e)}"
                    peppol_access.message_post(body=error_msg)
                    continue

    def get_uuid(self):
        return str(uuid.uuid4())
