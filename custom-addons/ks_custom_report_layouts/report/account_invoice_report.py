# -*- coding: utf-8 -*-

from odoo import models, fields, api

from functools import lru_cache

class KsReportInvoiceWithoutPayment(models.AbstractModel):
    _name = 'report.ks_custom_report_layouts.ks_custom_report_invoice'
    _description = 'Account report without payment lines'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        qr_code_urls = {}
        for invoice in docs:
            if invoice.display_qr_code:
                new_code_url = invoice.generate_qr_code()
                if new_code_url:
                    qr_code_urls[invoice.id] = new_code_url

        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
            'qr_code_urls': qr_code_urls,
        }

class KsReportInvoiceWithoutPaymentDplct(models.AbstractModel):
    _name = 'report.ks_custom_report_layouts.ks_duplicate_report_invoice'
    _description = 'Duplicate Account report without payment lines'
    _inherit = 'report.ks_custom_report_layouts.ks_custom_report_invoice'

    @api.model
    def _get_report_values(self, docids, data=None):
        rslt = super()._get_report_values(docids, data)
        return rslt

class KsReportInvoiceWithPayment(models.AbstractModel):
    _name = 'report.ks_custom_report_layouts.ks_invoice_report_with_payments'
    _description = 'Account report with payment lines'
    _inherit = 'report.ks_custom_report_layouts.ks_custom_report_invoice'

    @api.model
    def _get_report_values(self, docids, data=None):
        rslt = super()._get_report_values(docids, data)
        rslt['report_type'] = data.get('report_type') if data else ''
        return rslt

class KsReportInvoiceWithPaymentdplct(models.AbstractModel):
    _name = 'report.ks_custom_report_layouts.ks_invoice_with_payments_dplct'
    _description = 'Duplicate Account report with payment lines'
    _inherit = 'report.ks_custom_report_layouts.ks_invoice_report_with_payments'

    @api.model
    def _get_report_values(self, docids, data=None):
        rslt = super()._get_report_values(docids, data)
        return rslt