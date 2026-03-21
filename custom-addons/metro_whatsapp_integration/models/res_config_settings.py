# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError,UserError
import requests
import logging
_logger = logging.getLogger(__name__)
from datetime import timedelta



class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    
    url = fields.Char(string="URL", config_parameter="assistro.url")
    client_id = fields.Char(string="Client ID", config_parameter="assistro.client_id", default="6")
    client_secret = fields.Char(string="Client Secret", config_parameter="assistro.client_secret")
    redirect_url = fields.Char(string="Redirect URL", config_parameter="assistro.redirect_url")
    use_assistro = fields.Boolean(related="company_id.use_assistro",readonly=False,string="Use Assistro")
    auth_code = fields.Char(string="Auth Code",config_parameter="assistro.auth_code",readonly=False)
    access_token = fields.Char(string="Access Token",config_parameter="assistro.access_token",readonly=False)
    refresh_token = fields.Char(string="Refresh Token",config_parameter="assistro.refresh_token",readonly=False)

    
    def signup_url_action(self):
        base_url = self.url or 'https://app.assistro.co'
        return {
            'type': 'ir.actions.act_url',
            'url': f"{base_url.rstrip('/')}/register",
            'target': 'new',
        }
    
    def generate_oauth_url(self):
        """Generate the custom OAuth URL using configured values."""
        # Fetch values from the form
        url = self.url
        client_id = self.client_id
        redirect_url = self.redirect_url

        if not (url and client_id and redirect_url):
            raise ValidationError("Please configure the URL, Client ID, and Redirect URL in the settings.")

        # Construct the OAuth URL
        oauth_url = (
            f"{url}/oauth/authorize?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_url}&"
            f"response_type=code&"
            f"scope=all&"
            f"integration_name=customall&"
            f"integration_name=custom"
        )
        return {
                'type': 'ir.actions.act_url',
                'target': 'new',  # Opens in a new tab
                'url': oauth_url,  # Replace with your desired URL
            }
    
    
    def fetch_tokens(self):
        """
        Fetch access_token and refresh_token using the authorization code.
        """
        self.ensure_one()  # Ensure only one record is processed
        
        # Fetch stored values from res.config.settings
        client_id = self.client_id
        client_secret = self.client_secret
        auth_code = self.auth_code
        redirect_url = self.redirect_url
        url = self.url

        if not client_id or not client_secret or not auth_code or not redirect_url:
            raise UserError("Missing required credentials. Please check your configuration.")

        token_url = f"{url.rstrip('/')}/oauth/token"

        payload = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': auth_code,
            'redirect_uri': redirect_url,
            'grant_type': 'authorization_code',
        }

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        try:
            response = requests.post(token_url, data=payload, headers=headers)
            response_data = response.json()

            if response.status_code == 200 and 'access_token' in response_data:
                access_token = response_data.get('access_token')
                refresh_token = response_data.get('refresh_token')

                # Save tokens in ir.config_parameter
                config_param = self.env['ir.config_parameter'].sudo()
                config_param.set_param('assistro.access_token', access_token)
                config_param.set_param('assistro.refresh_token', refresh_token)

                _logger.info("Access token and refresh token successfully saved.")

                return {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                }
            else:
                _logger.error("Failed to fetch tokens: %s", response_data)
                raise UserError("Unable to fetch tokens. Error: %s" % response_data.get('error_description', 'Unknown error'))

        except Exception as e:
            _logger.exception("Error during token fetching: %s", e)
            raise UserError("An error occurred while fetching tokens: %s" % str(e))
        



    # def refresh_tokens(self):
    #     for record in self:
    #         record._refresh_token_logic()

    def _refresh_token_logic(self):
        """Refresh access_token and refresh_token using the stored refresh_token."""
        config_param = self.env['ir.config_parameter'].sudo()

        client_id = config_param.get_param('assistro.client_id')
        client_secret = config_param.get_param('assistro.client_secret')
        refresh_token = config_param.get_param('assistro.refresh_token')
        url = config_param.get_param('assistro.url')

        if not client_id or not client_secret or not refresh_token or not url:
            raise UserError("Missing required credentials. Please check system parameters.")

        token_url = f"{url.rstrip('/')}/oauth/token"
        payload = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        try:
            response = requests.post(token_url, data=payload, headers=headers)
            response_data = response.json()

            if response.status_code == 200 and 'access_token' in response_data:
                new_access_token = response_data.get('access_token')
                new_refresh_token = response_data.get('refresh_token')

                # Save refreshed tokens globally
                config_param.set_param('assistro.access_token', new_access_token)
                config_param.set_param('assistro.refresh_token', new_refresh_token)

                _logger.info("Access token successfully refreshed.")
                return {'access_token': new_access_token, 'refresh_token': new_refresh_token}
            else:
                _logger.error("Failed to refresh token: %s", response_data)
                raise UserError("Unable to refresh token. Error: %s" % response_data.get('error_description', 'Unknown error'))

        except Exception as e:
            _logger.exception("Error during token refresh: %s", e)
            raise UserError("An error occurred while refreshing tokens: %s" % str(e))
        
        
    @api.model
    def _cron_refresh_whatsapp_token(self):
        """Cron job to refresh the WhatsApp API token daily, using global configuration."""
        config_param = self.env['ir.config_parameter'].sudo()

        client_id = config_param.get_param('assistro.client_id')
        client_secret = config_param.get_param('assistro.client_secret')
        refresh_token = config_param.get_param('assistro.refresh_token')
        url = config_param.get_param('assistro.url')

        if not client_id or not client_secret or not refresh_token or not url:
            _logger.error("Missing required credentials in system parameters. Token refresh failed.")
            return

        token_url = f"{url.rstrip('/')}/oauth/token"
        payload = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        try:
            import requests
            response = requests.post(token_url, data=payload, headers=headers)
            response_data = response.json()

            if response.status_code == 200 and 'access_token' in response_data:
                new_access_token = response_data.get('access_token')
                new_refresh_token = response_data.get('refresh_token')

                # Store the refreshed tokens
                config_param.set_param('assistro.access_token', new_access_token)
                config_param.set_param('assistro.refresh_token', new_refresh_token)

                _logger.info("Access token successfully refreshed via cron job.")
            else:
                _logger.error("Failed to refresh token: %s", response_data)
        except Exception as e:
            _logger.exception("Error during token refresh: %s", e)


    def action_refresh_token(self):
        """
        Button action to manually refresh the token.
        """
        self._refresh_token_logic()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    

    

    