# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super(PosPaymentMethod, self)._get_payment_terminal_selection() + [('paynow_static', 'Paynow Static')]