# Copyright 2018 ForgeFlow, S.L. (http://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
from odoo import models


class OutstandingStatementWizard(models.TransientModel):
    """Outstanding Statement wizard."""

    _name = "outstanding.statement.wizard"
    _inherit = "statement.common.wizard"
    _description = "Outstanding Statement Wizard"

    def _prepare_statement(self):
        res = super()._prepare_statement()
        return res

    def _print_report(self):
        self.ensure_one()
        data = self._prepare_statement()
        partners = self.env["res.partner"].browse(data["partner_ids"])
        return self.env.ref("partner_statement.action_print_outstanding_statement").report_action(partners, data=data)

    def _export(self):
        """Default export is PDF."""
        return self._print_report()
    
    def action_send_activity_statement(self):
        self.ensure_one()
        data = self._prepare_statement()
        partners = self.env["res.partner"].browse(data["partner_ids"])
        report = self.env.ref("partner_statement.action_print_outstanding_statement")
        template = self.env.ref('partner_statement.email_template_customer_outstanding_statement')

        actions = []

        for partner in partners:
            partner_data = {partner.id: data.get(partner.id)}
            pdf_report, _ = report._render_qweb_pdf([partner.id], data=partner_data)
            pdf_base64 = base64.b64encode(pdf_report)

            # Create attachment
            attachment = self.env['ir.attachment'].create({
                'name': f'Outstanding Statement - {partner.name}.pdf',
                'type': 'binary',
                'datas': pdf_base64,
                'res_model': 'res.partner',
                'res_id': partner.id,
                'mimetype': 'application/pdf',
            })

            # Set up context for wizard
            ctx = {
                'default_model': 'res.partner',
                'default_res_id': partner.id,
                'default_use_template': True,
                'default_template_id': template.id,
                'default_composition_mode': 'comment',
                'force_email': True,
                'default_attachment_ids': [(6, 0, [attachment.id])],
            }

            # Return the action for the first partner only
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(False, 'form')],
                'view_id': False,
                'target': 'new',
                'context': ctx,
            }

        return True

    # def send_email(self):
    #     data = self._prepare_statement()
    #     partners = self.env["res.partner"].browse(data["partner_ids"])
    #     report = self.env.ref("partner_statement.action_print_outstanding_statement")
    #     template = self.env.ref('partner_statement.email_template_customer_outstanding_statement')
    #     for partner in partners:
    #         partner_data = {
    #             partner.id: data.get(partner.id)  #  specific partner id
    #         }
    #         pdf_report, _ = report._render_qweb_pdf([partner.id], data=partner_data)
    #         pdf_base64 = base64.b64encode(pdf_report)

    #         # Create attachment for the partner
    #         attachment = self.env['ir.attachment'].create({
    #             'name': f'Outstanding Statement - {partner.name}.pdf',
    #             'type': 'binary',
    #             'datas': pdf_base64,
    #             'res_model': 'res.partner',
    #             'res_id': partner.id,
    #             'mimetype': 'application/pdf',
    #         })
    #         template.attachment_ids = [(5, 0, 0)] # remove attachement from template
    #         template.attachment_ids = [(4, attachment.id)]  # Attach the partner-specific report
    #         template.send_mail(partner.id, force_send=True)  # Send  email to  partner
