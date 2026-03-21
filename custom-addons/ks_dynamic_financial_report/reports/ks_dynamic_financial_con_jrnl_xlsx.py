# -*- coding: utf-8 -*-
import io
from odoo import models, api, _
from odoo.tools.misc import xlsxwriter
from datetime import datetime


class KsDynamicFinancialXlsxCJ(models.Model):
    _inherit = 'ks.dynamic.financial.base'

    @api.model
    def ks_dynamic_consolidate_xlsx(self, ks_df_informations):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        currency_id = self.env.user.company_id.currency_id
        move_lines, ks_month_lines = self._get_lines(ks_df_informations)
        ks_company_id = self.env['res.company'].sudo().browse(ks_df_informations.get('company_id'))

        sheet = workbook.add_worksheet('Consolidate Journal Report')
        row_pos = 0
        row_pos_2 = 0
        sheet.set_column(0, 0, 12)
        sheet.set_column(1, 1, 12)
        sheet.set_column(2, 2, 30)
        sheet.set_column(3, 3, 18)
        sheet.set_column(4, 4, 30)
        sheet.set_column(5, 5, 10)
        sheet.set_column(6, 6, 10)
        sheet.set_column(7, 7, 10)

        format_title = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size': 12,
            'font': 'Arial',
            'border': False
        })

        format_header = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'font': 'Arial',
            'align': 'center',
            # 'border': True
        })
        content_header = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial',
            'border': True,
            'text_wrap': True,
        })
        content_header_date = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'border': True,
            'align': 'center',
            'font': 'Arial',
        })
        line_header = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'center',
            'top': True,
            'font': 'Arial',
            'bottom': True,
        })
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
        line_header.set_num_format(format_string)
        line_header_left = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'left',
            'top': True,
            'font': 'Arial',
            'bottom': True,
        })
        line_header_light = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'center',
            # 'top': True,
            # 'bottom': True,
            'font': 'Arial',
            'text_wrap': True,
            'valign': 'top'
        })
        line_header_light.set_num_format(format_string)
        line_header_light_date = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'top': True,
            # 'bottom': True,
            'font': 'Arial',
            'align': 'center',
            'num_format': 'mm/dd/yyyy'
        })
        font_style = workbook.add_format({'font': 'Arial', 'font_size': 10})
        address = ", ".join(
            filter(None, [self.env.company.street, self.env.company.street, self.env.company.zip,
                          self.env.company.country_id.name])
        )
        company_format = workbook.add_format({'bold': True, 'font_size': 14, 'font': 'Arial'})
        address_wrap_format = workbook.add_format(
            {'text_wrap': True, 'valign': 'top', 'font_size': 10, 'font': 'Arial'})
        sheet.merge_range(0, 2, 0, 3, self.env.company.name, company_format)
        sheet.merge_range(1, 2, 1, 3, address, address_wrap_format)
        if self.env.company.l10n_sg_unique_entity_number:
            uen = 'UEN:' + self.env.company.l10n_sg_unique_entity_number
            sheet.merge_range(2, 2, 2, 3, uen, font_style)
        if self.env.company.phone:
            phone = 'Phone:' + self.env.company.phone
            sheet.merge_range(3, 2, 3, 3, phone, font_style)
        if self.env.company.email:
            email = 'Email:' + self.env.company.email
            sheet.merge_range(4, 2, 4, 3, email, font_style)
        row_pos_2 += 6
        if ks_df_informations:
            # Date from
            if ks_df_informations['date']['ks_process'] == 'range':
                sheet.write_string(row_pos_2, 0, _('Date from'),
                                   format_header)
                sheet.write_string(row_pos_2 + 1, 0, ks_df_informations['date'].get('ks_start_date'),
                                   content_header_date)

                sheet.write_string(row_pos_2, 1, _('Date to'),
                                   format_header)

                sheet.write_string(row_pos_2 + 1, 1, ks_df_informations['date'].get('ks_end_date'),
                                   content_header_date)
            else:

                sheet.write_string(row_pos_2, 0, _('As of Date'),
                                   format_header)

                sheet.write_string(row_pos_2 + 1, 0, ks_df_informations['date'].get('ks_end_date'),
                                   content_header_date)

            # row_pos_2 += 1
            # sheet_2.write_string(row_pos_2, 0, _('Display accounts'),
            #                         format_header)
            # sheet_2.write_string(row_pos_2, 1, filter['display_accounts'],
            #                         self.content_header)
            #
            # Journals
            row_pos_2 += 0
            sheet.write_string(row_pos_2, 3, _('Journals'),
                               format_header)
            j_list = ', '.join(
                journal.get('code') or '' for journal in ks_df_informations['journals'] if journal.get('selected'))
            sheet.write_string(row_pos_2 + 1, 3, j_list,
                               content_header)

            # Account
            row_pos_2 += 0
            sheet.write_string(row_pos_2, 4, _('Account'), format_header)
            j_list = ', '.join(
                journal.get('name') or '' for journal in ks_df_informations['account'] if journal.get('selected'))
            sheet.write_string(row_pos_2 + 1, 4, j_list,
                               content_header)

            #
            # # Accounts
            # row_pos_2 += 0
            # sheet.write_string(row_pos_2, 6, _('Analytic Accounts'),
            #                    format_header)
            # a_list = ', '.join(lt or '' for lt in ks_df_informations['selected_analytic_account_names'])
            # sheet.write_string(row_pos_2 + 1, 6, a_list,
            #                    content_header)

        row_pos += 11
        if ks_df_informations.get('ks_report_with_lines', False):
            sheet.merge_range(row_pos, 0, row_pos, 2, _('Account'),
                              format_header)
            sheet.write_string(row_pos, 3, _('Debit'),
                               format_header)
            sheet.write_string(row_pos, 4, _('Credit'),
                               format_header)
            # sheet.write_string(row_pos, 3, _('Ref'),
            #                         format_header)
            sheet.write_string(row_pos, 5, _('Balance'),
                               format_header)

        else:
            sheet.merge_range(row_pos, 0, row_pos, 2, _('Journal'), format_header)

            sheet.write_string(row_pos, 3, _('Debit'),
                               format_header)
            sheet.write_string(row_pos, 4, _('Credit'),
                               format_header)
            sheet.write_string(row_pos, 5, _('Balance'),
                               format_header)
        if move_lines:
            for line in move_lines:
                # line = line[0]
                row_pos += 1
                if not line['id'] == "Details_":
                    sheet.merge_range(row_pos, 0, row_pos, 2, (line.get('name')),
                                      line_header_left)
                    sheet.write_number(row_pos, 3, float(line.get('debit')), line_header)
                    sheet.write_number(row_pos, 4, float(line.get('credit')), line_header)
                    sheet.write_number(row_pos, 5, float(line.get('balance')), line_header)
                else:
                    sheet.merge_range(row_pos, 0, row_pos, 2, (line.get('name')),
                                      line_header_left)
                    sheet.write(row_pos, 3, line.get('debit'), line_header)
                    sheet.write(row_pos, 4, line.get('credit'), line_header)
                    sheet.write(row_pos, 5, line.get('balance'), line_header)

                if ks_df_informations.get('ks_report_with_lines', False):
                    if not line['id'] == 'total' and not line['id'] == 'Details_':
                        for sub_line in line.get('lines'):
                            row_pos += 1
                            sheet.merge_range(row_pos, 0, row_pos, 2, sub_line.get('account_name'),
                                              line_header_light_date)
                            sheet.write_number(row_pos, 3, sub_line.get('debit'),
                                               line_header_light)
                            sheet.write_number(row_pos, 4, sub_line.get('credit'),
                                               line_header_light)

                            sheet.write_number(row_pos, 5, sub_line.get('balance'),
                                               line_header_light)

            for months in ks_month_lines:
                row_pos = row_pos + 1
                sheet.merge_range(row_pos, 0, row_pos, 2, (months.get('name')),
                                  line_header_left)
                sheet.write(row_pos, 3, months.get('debit'), line_header)
                sheet.write(row_pos, 4, months.get('credit'), line_header)
                sheet.write(row_pos, 5, months.get('balance'), line_header)

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
        #Branding step end here
        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return generated_file
