# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import requests
import json 
from odoo import api, fields, models, _
_logger = logging.getLogger(__name__)


class WhatsAppComposer(models.TransientModel):
    _name = 'whatsapp.composer'
    _description = 'Send WhatsApp Wizard'

    wa_template_id = fields.Many2one("assistro.whatsapp.template", string="Template",required=True,domain="[('model_id.model', '=', res_model)]")
    partner_ids = fields.Many2many('res.partner', string="Recipients", required=True)
    body = fields.Text(string="Message Body",default="")
    res_model = fields.Char(string='Related Document Model')  # Add this field
    res_id = fields.Integer(string='Related Document ID')     # Add this field


    def action_send_whatsapp(self):
        """Send the WhatsApp message using Assistro API and log the results."""
        config_param = self.env['ir.config_parameter'].sudo()

        access_token = config_param.get_param('assistro.access_token')
        api_url = config_param.get_param('assistro.url')

        if not access_token:
            _logger.error("No access token found. Cannot send WhatsApp message.")
            self.env['whatsapp.log'].create({
                'name': "WhatsApp API Error",
                'status': 'fail',
                'status_code': 401,  # Unauthorized
                'json_data': json.dumps({"error": "No access token found"}),
                'message': "No access token found. Cannot send WhatsApp message.",
                'company_id': self.env.company.id,
            })
            return

        if not api_url:
            _logger.error("No Assistro API URL found. Check the configuration.")
            self.env['whatsapp.log'].create({
                'name': "WhatsApp API Error",
                'status': 'fail',
                'status_code': 400,  # Bad request
                'json_data': json.dumps({"error": "No Assistro API URL found"}),
                'message': "No Assistro API URL found. Check the configuration.",
                'company_id': self.env.company.id,
            })
            return

        # Correct API Endpoint for sending WhatsApp messages
        whatsapp_api_url = f"{api_url}/api/v1/wapushplus/singlePass/message"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        for partner in self.partner_ids:
            if not partner.mobile:
                _logger.warning(f"Skipping {partner.name} as no mobile number is set.")
                self.env['whatsapp.log'].create({
                    'name': f"WhatsApp Message Skipped - {partner.name}",
                    'status': 'fail',
                    'status_code': 400,
                    'json_data': json.dumps({"error": "No mobile number"}),
                    'message': f"Skipping {partner.name} as no mobile number is set.",
                    'company_id': self.env.company.id,
                })
                continue
            
            # Constructing the payload for the message
            payload = {
                "msgs": [
                    {
                        "number": partner.mobile,
                        "message": self.body,
                        "media": []  # Optionally, add media (if needed)
                    }
                ]
            }

            try:
                response = requests.post(whatsapp_api_url, headers=headers, json=payload)
                response_data = response.json()

                log_vals = {
                    'name': f"WhatsApp Message to {partner.name}",
                    'status_code': response.status_code,
                    'json_data': json.dumps(response_data),
                    'company_id': self.env.company.id,
                }

                if response.status_code == 200 and response_data.get("success"):
                    log_vals.update({
                        'status': 'success',
                        'message': f"Message sent successfully to {partner.name} ({partner.mobile}).",
                    })
                    _logger.info(f"WhatsApp message sent successfully to {partner.name} ({partner.mobile}).")
                else:
                    log_vals.update({
                        'status': 'fail',
                        'message': f"Failed to send WhatsApp message to {partner.name}. Response: {response_data}",
                    })
                    _logger.error(f"Failed to send WhatsApp message to {partner.name}. Response: {response_data}")

                # Create a log record
                self.env['whatsapp.log'].create(log_vals)

            except Exception as e:
                # Log any exceptions that occur
                log_vals = {
                    'name': f"WhatsApp Message to {partner.name}",
                    'status': 'fail',
                    'status_code': 500,  # Use 500 for internal errors
                    'json_data': json.dumps({"error": str(e)}),
                    'message': f"Error sending WhatsApp message: {str(e)}",
                    'company_id': self.env.company.id,
                }
                self.env['whatsapp.log'].create(log_vals)
                _logger.error(f"Error sending WhatsApp message: {str(e)}")

        return {"type": "ir.actions.act_window_close"}


    @api.model
    def default_get(self, fields):
        result = super(WhatsAppComposer, self).default_get(fields)
        context = self.env.context

        # Set model and record ID from context
        result['res_model'] = context.get('active_model', False)
        result['res_id'] = context.get('active_id', False)

        if result['res_model'] and result['res_id']:
            record = self.env[result['res_model']].browse(result['res_id'])

            # Set default partner from record if available
            if hasattr(record, 'partner_id'):
                result['partner_ids'] = [(6, 0, [record.partner_id.id])]

            # Find all templates for the model (not just default)
            templates = self.env['assistro.whatsapp.template'].search([
                ('model_id.model', '=', result['res_model'])
            ])

            if templates:
                # Set the default template (if any) or the first template in the list
                default_template = templates.filtered(lambda t: t.is_default)
                result['wa_template_id'] = default_template.id if default_template else templates[0].id
                result['body'] = default_template.body.format(object=record) if default_template else templates[0].body.format(object=record)

        return result

    # @api.onchange('wa_template_id')
    # def _onchange_wa_template_id(self):
    #     """Update the message body when the template is changed."""
    #     if self.wa_template_id:
    #         record = self.env[self.res_model].browse(self.res_id)
            
    #         # Ensure body is a string before formatting
    #         template_body = self.wa_template_id.body or ""

    #         try:
    #             self.body = template_body.format(object=record)
    #         except Exception as e:
    #             self.body = template_body  # Fallback to raw template body if formatting fails
    #             _logger.warning("Error formatting WhatsApp template body: %s", e)

    @api.onchange('wa_template_id')
    def _onchange_wa_template_id(self):
        """Dynamically update the WhatsApp message for both default and custom templates."""
        if not self.wa_template_id:
            return

        # Fetch the record related to the message
        record = self.env[self.res_model].browse(self.res_id)

        if not record:
            self.body = "Error: No record found."
            return

        # Get the base URL for generating share links
        portal_url = record._get_share_url(redirect=True) if hasattr(record, '_get_share_url') else ""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        full_url = f"{base_url}{portal_url}" if portal_url else ""

        # Check if the selected template is a default template
        if self.wa_template_id.is_default:
            # Handle dynamic message formatting for default templates
            if self.res_model == "sale.order":
                formatted_body = (
                    f"Dear {record.partner_id.name}, "
                    f"Your order {record.name} amounting in {record.currency_id.symbol} {record.amount_total} "
                    "has been confirmed. Thank you for your trust!"
                ) if record.state not in ["draft", "sent"] else (
                    f"Dear {record.partner_id.name}, "
                    f"Your quotation {record.name} amounting in {record.currency_id.symbol} {record.amount_total} "
                    "is ready for your review. Please confirm to proceed."
                )

            elif self.res_model == "account.move":
                formatted_body = (
                    f"Dear {record.partner_id.name}, "
                    f"Your invoice {record.name} amounting in {record.currency_id.symbol} {record.amount_total} "
                    "is ready for payment. Please find the details below."
                ) if record.move_type == "out_invoice" else (
                    f"Dear {record.partner_id.name}, "
                    f"Your bill {record.name} amounting in {record.currency_id.symbol} {record.amount_total} "
                    "has been received. Please review the details."
                ) if record.move_type == "in_invoice" else (
                    f"Dear {record.partner_id.name}, your document {record.name} is available."
                )

            elif self.res_model == "stock.picking":
                formatted_body = (
                    f"Dear {record.partner_id.name},\n\n"
                    f"We are glad to inform you that your delivery order {record.name} has been confirmed.\n\n"
                    "Please find your delivery order attached for more details.\n\n"
                    "Thank you."
                ) if record.picking_type_code == "outgoing" else (
                    f"Dear {record.partner_id.name},\n\n"
                    f"Your incoming shipment {record.name} has been received successfully.\n\n"
                    "Please review the details in the attached document.\n\n"
                    "Thank you."
                ) if record.picking_type_code == "incoming" else (
                    f"Dear {record.partner_id.name}, your stock movement {record.name} is recorded."
                )

            elif self.res_model == "purchase.order":
                # Handle RFQ and Purchase Order template logic
                if record.state in ['draft', 'sent']:
                    formatted_body = (
                        f"Dear {record.partner_id.name},\n"
                        f"Your Request for Quotation (RFQ) {record.name} amounting in {record.currency_id.symbol} {record.amount_total} "
                        "is ready for your review. Please confirm to proceed."
                    )
                else:
                    formatted_body = (
                        f"Dear {record.partner_id.name},\n"
                        f"Your purchase order {record.name} amounting in {record.currency_id.symbol} {record.amount_total} "
                        "has been confirmed. Thank you for your business!"
                    )
            else:
                # For other models or unknown ones
                formatted_body = "Enter your message here."

        else:
            # For custom/new templates, use the body from wa_template_id with formatting
            formatted_body = self.wa_template_id.body if self.wa_template_id.body else "Enter your message here."
            # Replace placeholders like {object} with the actual record data in the template
            formatted_body = formatted_body.format(object=record, portal_url=full_url)

        # Append portal link if available
        formatted_body = f"{formatted_body}\n\nPlease access your document using the link below:\n{full_url}" if full_url else formatted_body

        # Add the branding footer in bold
        branding_footer = "*Powered by Metro Accounting System*"
        self.body = f"{formatted_body}\n\n{branding_footer}"


                                
                            