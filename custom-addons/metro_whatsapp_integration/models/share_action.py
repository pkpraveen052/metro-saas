from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import urllib.parse as urllib
from urllib.parse import quote  # Updated import
import re
import json
import requests
import base64
import logging
_logger = logging.getLogger(__name__)
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB limit

class PortalShare(models.TransientModel):
    _inherit = 'portal.share'


    wa_template_id = fields.Many2one("assistro.whatsapp.template", string="Template",domain="[('model_id.model', '=', res_model)]")
    body = fields.Text(string="Message Body")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    use_assistro = fields.Boolean(related="company_id.use_assistro",string="Use Assistro",readonly=False)
    res_model = fields.Char(string='Related Document Model')  # Add this field
    res_id = fields.Integer(string='Related Document ID')     # Add this field
    attachment_ids = fields.Many2many('ir.attachment', string="WhatsApp PDF Attachment")

    @api.model
    def default_get(self, fields):
        result = super(PortalShare, self).default_get(fields)
        result['res_model'] = self._context.get('active_model', False)
        result['res_id'] = self._context.get('active_id', False)

        if result['res_model'] and result['res_id']:
            record = self.env[result['res_model']].browse(result['res_id'])
            result['partner_ids'] = record.partner_id

        company_id = self.env.company.id

        templates = self.env['assistro.whatsapp.template'].search([
            ('model_id.model', '=', result['res_model']),
            ('company_id', 'in', [False, company_id])   
        ])

        if templates:
            default_template = templates.filtered(lambda t: t.is_default and t.company_id.id in [False, company_id])
            default_template = default_template[:1]  

            selected_template = default_template or templates[0]

            result['wa_template_id'] = selected_template.id
            result['body'] = selected_template.body.format(object=record)

        return result
    

    def show_invoice_feature_popup(self):

        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Feature Restricted',
                'res_model': 'invoice.popup.wizard',
                'view_mode': 'form',
                'target': 'new',
            }


    def action_send_mail(self):
        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user') and self.env.context.get('active_model') == 'account.move':
            return self.show_invoice_feature_popup()

        ctx = self._context or {}
        for partner in self.partner_ids:
            if not partner.email:
                raise ValidationError("Please add an email address for the customer: %s" % partner.name)
        if ctx.get('active_model', False) == 'sale.order':
            sale_obj = self.env['sale.order'].browse(ctx['active_id'])
            if sale_obj.state == 'draft':
                sale_obj.write({'state': 'sent'})
        return super(PortalShare, self).action_send_mail()
    

    def action_send_whatsapp(self):
        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user') and self.env.context.get('active_model') == 'account.move':
            return self.show_invoice_feature_popup()
        
        ctx = self._context or {}
        if len(self.partner_ids) > 1:
            raise ValidationError("Please Select Only One Recipients!")
        if not self.partner_ids.mobile and not self.partner_ids.phone:
            raise ValidationError("Please Add Mobile or Phone Number!")

        phone, mobile = '', ''
        if self.partner_ids.mobile:
            mobile = "".join(self.partner_ids.mobile.split())
            mobile = re.sub(r'[^a-zA-Z0-9]', '', mobile)
        elif self.partner_ids.phone:
            phone = "".join(self.partner_ids.phone.split())
            phone = re.sub(r'[^a-zA-Z0-9]', '', phone)

        def validate_string(input_string):
            pattern = r'^\d{8}$|^\d{10}$'
            if re.match(pattern, input_string):
                if len(input_string) == 8:
                    input_string = '65' + input_string
                return input_string
            else:
                return None

        if mobile:
            mobile = validate_string(mobile)
            if not mobile:
                raise ValidationError("Please add valid mobile!")
        elif phone:
            phone = validate_string(phone)
            if not phone:
                raise ValidationError("Please add valid mobile!")

        common_message = 'Please access your documents using below link'
        # ✅ Use \n for line breaks instead of %0a
        message_string = _('Dear') + ' ' + self.partner_ids.name + ',' + '\n\n' + common_message + '\n' + 'Link : ' + self.share_link
        if self.note:
            message_string += '\n\n' + 'Note : ' + self.note
        message_string += '\n\n' + 'Powered By *Metro Accounting System*'

        encoded_message = quote(message_string)  # ✅ Let quote() handle encoding

        if mobile:
            link = "https://api.whatsapp.com/send?phone=" + mobile
        else:
            link = "https://api.whatsapp.com/send?phone=" + phone

        action_url = {
            'type': 'ir.actions.act_url',
            'url': link + "&text=" + encoded_message,
            'target': 'new',
        }
        action_close = {'type': 'ir.actions.act_window_close'}
        if ctx.get('active_model', False) == 'sale.order':
            sale_obj = self.env['sale.order'].browse(ctx['active_id'])
            if sale_obj.state == 'draft':
                sale_obj.write({'state': 'sent'})

        return {
            'type': 'ir.actions.act_multi',
            'actions': [action_url, action_close]
        }
            
        


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

    def action_send_assistro_whatsapp(self):
        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user') and self.env.context.get('active_model') == 'account.move':
            return self.show_invoice_feature_popup()
        
        """Send WhatsApp messages using Assistro API with multiple attachments and proper logging."""
        config_param = self.env["ir.config_parameter"].sudo()
        access_token = config_param.get_param("assistro.access_token")
        api_url = config_param.get_param("assistro.url")

        related_record = self.env[self.res_model].browse(self.res_id) if self.res_model and self.res_id else None

        if not access_token:
            message = "No access token found. Cannot send WhatsApp message."
            _logger.error(message)
            if related_record:
                related_record.message_post(body=message, message_type="comment", subtype_xmlid="mail.mt_note")

            self.env["whatsapp.log"].create({
                "name": "WhatsApp API Error",
                "status": "fail",
                "status_code": 401,
                "json_data": json.dumps({"error": "No access token found"}),
                "message": message,
                "company_id": self.env.company.id,
            })
            return

        if not api_url:
            message = "No Assistro API URL found. Check the configuration."
            _logger.error(message)
            if related_record:
                related_record.message_post(body=message, message_type="comment", subtype_xmlid="mail.mt_note")

            self.env["whatsapp.log"].create({
                "name": "WhatsApp API Error",
                "status": "fail",
                "status_code": 400,
                "json_data": json.dumps({"error": "No Assistro API URL found"}),
                "message": message,
                "company_id": self.env.company.id,
            })
            return

        whatsapp_api_url = f"{api_url}/api/v1/wapushplus/singlePass/message"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        branding_footer = "*Powered by Metro Accounting System*"
        attachments_data = []

        for attachment in self.attachment_ids:
            
            if not attachment.datas:
                _logger.warning(f"Skipping empty attachment: {attachment.name}")
                continue

            file_size = len(attachment.datas)
            if file_size > MAX_FILE_SIZE:
                _logger.warning(f"Skipping {attachment.name}: File too large ({file_size} bytes)")
                continue

            try:
                encoded_file = attachment.datas.decode("utf-8")  
                mimetype = attachment.mimetype if attachment.mimetype else "application/octet-stream"

                file_name = attachment.name if attachment.name else "attachment.pdf"

                attachments_data.append({
                    "media_base64": encoded_file,
                    "file_name": file_name,
                    "mimetype": mimetype
                })
                _logger.info(f"Processed attachment: {file_name} (Size: {file_size} bytes, Type: {mimetype})")

            except Exception as e:
                _logger.error(f"Failed to encode attachment {file_name}: {str(e)}")

        success_count = 0
        for partner in self.partner_ids:
            phone_number = partner.mobile or partner.phone or ""
            validated_number = self._validate_phone_number(phone_number)

            if not validated_number:
                message = f"⚠️ Skipping {partner.name}: Invalid or missing phone number."
                _logger.warning(message)
                if related_record:
                    related_record.message_post(body=message, message_type="comment", subtype_xmlid="mail.mt_note")

                self.env["whatsapp.log"].create({
                    "name": f"WhatsApp Message Skipped - {partner.name}",
                    "status": "fail",
                    "status_code": 400,
                    "json_data": json.dumps({"error": "Invalid phone number"}),
                    "message": message,
                    "company_id": self.env.company.id,
                })
                continue

            full_message = f"{self.body}\n\n{branding_footer}"
            _logger.info(f"Sending WhatsApp message to: {partner.name} ({validated_number})")
           
            payload = {
                "msgs": [
                    {
                        "number": validated_number,
                        "message": full_message,
                        "media": attachments_data if attachments_data else []
                    }
                ]
            }

            try:
                response = requests.post(whatsapp_api_url, headers=headers, json=payload)

                try:
                    response_data = response.json()
                    _logger.info(f"🔹 Full API Response: {json.dumps(response_data, indent=2)}")
                except Exception:
                    _logger.error(f"Invalid JSON Response from WhatsApp API: {response.text}")
                    response_data = {"error": "Invalid JSON response", "success": False}

                if response.status_code == 200 and response_data.get("success"):
                    success_count += 1
                    success_msg = f"WhatsApp message sent successfully to {partner.name} ({validated_number})."
                    _logger.info(success_msg)
                    if related_record:
                        related_record.message_post(body=success_msg, message_type="comment", subtype_xmlid="mail.mt_note")

                    self.env["whatsapp.log"].create({
                        "name": f"WhatsApp Message to {partner.name}",
                        "status": "success",
                        "status_code": response.status_code,
                        "json_data": json.dumps(response_data),
                        "message": success_msg,
                        "company_id": self.env.company.id,
                    })

                else:
                    error_msg = f"Failed to send WhatsApp message to {partner.name}. Response: {response_data}"
                    _logger.error(error_msg)
                    if related_record:
                        related_record.message_post(body=error_msg, message_type="comment", subtype_xmlid="mail.mt_note")

                    self.env["whatsapp.log"].create({
                        "name": f"WhatsApp Message to {partner.name}",
                        "status": "fail",
                        "status_code": response.status_code,
                        "json_data": json.dumps(response_data),
                        "message": error_msg,
                        "company_id": self.env.company.id,
                    })

            except Exception as e:
                error_msg = f"Error sending WhatsApp message to {partner.name}: {str(e)}"
                _logger.error(error_msg)
                if related_record:
                    related_record.message_post(body=error_msg, message_type="comment", subtype_xmlid="mail.mt_note")

                self.env["whatsapp.log"].create({
                    "name": f"WhatsApp Message to {partner.name}",
                    "status": "fail",
                    "status_code": 500,
                    "json_data": json.dumps({"error": str(e)}),
                    "message": error_msg,
                    "company_id": self.env.company.id,
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
                    f"Dear {record.partner_id.name},\n\n"
                    f"Thank you for your payment of {record.currency_id.symbol} {record.amount} to {record.company_id.name}.\n\n"
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

        # Add the branding footer in bold
        self.body = formatted_body

