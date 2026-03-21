# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import requests
import json
import base64
import re
from odoo import api, fields, models, _
_logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB limit

class WhatsAppComposer(models.TransientModel):
    _name = 'whatsapp.composer'
    _description = 'Send WhatsApp Wizard'

    wa_template_id = fields.Many2one("assistro.whatsapp.template", string="Template",required=True,domain="[('model_id.model', '=', res_model)]")
    partner_ids = fields.Many2many('res.partner', string="Recipients", required=True)
    body = fields.Text(string="Message Body",default="")
    res_model = fields.Char(string='Related Document Model')  # Add this field
    res_id = fields.Integer(string='Related Document ID')     # Add this field
    attachment_ids = fields.Many2many('ir.attachment', string="WhatsApp PDF Attachment")


    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB limit

    def _validate_phone_number(self, number):
        """Validate and format phone numbers for India, Singapore, and international numbers."""
        if not number:
            return None

        # Remove non-numeric characters except '+'
        number = re.sub(r'[^\d+]', '', number)

        # ✅ Ensure +91 or 91 for Indian numbers
        if number.startswith("+91"):
            number = number[1:]  # Remove the '+'
        if number.startswith("91") and len(number) > 10:
            number = number[2:]  # Remove '91' if present

        if len(number) == 10:  # If it's exactly 10 digits, assume Indian number and add '91' prefix
            return "91" + number

        # ✅ Ensure +65 or 65 for Singapore numbers
        if number.startswith("+65"):
            number = number[1:]  # Remove '+'
        if len(number) == 8:  # If it's exactly 8 digits, assume Singapore number and add '65' prefix
            return "65" + number
        elif number.startswith("65") and len(number) == 10:
            return number  # Already valid Singapore number

        # ✅ Keep other international numbers unchanged
        if len(number) >= 10:
            return number  

        return None  # Invalid number


    def show_invoice_feature_popup(self):

        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Feature Restricted',
                'res_model': 'invoice.popup.wizard',
                'view_mode': 'form',
                'target': 'new',
            }

    def action_send_whatsapp(self):
        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user') and self.env.context.get('active_model') == 'account.move':
            return self.show_invoice_feature_popup()
        
        """Send WhatsApp messages using Assistro API with attachments and proper logging."""
        config_param = self.env["ir.config_parameter"].sudo()
        access_token = config_param.get_param("assistro.access_token")
        api_url = config_param.get_param("assistro.url")

        related_record = self.env[self.res_model].browse(self.res_id) if self.res_model and self.res_id else None

        if not access_token:
            message = "No access token found. Cannot send WhatsApp message."
            _logger.error(message)
            if related_record:
                related_record.message_post(body=message, message_type="comment", subtype_xmlid="mail.mt_note")
            return

        if not api_url:
            message = "No Assistro API URL found. Check the configuration."
            _logger.error(message)
            if related_record:
                related_record.message_post(body=message, message_type="comment", subtype_xmlid="mail.mt_note")
            return

        whatsapp_api_url = f"{api_url}/api/v1/wapushplus/singlePass/message"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        branding_footer = "*Powered by Metro Accounting System*"
        skipped_partners = []
        attachments_data = []

        for attachment in self.attachment_ids:
            if not attachment.datas:
                _logger.warning(f"⚠️ Skipping empty attachment: {attachment.name}")
                continue

            file_size = len(attachment.datas) * 3 // 4  # Approximate actual size after decoding
            if file_size > MAX_FILE_SIZE:
                _logger.warning(f"⚠️ Skipping {attachment.name}: File too large ({file_size} bytes)")
                continue

            try:
                encoded_file = attachment.datas.decode("utf-8")
                mimetype = attachment.mimetype if attachment.mimetype else "application/octet-stream"
                attachments_data.append({
                    "media_base64": encoded_file,
                    "file_name": attachment.name,
                    "mimetype": mimetype
                })

            except Exception as e:
                _logger.error(f"Failed to read attachment {attachment.name}: {str(e)}")

        success_count = 0
        for partner in self.partner_ids:
            mobile = partner.mobile and "".join(partner.mobile.split())
            phone = partner.phone and "".join(partner.phone.split())

            mobile = re.sub(r'[^0-9]', '', mobile) if mobile else None
            phone = re.sub(r'[^0-9]', '', phone) if phone else None

            valid_number = None
            if mobile:
                valid_number = self._validate_phone_number(mobile)
            elif phone:
                valid_number = self._validate_phone_number(phone)

            if not valid_number:
                message = f"Skipping {partner.name}: Invalid phone number."
                _logger.warning(message)
                if related_record:
                    related_record.message_post(body=message, message_type="comment", subtype_xmlid="mail.mt_note")
                continue

            full_message = f"{self.body}\n\n{branding_footer}"
            _logger.info(f"Sending WhatsApp message to: {partner.name} ({valid_number})")

            payload = {
                "msgs": [
                    {
                        "number": valid_number,
                        "message": full_message,
                        "media": attachments_data if attachments_data else []
                    }
                ]
            }

            try:
                response = requests.post(whatsapp_api_url, headers=headers, json=payload)

                try:
                    response_data = response.json()
                except Exception:
                    _logger.error(f"Invalid JSON Response from WhatsApp API: {response.text}")
                    response_data = {"error": "Invalid JSON response", "success": False}

                if response.status_code == 200 and response_data.get("success"):
                    success_count += 1
                    success_msg = f"WhatsApp message sent successfully to {partner.name} ({valid_number})."
                    _logger.info(success_msg)
                    if related_record:
                        related_record.message_post(body=success_msg, message_type="comment", subtype_xmlid="mail.mt_note")

                    self.env['whatsapp.log'].create({
                        'name': f"WhatsApp Message to {partner.name}",
                        'status': 'success',
                        'status_code': response.status_code,
                        'json_data': json.dumps(response_data),
                        'message': success_msg,
                        'company_id': self.env.company.id,
                    })
                else:
                    error_msg = f"Failed to send WhatsApp message to {partner.name}. Response: {response_data}"
                    _logger.error(error_msg)
                    if related_record:
                        related_record.message_post(body=error_msg, message_type="comment", subtype_xmlid="mail.mt_note")

                    self.env['whatsapp.log'].create({
                        'name': f"WhatsApp Message to {partner.name}",
                        'status': 'fail',
                        'status_code': response.status_code,
                        'json_data': json.dumps(response_data),
                        'message': error_msg,
                        'company_id': self.env.company.id,
                    })

            except Exception as e:
                error_msg = f"Error sending WhatsApp message to {partner.name}: {str(e)}"
                _logger.error(error_msg)
                if related_record:
                    related_record.message_post(body=error_msg, message_type="comment", subtype_xmlid="mail.mt_note")

                self.env['whatsapp.log'].create({
                    'name': f"WhatsApp Message to {partner.name}",
                    'status': 'fail',
                    'status_code': 500,
                    'json_data': json.dumps({"error": str(e)}),
                    'message': error_msg,
                    'company_id': self.env.company.id,
                })


        if success_count > 0:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Success",
                    "message": f"{success_count} WhatsApp message(s) sent successfully!",
                    "type": "success",
                    "sticky": False,
                    "next": {"type": "ir.actions.act_window_close"} 
                }
            }

        

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

            elif self.res_model == "progressive.billing.qt":
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

            elif self.res_model == "account.payment":
                formatted_body = (
                    f"Dear {record.partner_id.name}, "
                    f"Thank you for your payment of {record.currency_id.symbol} {record.amount} to {record.company_id.name}.\n"
                    "Do not hesitate to contact us if you have any questions."
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

        self.body = formatted_body


                                
                            