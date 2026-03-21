from odoo import models,fields,api,_
import base64
import logging
_logger = logging.getLogger(__name__)

class AccountPaymentInherited(models.Model):
    _inherit = "account.payment"

    use_assistro = fields.Boolean(related="company_id.use_assistro",string="Use Assistro",readonly=True)

    REPORT_MAPPING = {
        "account.payment": "account.action_report_payment_receipt",
    }

    def action_open_whatsapp_composer(self):
        """Opens the WhatsApp message composer wizard and attaches the PDF."""
        self.ensure_one()
        pdf_attachment = None
        if self._name in self.REPORT_MAPPING:
            try:
                report_action = self.env.ref(self.REPORT_MAPPING[self._name])
                pdf_content, _ = report_action._render_qweb_pdf(self.id)
                pdf_base64 = base64.b64encode(pdf_content)
                
                # ✅ Ensure a valid filename
                if self.state == 'draft':
                    file_name = "Payment_Receipt.pdf"
                else:
                    file_name = f"{(self.name or 'Payment_Receipt').replace('/', '_')}.pdf"
                
                # ✅ Create the attachment
                pdf_attachment = self.env['ir.attachment'].create({
                    'name': file_name,
                    'type': 'binary',
                    'datas': pdf_base64,
                    'res_model': self._name,
                    'res_id': self.id,
                    'mimetype': 'application/pdf',
                })

                _logger.info(f"✅ PDF attachment created: {pdf_attachment.name} (ID: {pdf_attachment.id})")

            except Exception as e:
                _logger.error(f"❌ Failed to generate PDF for {self._name} ({self.id}): {str(e)}")


        # ✅ Open the wizard and link the attachment
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send WhatsApp Message',
            'res_model': 'whatsapp.composer',
            'view_mode': 'form',
            'view_id': False,
            'target': 'new',
            'context': {
                'default_active_model': self._name,
                'default_active_id': self.id,
                'default_attachment_ids': [(6, 0, [pdf_attachment.id])] if pdf_attachment else False,
                'default_template_id': self.env['assistro.whatsapp.template'].search([('is_default', '=', True)], limit=1).id,
            },
        }
    

    def action_open_web_whatsapp_composer(self):
        """Opens the Web WhatsApp message composer wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send WhatsApp Message',
            'res_model': 'portal.share',
            'view_mode': 'form',
            'view_id': False,
            'target': 'new',
            'context': {
                'default_active_model': self._name,
                'default_active_id': self.id,
            },
        }
    