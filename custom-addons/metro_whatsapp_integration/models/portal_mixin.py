from odoo import models, api, _
import base64
import logging
_logger = logging.getLogger(__name__)

class PortalMixin(models.AbstractModel):
    _inherit = "portal.mixin"

    REPORT_MAPPING = {
        "sale.order": "sale.action_report_saleorder",
        "account.move": "account.account_invoices",
        "purchase.order": "purchase.action_report_purchase_order",
        "stock.picking": "stock.action_report_delivery",
    }

    @api.model
    def action_share(self):
        action = self.env["ir.actions.actions"]._for_xml_id("portal.portal_share_action")

        # ✅ Get active record
        active_id = self.env.context.get("active_id")
        active_model = self.env.context.get("active_model")
        record = self.env[active_model].browse(active_id) if active_id and active_model else None

        # ✅ Generate PDF and attach it
        attachment = None
        if record and active_model in self.REPORT_MAPPING:
            try:
                report_action = self.env.ref(self.REPORT_MAPPING[active_model])
                pdf_content, _ = report_action._render_qweb_pdf(active_id)
                pdf_base64 = base64.b64encode(pdf_content)
                file_name = f"{record.name.replace('/', '_')}.pdf"

                # ✅ Create the attachment
                attachment = self.env["ir.attachment"].create({
                    "name": file_name,
                    "type": "binary",
                    "datas": pdf_base64,
                    "res_model": active_model,
                    "res_id": active_id,
                    "mimetype": "application/pdf",
                })
                _logger.info(f"✅ PDF attachment created: {attachment.name} (ID: {attachment.id})")

            except Exception as e:
                _logger.error(f"❌ Failed to generate PDF for {active_model} ({active_id}): {str(e)}")

        # ✅ Add attachment to the wizard
        action["context"] = {
            "active_id": active_id,
            "active_model": active_model,
            "default_attachment_ids": [(6, 0, [attachment.id])] if attachment else False,
        }
        return action
