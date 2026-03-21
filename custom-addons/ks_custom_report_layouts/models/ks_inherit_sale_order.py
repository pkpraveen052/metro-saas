from odoo import api, fields, models, tools, _
import logging
from odoo.tools.image import image_data_uri

_logger = logging.getLogger(__name__)

try:
    from num2words import num2words
except ImportError:
    _logger.warning("The num2words python library is not installed, amount-to-text features won't be fully available.")
    num2words = None


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    total_amount_in_words = fields.Text(string='Total Amount (In Words)', compute="_set_amount_total_in_words")

    @api.depends('amount_total')
    def _set_amount_total_in_words(self):
        for rec in self:
            if rec.currency_id:
                rec.total_amount_in_words = rec.currency_id.amount_to_text(rec.amount_total, rec.partner_id.lang)
            else:
                rec.total_amount_in_words = ''
    def action_quotation_send(self):
        result = super(SaleOrder, self).action_quotation_send()
        company_id = self.company_id.id if self.company_id else self.env.company.id
        report_ui_id = self.env['ks.report.configuration'].search([("ks_record_status", "=", 'sale_order'),("company_id", "=", company_id)], limit=1)
        result['context']['ks_mail_cc'] = report_ui_id.ks_emailcc_partner_id.mapped('email') if len(report_ui_id.ks_emailcc_partner_id.mapped('email')) else self.company_id.ks_emailcc_partner_id.mapped('email')
        return result
    

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'


    def _get_line_headers_for_product(self):
        """Return section/note lines above this product line until previous product line.
        Handles missing, duplicate, or same sequence numbers automatically.
        """
        self.ensure_one()
        result = []

        order_lines = self.order_id.order_line

        # Collect valid sequence values
        seq_values = [l.sequence for l in order_lines if l.sequence]

        # Detect invalid sequence cases (empty, duplicate, or all same)
        if not seq_values or len(seq_values) != len(set(seq_values)):
            # Temporarily resequence lines in memory (not writing to DB)
            resequenced_lines = []
            sequence = 1
            for line in order_lines.sorted(key=lambda l: l.id):
                line.sequence = sequence
                resequenced_lines.append(line)
                sequence += 1
            order_lines = resequenced_lines

        # Now find preceding lines
        preceding_lines = [l for l in order_lines if l.sequence < self.sequence]
        preceding_lines = sorted(preceding_lines, key=lambda l: l.sequence, reverse=True)

        for line in preceding_lines:
            if line.display_type:  # section/note
                result.append(line)
            else:  # stop at previous product
                break

        return list(reversed(result))  # maintain sale order order

    

    # def _get_headers_for_do(self):
    #     """Return section/note lines immediately above this product line,
    #     stopping at the previous product line."""
    #     self.ensure_one()
    #     preceding_lines = self.order_id.order_line.filtered(
    #         lambda l: l.sequence < self.sequence
    #     ).sorted(key=lambda l: l.sequence, reverse=True)

    #     headers = []
    #     for line in preceding_lines:
    #         if line.display_type:
    #             headers.append(line)
    #         else:
    #             break
    #     return list(reversed(headers))


class KsResCurrency(models.Model):
    _inherit = 'res.currency'

    def amount_to_text(self, amount, language=False):
        self.ensure_one()

        def _num2words(number, lang):
            try:
                return num2words(number, lang=lang).title()
            except NotImplementedError:
                return num2words(number, lang='en').title()

        if num2words is None:
            logging.getLogger(__name__).warning("The library 'num2words' is missing, cannot render textual amounts.")
            return ""

        formatted = "%.{0}f".format(self.decimal_places) % amount
        parts = formatted.partition('.')
        integer_value = int(parts[0])
        fractional_value = int(parts[2] or 0)
        if language:
            lang = language
        else:
            lang = tools.get_lang(self.env).iso_code
        amount_words = tools.ustr('{amt_value} {amt_word}').format(
            amt_value=_num2words(integer_value, lang=lang),
            amt_word=self.currency_unit_label,
        )
        if not self.is_zero(amount - integer_value):
            amount_words += ' ' + _('and') + tools.ustr(' {amt_value} {amt_word}').format(
                amt_value=_num2words(fractional_value, lang=lang),
                amt_word=self.currency_subunit_label,
            )
        return amount_words