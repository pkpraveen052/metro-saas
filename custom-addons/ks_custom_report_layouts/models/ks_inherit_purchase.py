from odoo import models, fields, api, _

from num2words import num2words

class KsPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    ks_total_amount_in_words = fields.Text(string='Total Amount (In Words)', compute="_set_amount_total_in_words")

    @api.depends('amount_total')
    def _set_amount_total_in_words(self):
        for rec in self:
            if rec.currency_id:
                rec.ks_total_amount_in_words = rec.currency_id.amount_to_text(rec.amount_total, rec.partner_id.lang)
            else:
                rec.total_amount_in_words = ''
    def action_rfq_send(self):
        result = super(KsPurchaseOrder, self).action_rfq_send()
        company_id = self.company_id.id if self.company_id else self.env.company.id
        if self.state == 'purchase':
            report_ui_id = self.env['ks.report.configuration'].search([("ks_record_status", "=", 'purchase_order'), ("company_id", "=", company_id)], limit=1)
        else:
            report_ui_id = self.env['ks.report.configuration'].search([("ks_record_status", "=", 'RFQ'), ("company_id", "=", company_id)], limit=1)
        result['context']['ks_mail_cc'] = report_ui_id.ks_emailcc_partner_id.mapped('email') if len(
            report_ui_id.ks_emailcc_partner_id.mapped('email')) else self.company_id.ks_emailcc_partner_id.mapped('email')

        return result