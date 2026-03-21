from odoo import models, fields, api, _

from num2words import num2words


class KsAccountPayment(models.Model):
    _inherit = "account.payment"

    ks_total_amount_in_words = fields.Text(string='Total Amount (In Words)', compute="_set_amount_total_in_words")

    @api.depends('amount')
    def _set_amount_total_in_words(self):
        for rec in self:
            if rec.currency_id:
                rec.ks_total_amount_in_words = rec.currency_id.amount_to_text(rec.amount_total, rec.partner_id.lang)
            else:
                rec.total_amount_in_words = ' '

