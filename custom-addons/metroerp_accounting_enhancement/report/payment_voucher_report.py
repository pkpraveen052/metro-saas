# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.exceptions import UserError
from functools import lru_cache


class PaymentVoucherReport(models.AbstractModel):
    _name = 'report.metroerp_accounting_enhancement.payment_voucher_report'
    _description = 'Payment Voucher Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        if docs and docs.move_type not in ['out_invoice', 'out_refund','in_invoice','in_refund']:
            return {
                'doc_ids': docids,
                'doc_model': 'account.move',
                'docs': docs,
            }
        else:
            raise UserError(_(""" Only Journal entries could be printed. """))
