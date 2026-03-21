# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, SUPERUSER_ID, _
import logging
from string import punctuation
from bs4 import BeautifulSoup
import tempfile
import os
import PyPDF2
import base64
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

class KsIrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, res_ids=None, data=None):
        report = False

        # 1. Ensure res_ids is a list
        if isinstance(res_ids, int):
            res_ids = [res_ids]

        # 2. INVOICE LOGIC: Validation for account.move reports
        if self.model == 'account.move' and res_ids:
            invoice_reports = (
                self.env.ref('account.account_invoices_without_payment'),
                self.env.ref('account.account_invoices')
            )
            if self in invoice_reports:
                if self.env['ir.config_parameter'].sudo().get_param('account.display_name_in_footer'):
                    data = data and dict(data) or {}
                    data.update({'display_name_in_footer': True})
                moves = self.env['account.move'].browse(res_ids)
                if any(not move.is_invoice(include_receipts=True) for move in moves):
                    raise UserError(_("Only invoices could be printed."))

            # if self == self.env.ref('ks_custom_report_layouts.ks_account_invoices_without_amount'):
            #     moves = self.env['account.move'].browse(res_ids)
            #     company = moves[0].company_id  # Assuming all belong to same company
            #     report_config = self.env['ks.report.configuration'].sudo().search(
            #         [('ks_record_status', '=', 'Invoice'), ('company_id', '=', company.id)],
            #         limit=1
            #     )
            #     if report_config and report_config.sale_report_style_id.name != 'Minimalist':
            #         raise UserError(_("Only the Invoice Minimalist report could be printed."))


            if self in [
                self.env.ref('ks_custom_report_layouts.ks_account_invoices_without_amount'),
                self.env.ref('ks_custom_report_layouts.invoice_report_with_local_currency')
            ]:
                moves = self.env['account.move'].browse(res_ids)
                company = moves[0].company_id  # Assuming all belong to same company
                report_config = self.env['ks.report.configuration'].sudo().search(
                    [('ks_record_status', '=', 'Invoice'), ('company_id', '=', company.id)],
                    limit=1
                )
                
                if report_config and report_config.sale_report_style_id.name not in ['Minimalist','Lite','MCT']:
                    raise UserError(_("Only the Invoice Minimalist report could be printed."))

                
                
            invoice_reports = (
                self.env.ref('account.account_invoices_without_payment'),
                self.env.ref('account.account_invoices'), self.env.ref('ks_custom_report_layouts.ks_account_invoices_without_amount'),
                self.env.ref('ks_custom_report_layouts.ks_duplicate_account_invoices'), self.env.ref('ks_custom_report_layouts.ks_delivery_invoice_report'),
                self.env.ref('ks_custom_report_layouts.ks_duplicate_account_invoices_without_payment'), 
                self.env.ref('accounting_pdf_reports.action_report_journal_entries'),

            )
            if self in invoice_reports:
                moves = self.env['account.move'].browse(res_ids)
                company = moves[0].company_id 

                # Validation: Only progressive invoices allowed
                non_progressive_moves = moves.filtered(lambda m: m.is_progressive_invoice)
                if non_progressive_moves:
                    raise UserError(_("You can only print Progressive Invoices."))
                
            progressive_report_refs = (
                self.env.ref('ks_custom_report_layouts.action_progressive_invoice_report'), 
            )
            journal_entries_reports = (
                self.env.ref('accounting_pdf_reports.action_report_journal_entries'),
            )

            if self in progressive_report_refs:
                moves = self.env['account.move'].browse(res_ids)
                non_progressive = moves.filtered(lambda m: not getattr(m, 'is_progressive_invoice', False))
                if non_progressive:
                    raise UserError(_("Only Progressive Invoices can be printed with this report."))

            if self in journal_entries_reports:
                moves = self.env['account.move'].browse(res_ids)
                non_entries = moves.filtered(lambda m: m.move_type != 'entry')
                if non_entries:
                    raise UserError(_("Only Journal Entries can be printed with this report."))

        # 3. RENDER PDF FOR EACH RECORD INDIVIDUALLY TO SUPPORT MERGING
        if res_ids:
            for report_id in res_ids:
                temp_report = super()._render_qweb_pdf([report_id], data)
                if not report:
                    report = temp_report
                else:
                    report = self.ks_merge_pdf(report, temp_report[0])
        else:
            temp_report = super()._render_qweb_pdf(res_ids, data)
            if not report:
                report = temp_report
            else:
                report = self.ks_merge_pdf(report, temp_report[0])

        # 4. MERGE EXTRA CONTENT PDF IF CONFIGURED
        try:
            report_company_ids = self.env[self.model].browse(res_ids).mapped('company_id').ids
        except Exception:
            report_company_ids = []

        report_configs = self.ks_report_record(report_company_ids)
        for report_config in report_configs:
            if report_config.ks_is_custom_layout and report_config.ks_is_extra_content:
                if report_config.ks_extra_content_type != 'pdf' and report_config.ks_extra_content:
                    ks_extra_content = self.env['mail.render.mixin']._replace_local_links(report_config.ks_extra_content)
                    bodies = [bytes(ks_extra_content, 'utf-8')]
                    custom_pdf_bytes = self._run_wkhtmltopdf(
                        bodies,
                        specific_paperformat_args={'data-report-margin-top': 10, 'data-report-header-spacing': 10}
                    )
                    report = self.ks_merge_pdf(report, custom_pdf_bytes)

                if report_config.ks_extra_content_type != 'custom_content' and report_config.ks_upload_extra_content_pdf:
                    custom_pdf = report_config.ks_upload_extra_content_pdf
                    custom_pdf_bytes = base64.b64decode(custom_pdf)
                    report = self.ks_merge_pdf(report, custom_pdf_bytes)

        # 5. APPEND DELIVERY REPORT IF REPORT IS FOR SALES-DELIVERY
        if self.name == 'Sales-Delivery':
            docids = self.env['stock.picking'].sudo().search([('sale_id', 'in', res_ids)]).ids
            if docids:
                report = self.ks_sale_delivery(report, docids, data)

        return report


    def ks_merge_pdf(self, report, custom_pdf_bytes):
        temp_fiels = []
        pdf_report_fd, pdf_report_path = tempfile.mkstemp(suffix='.pdf', prefix='report.tmp.')
        os.close(pdf_report_fd)
        temp_fiels.append(pdf_report_path)
        report_bytes = report[0]

        f = open(pdf_report_path, 'wb')
        f.write(report_bytes)
        f.close()

        custom_pdf_report_fd, custom_pdf_report_path = tempfile.mkstemp(suffix='.pdf', prefix='report.tmp.')
        os.close(custom_pdf_report_fd)
        temp_fiels.append(custom_pdf_report_path)

        f = open(custom_pdf_report_path, 'wb')
        f.write(custom_pdf_bytes)
        f.close()

        final_merged_file_path = self.ks_merge_file(pdf_report_path, custom_pdf_report_path)

        with open(final_merged_file_path, 'rb') as pdf_document:
            pdf_content = pdf_document.read()

        for temporary_file in temp_fiels:
            try:
                os.unlink(temporary_file)
            except (OSError, IOError):
                _logger.error('Error when trying to remove file %s' % temporary_file)
        t1 = list(report)
        t1[0] = pdf_content
        report = tuple(t1)
        return report

    def ks_merge_file(self, input_file, output_file):
        report = open(input_file, 'rb')
        custom_pdf = open(output_file, 'rb')

        report_Reader = PyPDF2.PdfFileReader(report, strict=False)
        custom_pdf_Reader = PyPDF2.PdfFileReader(custom_pdf, strict=False)

        pdfWriter = PyPDF2.PdfFileWriter()

        for pageNum in range(report_Reader.numPages):
            pageObj = report_Reader.getPage(pageNum)
            pdfWriter.addPage(pageObj)

        for pageNum in range(custom_pdf_Reader.numPages):
            pageObj = custom_pdf_Reader.getPage(pageNum)
            pdfWriter.addPage(pageObj)

        final_pdf_report_fd , final_pdf_report_path = tempfile.mkstemp(suffix='.pdf', prefix='report.tmp.merge')
        os.close(final_pdf_report_fd)

        final_merged_file = open(final_pdf_report_path, 'wb')
        pdfWriter.write(final_merged_file)

        final_merged_file.close()
        report.close()
        custom_pdf.close()

        return final_pdf_report_path

    def ks_sale_delivery(self, report, docids, data):
        context = self.env.context
        delvry_report = self.env['ir.actions.report'].with_context(context).sudo().search([('report_name', '=', 'ks_custom_report_layouts.ks_custom_report_delivery_document')], limit=1)
        delvry_pdf = delvry_report.with_context(context)._render_qweb_pdf(docids, data=data)[0]
        sale_dlvry_report = self.ks_merge_pdf(report, delvry_pdf)
        return sale_dlvry_report

    def ks_report_record(self, company_ids):
        if self.xml_id == 'purchase.report_purchase_quotation' or self.xml_id == 'ks_custom_report_layouts.ks_duplicate_action_report_purchase_rfq_order':
            report_ui_id = self.env['ks.report.configuration'].search([('ks_record_status', '=', 'RFQ'), ('company_id', 'in', company_ids)])
        elif self.xml_id == 'purchase.action_report_purchase_order' or self.xml_id == 'ks_custom_report_layouts.ks_duplicate_action_report_purchase_order':
            report_ui_id = self.env['ks.report.configuration'].search([('ks_record_status', '=', 'purchase_order'), ('company_id', 'in', company_ids)])
        elif self.xml_id == 'stock.action_report_picking' or self.xml_id == 'ks_custom_report_layouts.ks_duplicate_action_report_picking':
            report_ui_id = self.env['ks.report.configuration'].search([('ks_record_status', '=', 'picking'), ('company_id', 'in', company_ids)])
        elif self.xml_id == 'stock.action_report_delivery' or self.xml_id == 'ks_custom_report_layouts.ks_duplicate_action_report_delivery':
            report_ui_id = self.env['ks.report.configuration'].search([('ks_record_status', '=', 'delivery'), ('company_id', 'in', company_ids)])
        else:
            report_ui_id = self.env['ks.report.configuration'].search([("ks_model_id", "in", self.model_id.ids), ('company_id', 'in', company_ids)])

        return report_ui_id

