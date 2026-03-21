# -*- coding: utf-8 -*-
import io
from odoo import models, api, _, fields
from odoo.tools.misc import xlsxwriter
from datetime import datetime
import xlsxwriter
from collections import defaultdict



class KsDynamicFinancialXlsxTR(models.Model):
    _inherit = 'ks.dynamic.financial.base'

    @api.model
    def ks_dynamic_tax_xlsx(self, ks_df_informations):
        if ks_df_informations.get('ks_report_with_lines', False):
            return self._generate_tax_report_with_details(ks_df_informations)
        else:
            return self._generate_tax_report_without_details(ks_df_informations)

    def _generate_tax_report_with_details(self, ks_df_informations):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Tax Report")
        print(ks_df_informations.get('ks_report_with_lines', False))

        # ----------------- Formats (based on your old header styles) -----------------
        format_title = workbook.add_format({
            "bold": True, "align": "center", "font_size": 12, "border": True, "font": "Arial"
        })
        format_header = workbook.add_format({
            "bold": True, "font_size": 10, "align": "center", "font": "Arial", "bottom": False, "border": True
        })
        content_header = workbook.add_format({
            "bold": False, "font_size": 10, "align": "center", "font": "Arial"
        })
        content_header_date = workbook.add_format({
            "bold": False, "font_size": 10, "align": "center", "font": "Arial"
        })
        line_header = workbook.add_format({
            "bold": False, "font_size": 10, "align": "right", "font": "Arial", "bottom": True
        })
        line_header_bold = workbook.add_format({
            "bold": True, "font_size": 10, "align": "right", "font": "Arial", "bottom": True
        })
        line_header_string = workbook.add_format({
            "bold": False, "font_size": 10, "align": "left", "font": "Arial", "bottom": True
        })
        line_header_string_bold = workbook.add_format({
            "bold": True, "font_size": 10, "align": "left", "font": "Arial", "bottom": True
        })

        # company / small text
        font_style = workbook.add_format({"font": "Arial", "font_size": 10})
        company_format = workbook.add_format({"bold": True, "font_size": 14, "font": "Arial"})
        text_format_left = workbook.add_format({"align": "left", "valign": "vcenter"})

        # ----------------- Company & header block -----------------
        ks_company_id = self.env["res.company"].sudo().browse(ks_df_informations.get("company_id"))
        ks_company = ks_company_id  # alias

        row_pos = 0
        # Company name and address/contact
        sheet.write_string(row_pos, 0, ks_company.name or "", company_format)
        row_pos += 1

        address = ", ".join(
            filter(None, [ks_company.street, ks_company.street2, ks_company.zip, ks_company.country_id.name])
        )
        if address:
            sheet.write_string(row_pos, 0, address, font_style)
            row_pos += 1

        if ks_company.l10n_sg_unique_entity_number:
            sheet.write_string(row_pos, 0, _("UEN: ") + ks_company.l10n_sg_unique_entity_number, font_style)
            row_pos += 1
        if ks_company.phone:
            sheet.write_string(row_pos, 0, _("Phone: ") + ks_company.phone, font_style)
            row_pos += 1
        if ks_company.email:
            sheet.write_string(row_pos, 0, _("Email: ") + ks_company.email, font_style)
            row_pos += 1

        # show_partner = ks_df_informations.get('display_customer_name_on_tax_report')
        show_partner = ks_company.display_customer_name_on_tax_report

        # Leave a small gap before date/filter info
        row_pos_2 = max(6, row_pos + 1)

        # ----------------- Date / Comparison filter printing -----------------
        # If comparison disabled -> print Date from / Date to or As of Date
        if not ks_df_informations["ks_diff_filter"]["ks_diff_filter_enablity"]:
            if ks_df_informations["date"]["ks_process"] == "range":
                sheet.write_string(row_pos_2, 0, _("Date from"), format_header)
                if ks_df_informations["date"].get("ks_start_date"):
                    sheet.write_string(row_pos_2, 1, ks_df_informations["date"].get("ks_start_date"),
                                       content_header_date)
                row_pos_2 += 1

                sheet.write_string(row_pos_2, 0, _("Date to"), format_header)
                if ks_df_informations["date"].get("ks_end_date"):
                    sheet.write_string(row_pos_2, 1, ks_df_informations["date"].get("ks_end_date"), content_header_date)
            else:
                sheet.write_string(row_pos_2, 0, _("As of Date"), format_header)
                if ks_df_informations["date"].get("ks_end_date"):
                    sheet.write_string(row_pos_2, 1, ks_df_informations["date"].get("ks_end_date"), content_header_date)

        # If comparison enabled -> print comparison period
        if ks_df_informations["ks_diff_filter"]["ks_diff_filter_enablity"]:
            # print Comparison Date from / to based on ks_differ intervals
            sheet.write_string(row_pos_2, 0, _("Comparison Date from"), format_header)
            comp_start = ks_df_informations["ks_differ"].get("ks_intervals")[-1].get("ks_start_date")
            sheet.write_string(row_pos_2, 1, comp_start, content_header_date)
            row_pos_2 += 1
            sheet.write_string(row_pos_2, 0, _("Comparison Date to"), format_header)
            comp_end = ks_df_informations["ks_differ"].get("ks_intervals")[0].get("ks_end_date")
            sheet.write_string(row_pos_2, 1, comp_end, content_header_date)

        # Move row_pos to start report body below header block
        row_pos = row_pos_2 + 3

        # ----------------- Number format (company currency / decimals) -----------------
        decimal_places = ks_company.currency_id.decimal_places or 2
        currency_symbol = ks_company.currency_id.symbol or ""
        format_string = "#,##0." + ("0" * decimal_places)
        # If user enabled currency symbol on dynamic report, include it
        if getattr(ks_company, "ks_enable_currency_symbol_on_dynamic_report", False):
            if ks_company.currency_id.position == "before":
                format_string = '"' + currency_symbol + '" ' + format_string + ';"' + currency_symbol + '" -' + format_string
            else:
                format_string = format_string + ' "' + currency_symbol + '"' + ';-' + format_string + ' "' + currency_symbol + '"'
        num_format = workbook.add_format({"num_format": format_string, "align": "right", "valign": "vcenter"})
        num_format_bold = workbook.add_format(
            {"num_format": format_string, "align": "right", "bold": True, "valign": "vcenter"})
        combined_format = workbook.add_format({
            "num_format": format_string,  # number format
            "align": "right",  # alignment
            "valign": "vcenter",  # vertical alignment
            "font_size": 10,  # font size
            "font_name": "Arial",  # font family
            "bottom": 1  # bottom border (1 = thin)
        })
        combined_format_bold = workbook.add_format({
            "num_format": format_string,
            "align": "right",
            "bold": True,
            "valign": "vcenter",
            "font_size": 10,  # font size
            "font_name": "Arial",  # font family
            "bottom": 1  # bottom border (1 = thin)

        })

        # ----------------- TAX SUMMARY -----------------
        # sheet.write_string(row_pos, 0, _("TAX SUMMARY"), format_header)
        # row_pos += 2
        #
        # summary_headers = [_("Tax Name"), _("SubTotal"), _("TaxAmount"), _("Total Amount")]
        # for col, header in enumerate(summary_headers):
        #     sheet.write_string(row_pos, col, header, format_header)
        # row_pos += 1

        # lines come from the existing processor (keeps your existing logic/filters)
        lines = self.ks_process_tax_report(ks_df_informations) or []
        # filter only tax-like lines (example: 'GST 9% Sales (9.0)')
        tax_lines = [l for l in lines if "%" in l.get("ks_name", "") or "GST" in l.get("ks_name", "")]

        # ----------------- TAX WISE DETAILS -----------------
        sheet.write_string(row_pos, 0, _("TAX WISE DETAILS"), format_header)
        row_pos += 1

        for tax in tax_lines:
            print(tax.get("id"))
            # Heading for this tax
            sheet.write_string(row_pos, 0, tax.get("ks_name", ""), line_header_string_bold)
            row_pos += 1

            # Sub-headers (with TotalAmt before SubTotal as you requested)
            sub_headers = [
                _("DATE"),
                _("ACCOUNT"),
            ]

            if show_partner:
                sub_headers.append(_("CUSTOMER/VENDOR"))

            sub_headers += [
                _("INVOICE/REF"),
                _("LABEL"),
                _("TAX RATE"),
                _("CURRENCY"),
                _("TAX AMOUNT"),
                _("SUBTOTAL"),
                _("TOTAL AMOUNT")
            ]


            for col, header in enumerate(sub_headers):
                sheet.write_string(row_pos, col, header, format_header)
            row_pos += 1

            # ========= COLUMN WIDTHS =========
            sheet.set_column('A:A', 15)  # Date
            sheet.set_column('B:B', 25)  # Account
            sheet.set_column('C:C', 20)  # Inv Ref No.
            sheet.set_column('D:D', 35)  # Label
            sheet.set_column('E:E', 12)  # Tax Rate
            sheet.set_column('F:F', 12)  # Currency
            sheet.set_column('G:I', 18)  # Amounts

            sheet.set_column('A:A', 15)  # Date
            sheet.set_column('B:B', 25)  # Account
            sheet.set_column('C:C', 20)  # Inv Ref No.

            col_index = 3

            if show_partner:
                sheet.set_column(col_index, col_index, 25)  # Customer/Vendor
                col_index += 1

            sheet.set_column(col_index, col_index, 35)  # Label
            sheet.set_column(col_index + 1, col_index + 1, 12)  # Tax Rate
            sheet.set_column(col_index + 2, col_index + 2, 12)  # Currency
            sheet.set_column(col_index + 3, col_index + 5, 18)  # Amounts


            # Build AML search domain (company + posted + tax_line + date range)
            domain = [
                ("tax_ids", "=", tax.get("id")),
                ("move_id.state", "in", ["draft", "posted"]),
                ("company_id", "=", ks_company.id)
            ]
            date_vals = ks_df_informations.get("date", {}) or {}

            if date_vals.get("ks_start_date"):
                domain.append(("date", ">=", date_vals.get("ks_start_date")))
            if date_vals.get("ks_end_date"):
                domain.append(("date", "<=", date_vals.get("ks_end_date")))

            aml_records = self.env["account.move.line"].search(domain, order="date, id")

            #Logic to get the label of main move line
            aml_dict = {}

            for move in aml_records.mapped('move_id'):
                move_lines = move.line_ids

                # ✅ Only main product/service lines
                main_lines = move_lines.filtered(
                    lambda l: not l.tax_line_id and l.display_type not in ("line_section", "line_note")and (not l.name or not l.name.startswith("INV")
                ))

                names = [l.name.strip() for l in main_lines if l.name and l.name.strip()]
                if names:
                    aml_dict[move.id] = ", ".join(names)
                else:
                    aml_dict[move.id] = ""


            # Group AMLs by (move_id, tax_id)
            grouped = defaultdict(list)
            for aml in aml_records:
                grouped[(aml.move_id, aml.tax_line_id or aml.tax_ids[:1])].append(aml)

            # Per-tax accumulators
            tax_subtotal = 0.0
            tax_amount_sum = 0.0
            tax_total_amt = 0.0

            for (move, tax), aml in grouped.items():
                # Aggregate values
                tax_rate = ("%g%%" % tax.amount) if tax else "0%"
                currency = aml[0].currency_id or ks_company.currency_id

                move_line_ids = move.line_ids
                # Tax amount: sum for this tax only
                tax_amt = sum(abs(l.credit if tax.type_tax_use == 'sale' else l.debit) or 0.0 for l in move_line_ids if l.tax_line_id == tax )  # only tax line itself

                base_amt = sum(abs(l.credit if tax.type_tax_use == 'sale' else l.debit) or 0.0 for l in aml)

                total_amt = abs(tax_amt) + abs(base_amt)

                col = 0

                sheet.write_string(row_pos, col, str(move.date), line_header_string)
                col += 1

                sheet.write_string(row_pos, col, aml[0].account_id.display_name or "", line_header_string)
                col += 1

                if show_partner:
                    sheet.write_string(row_pos, col, move.partner_id.name or "", line_header_string)
                    col += 1

                sheet.write_string(row_pos, col, move.name or move.ref or "", line_header_string)
                col += 1

                sheet.write_string(row_pos, col, aml_dict.get(move.id, False) or "", line_header_string)
                col += 1

                sheet.write_string(row_pos, col, tax_rate, line_header_string)
                col += 1

                sheet.write_string(row_pos, col, aml[0].currency_id.name or ks_company.currency_id.name, line_header_string)
                col += 1

                sheet.write_number(row_pos, col, abs(tax_amt), combined_format)
                col += 1

                sheet.write_number(row_pos, col, abs(base_amt), combined_format)
                col += 1

                sheet.write_number(row_pos, col, abs(total_amt), combined_format)

                row_pos += 1

                amount_start_col = 6 if not show_partner else 7

                sheet.write_number(row_pos, amount_start_col, tax_amount_sum, combined_format_bold)
                sheet.write_number(row_pos, amount_start_col + 1, tax_subtotal, combined_format_bold)
                sheet.write_number(row_pos, amount_start_col + 2, tax_total_amt, combined_format_bold)

                row_pos += 2


        # ----------------- Footer Branding -----------------
        last_row = row_pos + 2
        copyright_format = workbook.add_format({
            "bold": True, "size": 10, "align": "left", "font": "Arial"
        })
        powered_format = workbook.add_format({
            "bold": True, "italic": True, "size": 10, "align": "left", "font": "Arial"
        })
        company_name = ks_company.name or ""
        sheet.merge_range(last_row, 0, last_row, 3, f"Copyright © {company_name}", copyright_format)
        sheet.merge_range(last_row, 4, last_row, 7, "Powered by Metro Accounting System", powered_format)

        # close & return file bytes
        workbook.close()
        output.seek(0)
        data = output.read()
        output.close()
        return data

    def _generate_tax_report_without_details(self, ks_df_informations):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(self.display_name[:31])
        lines = self.ks_process_tax_report(ks_df_informations)
        ks_company_id = self.env['res.company'].sudo().browse(ks_df_informations.get('company_id'))
        sheet.freeze_panes(4, 1)
        row_pos = 0
        row_pos_2 = 6
        format_title = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size': 12,
            'border': False,
            'font': 'Arial',
        })
        format_header = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial',
            'bottom': False
        })
        content_header = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial',
        })
        content_header_date = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial',
            # 'num_format': 'dd/mm/yyyy',
        })
        line_header = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'right',
            'font': 'Arial',
            'bottom': True
        })
        line_header_bold = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'right',
            'font': 'Arial',
            'bottom': True
        })
        line_header_string = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'left',
            'font': 'Arial',
            'bottom': True
        })
        line_header_string_bold = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'left',
            'font': 'Arial',
            'bottom': True
        })
        # Date from
        font_style = workbook.add_format({'font': 'Arial', 'font_size': 10})
        address = ", ".join(
            filter(None, [self.env.company.street, self.env.company.street, self.env.company.zip,
                          self.env.company.country_id.name])
        )
        company_format = workbook.add_format({'bold': True, 'font_size': 14, 'font': 'Arial'})
        # address_wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})
        sheet.write_string(0, 0, self.env.company.name, company_format)
        sheet.write_string(1, 0, address, font_style)
        if self.env.company.l10n_sg_unique_entity_number:
            uen = 'UEN:' + self.env.company.l10n_sg_unique_entity_number
            sheet.write_string(2, 0, uen, font_style)
        if self.env.company.phone:
            phone = 'Phone:' + self.env.company.phone
            sheet.write_string(3, 0, phone, font_style)
        if self.env.company.email:
            email = 'Email:' + self.env.company.email
            sheet.write_string(4, 0, email, font_style)
        if not ks_df_informations['ks_diff_filter']['ks_diff_filter_enablity']:
            if ks_df_informations['date']['ks_process'] == 'range':
                sheet.write_string(row_pos_2, 0, _('Date from'),
                                   format_header)
                if ks_df_informations['date'].get('ks_start_date'):
                    sheet.write_string(row_pos_2, 1, ks_df_informations['date'].get('ks_start_date'),
                                       content_header_date)
                row_pos_2 += 1
                # Date to
                sheet.write_string(row_pos_2, 0, _('Date to'),
                                   format_header)

                if ks_df_informations['date'].get('ks_end_date'):
                    sheet.write_string(row_pos_2, 1, ks_df_informations['date'].get('ks_end_date'),
                                       content_header_date)
            else:
                sheet.write_string(row_pos_2, 0, _('As of Date'),
                                   format_header)
                if ks_df_informations['date'].get('ks_end_date'):
                    sheet.write_string(row_pos_2, 1, ks_df_informations['date'].get('ks_end_date'),
                                       content_header_date)

        if ks_df_informations['ks_diff_filter']['ks_diff_filter_enablity']:
            sheet.write_string(row_pos_2, 0, _('Comparison Date from'),
                               format_header)
            sheet.write_string(row_pos_2, 1, ks_df_informations['ks_differ'].get('ks_intervals')[-1]['ks_start_date'],
                               content_header_date)
            row_pos_2 += 1
            # Date to
            sheet.write_string(row_pos_2, 0, _('Comparison Date to'),
                               format_header)

            sheet.write_string(row_pos_2, 1, ks_df_informations['ks_differ'].get('ks_intervals')[0]['ks_end_date'],
                               content_header_date)

        row_pos += 9
        if ks_df_informations['ks_diff_filter']['ks_debit_credit_visibility']:

            sheet.set_column(0, 0, 90)
            sheet.set_column(1, 1, 15)
            sheet.set_column(2, 3, 15)
            sheet.set_column(3, 3, 15)

            sheet.write_string(row_pos, 1, _('Net Amount'),
                               format_header)
            sheet.write_string(row_pos, 2, _('Tax'),
                               format_header)

            for a in lines:
                if a['ks_level'] == 2:
                    row_pos += 1
                row_pos += 1
                if a.get('account', False):
                    tmp_style_str = line_header_string
                    tmp_style_num = line_header
                else:
                    tmp_style_str = line_header_string_bold
                    tmp_style_num = line_header_bold
                decimal_places = ks_company_id.currency_id.decimal_places or 2
                currency_symbol = ks_company_id.currency_id.symbol
                format_string = '#,##0.' + '0' * decimal_places
                if ks_company_id.ks_enable_currency_symbol_on_dynamic_report:
                    if ks_company_id.currency_id.position == 'before':
                        format_string = (
                                '"' + currency_symbol + '" ' + format_string +
                                ';"' + currency_symbol + '" -' + format_string
                        )
                    else:
                        format_string = (
                                format_string + ' "' + currency_symbol + '"' +
                                ';-' + format_string + ' "' + currency_symbol + '"'
                        )
                tmp_style_num.set_num_format(format_string)
                sheet.write_string(row_pos, 0, '   ' * len(a.get('list_len', [])) + a.get('ks_name'),
                                   tmp_style_str)
                sheet.write_number(row_pos, 1, float(a.get('ks_net_amount', 0.0)), tmp_style_num)

                sheet.write_number(row_pos, 2, float(a.get('tax', 0.0)), tmp_style_num)
        if not ks_df_informations['ks_diff_filter']['ks_debit_credit_visibility']:

            sheet.set_column(0, 0, 50)
            sheet.set_column(1, 1, 15)
            sheet.set_column(2, 3, 15)
            sheet.set_column(3, 3, 15)
            sheet.write_string(row_pos, 0, _('Name'),
                               format_header)

            sheet.write_string(row_pos, 1, _('Net Amount') + ks_df_informations['date']['ks_string'],
                               format_header)
            sheet.write_string(row_pos, 2, _('Net Tax') + ks_df_informations['date']['ks_string'],
                               format_header)
            ks_col = 3
            # for x in range(3):

            for i in ks_df_informations['ks_differ']['ks_intervals']:
                sheet.write_string(row_pos, ks_col, _('Net Amount') + i['ks_string'],
                                   format_header)
                sheet.set_column(ks_col, ks_col, 20)
                ks_col += 1
                sheet.write_string(row_pos, ks_col, _('Net Tax') + i['ks_string'],
                                   format_header)
                sheet.set_column(ks_col, ks_col, 20)
                ks_col += 1

            ks_col_line = 0
            for line in lines:
                sheet.write(row_pos + 1, 0, line['ks_name'],
                            format_header)
                for ks in line['balance_cmp']:
                    sheet.write(row_pos + 1, ks_col_line + 1, ks[0]['ks_com_net'],
                                line_header)
                    ks_col_line = ks_col_line + 1
                    sheet.write(row_pos + 1, ks_col_line + 1, ks[1]['ks_com_tax'],
                                line_header)
                    ks_col_line += 1
                ks_col_line = 0
                row_pos += 1

        last_row = row_pos + 2
        # Create the format for copyright and powered by
        copyright_format = workbook.add_format({'bold': True, 'size': 10, 'align': 'left'})
        powered_format = workbook.add_format({'bold': True, 'italic': True, 'size': 10, 'align': 'left'})
        # Get the company name dynamically from the logged-in user's current company (multi-company aware)
        company_name = ks_company_id.name
        # Add the Copyright line with left alignment in columns 0 to 3
        sheet.merge_range(last_row + 2, 0, last_row + 2, 3, f"Copyright © {company_name}", copyright_format)
        # Add the Powered by Metro line with right alignment in columns 4 to 7
        sheet.merge_range(last_row + 2, 4, last_row + 2, 7, "Powered by Metro Accounting System", powered_format)
        # Branding step end here
        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return generated_file
