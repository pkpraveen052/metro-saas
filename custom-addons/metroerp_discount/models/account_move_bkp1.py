# -*- coding: utf-8 -*-

from odoo import fields, models, api
import logging
_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    discount_type = fields.Selection([('fixed', 'Fixed'),('percent', 'Percent')], string="Discount Type", default='percent')
    discount_rate = fields.Float(string='Discount')
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)


    @api.onchange('quantity', 'discount', 'price_unit', 'tax_ids', 'discount_type', 'discount_rate')
    def _onchange_price_subtotal(self):
        for line in self:
            if not line.move_id.is_invoice(include_receipts=True):
                continue

            if line.discount_type == 'percent':
                line.discount = line.discount_rate
            elif line.discount_type == 'fixed':
                if line.price_unit > 0:
                    if (line.quantity * line.price_unit) < line.discount_rate:
                        line.discount = 100
                    else:
                        line.discount = (line.discount_rate / (line.quantity * line.price_unit)) * 100
            line.update(line._get_price_total_and_subtotal())
            line.update(line._get_fields_onchange_subtotal())

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info("\ncreate.....")
        _logger.info(vals_list)
        for vals in vals_list:
            _logger.info("Vals ==")
            _logger.info(vals)
            if vals.get('discount_rate', 0.0) > 0 and vals.get('discount_type'):
                _logger.info('Entered If.....')
                if vals.get('discount_type') == 'percent':
                    _logger.info('Entered percent.....')
                    vals.update({'discount': vals['discount_rate']})
                elif vals.get('discount_type') == 'fixed' and vals.get('quantity') and vals.get('price_unit'):
                    _logger.info('Entered fixed.....')
                    vals.update({'discount': (vals['discount_rate'] / (vals['quantity'] * vals['price_unit'])) * 100})
                _logger.info("Final Vals ==")
                _logger.info(vals)
        return super(AccountMoveLine, self).create(vals_list)
