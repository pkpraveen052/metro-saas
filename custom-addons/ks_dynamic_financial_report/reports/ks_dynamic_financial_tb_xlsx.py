# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.misc import xlsxwriter
import json
import io
from collections import defaultdict


class KsDynamicFinancialXlsxTB(models.Model):
    _inherit = 'ks.dynamic.financial.base'

    def ks_get_xlsx_trial_balance(self, ks_df_informations):
        """ Metro Modified 30May2025 """
        is_data = True  #prakash this line remove when condition add
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        row_pos = 0
        row_pos_2 = 0
        move_lines, retained, subtotal = self.ks_process_trial_balance(ks_df_informations)

        ks_company_id = self.env['res.company'].sudo().browse(ks_df_informations.get('company_id'))
        sheet = workbook.add_worksheet('Trial Balance')
        sheet.set_column(0, 0, 30)
        # sheet.set_column(1, 1, 15)
        # sheet.set_column(2, 2, 15)
        # sheet.set_column(3, 3, 15)
        # sheet.set_column(4, 4, 15)
        # sheet.set_column(5, 5, 15)
        # sheet.set_column(6, 6, 15)
        # sheet.set_column(7, 7, 15)
        # sheet.set_column(8, 8, 15)
        
        format_title = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size': 12,
            'font': 'Arial',
        })
        format_header = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'font': 'Arial',
        })
        format_header1 = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'font': 'Arial',
            'bg_color': '#9e9e9e'
        })
        format_header2 = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'font': 'Arial',
            'bg_color': '#e4c100',
            'align': 'center',
        })
        format_header3 = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'font': 'Arial',
            'bg_color': '#00a09d'
        })
        format_header4 = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'font': 'Arial',
            'bg_color': '#9e9e9e',
            'align': 'center',
        })
        format_header5 = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'font': 'Arial',
            'bg_color': '#00a09d',
            'align': 'center',
        })
        format_merged_header = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'center',
            'right': True,
            'left': True,
            'font': 'Arial',
        })
        format_merged_header_without_border = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial',
        })
        content_header = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'font': 'Arial',
        })
        line_header = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'right',
            'font': 'Arial',
        })
        line_header_total = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'right',
            'font': 'Arial',
            'top': True,
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
        line_header_total.set_num_format(format_string)
        line_header_left = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'left',
            'font': 'Arial',
        })
        line_header_left_total = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'left',
            'font': 'Arial',
            'top': True,
            'bottom': True,
        })
        line_header_light = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'right',
            'font': 'Arial',
        })
        line_header_light.set_num_format(format_string)
        line_header_light_total = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'right',
            'font': 'Arial',
            'top': True,
            'bottom': True,
        })
        line_header_light_total.set_num_format(format_string)
        line_header_light_left = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'left',
            'font': 'Arial',
        })
        line_header_highlight = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'right',
            'font': 'Arial',
        })
        line_header_highlight.set_num_format(format_string)
        line_header_light_date = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial',
        })
        row_pos_2 += 6
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
        if ks_df_informations:
            # Date from
            if ks_df_informations['date']['ks_process'] == 'range':
                sheet.write_string(row_pos_2, 0, _('Date from'), format_header)
                sheet.write_string(row_pos_2 + 1, 0, ks_df_informations['date'].get('ks_start_date'),
                                   format_merged_header_without_border)

                sheet.write_string(row_pos_2, 1, _('Date to'), format_header)
                sheet.write_string(row_pos_2 + 1, 1, ks_df_informations['date'].get('ks_end_date'),
                                   format_merged_header_without_border)
            else:
                sheet.write_string(row_pos_2, 0, _('As of Date'), format_header)
                sheet.write_string(row_pos_2 + 1, 0, ks_df_informations['date'].get('ks_end_date'),
                                   format_merged_header_without_border)

            # Journals
            row_pos_2 += 0
            sheet.write_string(row_pos_2, 3, _('Journals'), format_header)
            j_list = ', '.join(
                journal.get('name') or '' for journal in ks_df_informations['journals'] if journal.get('selected'))
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
            row_pos_2 += 0
            if ks_df_informations.get('analytic_accounts'):
                sheet.write_string(row_pos_2, 5, _('Analytic Accounts'), format_header)
                a_list = ', '.join(lt or '' for lt in ks_df_informations['selected_analytic_account_names'])
                sheet.write_string(row_pos_2 + 1, 5, a_list, content_header)

            row_pos_2 += 0
            if ks_df_informations.get('analytic_tags'):
                sheet.write_string(row_pos_2, 6, _('Tags'), format_header)
                a_list = ', '.join(lt or '' for lt in ks_df_informations['selected_analytic_tag_names'])
                sheet.write_string(row_pos_2 + 1, 6, a_list, content_header)
        row_pos += 5

        row_pos += 8 #R
        first_key, first_value = next(iter(move_lines.items()))

        if is_data: # prakash Here condition add
            col_pos = 1
            sheet.write_string(row_pos + 1, 0, _('Account'),
                               format_header)
            for a, b in first_value['comparision'].items():
                # sheet.write_string(row_pos, col_pos, _('Initial Balance'), format_header1)
                sheet.merge_range(row_pos, col_pos, row_pos, col_pos + 1, _('Initial Balance'),
                                  format_header4)
                sheet.set_column(col_pos, col_pos, 15)
                sheet.write_string(row_pos + 1, col_pos, _('Debit'),
                                   format_header)
                sheet.set_column(col_pos + 1, col_pos + 1, 15)
                sheet.write_string(row_pos + 1, col_pos + 1, _('Credit'),
                                   format_header)
                col_pos += 2
                sheet.merge_range(row_pos, col_pos, row_pos, col_pos + 1, a,
                                   format_header2)
                sheet.set_column(col_pos, col_pos, 15)
                sheet.write_string(row_pos + 1, col_pos, _('Debit'),
                                   format_header)
                sheet.set_column(col_pos + 1, col_pos + 1, 15)
                sheet.write_string(row_pos + 1, col_pos + 1, _('Credit'),
                                   format_header)
                col_pos += 2
                sheet.merge_range(row_pos, col_pos, row_pos, col_pos + 1, _('Ending Balance'),
                                  format_header5)
                sheet.set_column(col_pos, col_pos, 15)
                sheet.write_string(row_pos + 1, col_pos, _('Debit'),
                                   format_header)
                sheet.set_column(col_pos + 1, col_pos + 1, 15)
                sheet.write_string(row_pos + 1, col_pos + 1, _('Credit'),
                                   format_header)
                # sheet.write_string(row_pos, col_pos, _('Ending Balance'), format_header3)
                col_pos += 2


            # sheet.merge_range(row_pos, col_pos, row_pos, col_pos + 1, _('Initial Balance'),
            #                   format_header4)
            # # sheet.write_string(row_pos, col_pos, _('Initial Balance'), format_header1)
            #
            # col_pos += 2
            # for tup in first_value['comparision']:
            #     # sheet.write_string(row_pos, col_pos, tup, format_header2)
            #     sheet.merge_range(row_pos, col_pos, row_pos, col_pos + 1, tup, format_header2)
            #     col_pos += 2
            #
            # # sheet.write_string(row_pos, col_pos, _('Ending Balance'), format_header3)
            # sheet.merge_range(row_pos, col_pos, row_pos, col_pos + 1, _('Ending Balance'),
            #                   format_header5)
            # row_pos += 1
            # sheet.write_string(row_pos, 0, _('Account'),
            #                    format_header)
            # sheet.write_string(row_pos, 1, _('Debit'),
            #                    format_header)
            # sheet.write_string(row_pos, 2, _('Credit'),
            #                    format_header)
            # col_pos = 3
            #
            # for tup in first_value['comparision']:
            #     sheet.write_string(row_pos, col_pos, _('Debit'),
            #                        format_header)
            #     col_pos += 1
            #     sheet.write_string(row_pos, col_pos, _('Credit'),
            #                        format_header)
            #     col_pos += 1
            # sheet.write_string(row_pos, col_pos, _('Debit'),
            #                    format_header)
            # col_pos += 1
            # sheet.write_string(row_pos, col_pos, _('Credit'),
            #                    format_header)
            # col_pos += 1

            # Initialize the subtotal accumulators
            subtotal_initial_debit = 0.0
            subtotal_initial_credit = 0.0
            subtotal_ending_debit = 0.0
            subtotal_ending_credit = 0.0
            totals_by_year = defaultdict(lambda: {
                'subtotal_initial_debit': 0.0,
                'subtotal_initial_credit': 0.0,
                'subtotal_ending_debit': 0.0,
                'subtotal_ending_credit': 0.0,
            })
            row_pos += 1
            for line in move_lines.values():  # Normal lines
                row_pos += 1

                sheet.write_string(row_pos, 0, line.get('code') + ' ' + line.get('name'), line_header_light_left)

                # Calculate initial balances
                col_pos = 1
                for a, tup in line.get('comparision').items():
                    year = str(tup.get('ks_string'))
                    print('\n\n\ntuptuptuptuptuptuptup', tup)
                    # initial balance debit , credit
                    initial_balance = float(tup.get('initial_balance'))
                    initial_debit = initial_balance if initial_balance > 0 else 0
                    initial_credit = abs(initial_balance) if initial_balance < 0 else 0
                    sheet.write_number(row_pos, col_pos, initial_debit, line_header_light)
                    col_pos += 1
                    sheet.write_number(row_pos, col_pos, initial_credit, line_header_light)
                    col_pos += 1
                    totals_by_year[year]['subtotal_initial_debit'] += initial_debit
                    totals_by_year[year]['subtotal_initial_credit'] += initial_credit
                    # subtotal_initial_debit += initial_debit
                    # subtotal_initial_credit += initial_credit

                    # years table debit,credit
                    sheet.write_number(row_pos, col_pos, float(tup.get('debit')), line_header_light)
                    col_pos += 1
                    sheet.write_number(row_pos, col_pos, float(tup.get('credit')), line_header_light)
                    col_pos += 1

                    # ending balance debit, credit
                    ending_balance = float(tup.get('balance'))
                    ending_debit = ending_balance if ending_balance > 0 else 0
                    ending_credit = abs(ending_balance) if ending_balance < 0 else 0
                    sheet.write_number(row_pos, col_pos, ending_debit, line_header_light)
                    col_pos += 1
                    sheet.write_number(row_pos, col_pos, ending_credit, line_header_light)
                    col_pos += 1
                    totals_by_year[year]['subtotal_ending_debit'] += ending_debit
                    totals_by_year[year]['subtotal_ending_credit'] += ending_credit
                    # subtotal_ending_debit += ending_debit
                    # subtotal_ending_credit += ending_credit

                # col_pos = 3
                # for b, tup in line.get('comparision').items():
                #     # Write other values
                #     sheet.write_number(row_pos, col_pos, float(tup.get('debit')), line_header_light)
                #     col_pos += 1
                #     sheet.write_number(row_pos, col_pos, float(tup.get('credit')), line_header_light)
                #     col_pos += 1
                #
                # # Calculate ending balances
                # col_pos = 5
                # for c, tup in line.get('comparision').items():
                #     ending_balance = float(tup.get('balance'))
                #     ending_debit = ending_balance if ending_balance > 0 else 0
                #     ending_credit = abs(ending_balance) if ending_balance < 0 else 0
                #     sheet.write_number(row_pos, col_pos, ending_debit, line_header_light)
                #     col_pos += 1
                #     sheet.write_number(row_pos, col_pos, ending_credit, line_header_light)
                #
                #     subtotal_ending_debit += ending_debit
                #     subtotal_ending_credit += ending_credit

            row_pos += 2
            sheet.write_string(row_pos, 0,
                               subtotal['SUBTOTAL'].get('code') + ' ' + subtotal['SUBTOTAL'].get('name'),
                               line_header_left_total)

            # Subtotal initial balance calculation
            col_pos = 1
            for year, total in totals_by_year.items():
                sheet.write_number(row_pos, col_pos, float(total.get('subtotal_initial_debit')), line_header_light_total)
                col_pos += 1
                sheet.write_number(row_pos, col_pos, float(total.get('subtotal_initial_credit')), line_header_light_total)
                col_pos += 3
                sheet.write_number(row_pos, col_pos, float(total.get('subtotal_ending_debit')), line_header_light_total)
                col_pos += 1
                sheet.write_number(row_pos, col_pos, float(total.get('subtotal_ending_credit')), line_header_light_total)
                col_pos += 1
            # sheet.write_number(row_pos, 1, subtotal_initial_debit, line_header_light_total)
            # sheet.write_number(row_pos, 2, subtotal_initial_credit, line_header_light_total)

            col_pos = 3
            for a, tup in subtotal['SUBTOTAL']['subtotal_comparision'].items():
                sheet.write_number(row_pos, col_pos, float(tup.get('ks_total_deb')), line_header_light_total)
                col_pos += 1
                sheet.write_number(row_pos, col_pos, float(tup.get('ks_total_cre')), line_header_light_total)
                col_pos += 5

            # Subtotal ending balance calculation
            # sheet.write_number(row_pos, col_pos, subtotal_ending_debit, line_header_light_total)
            # col_pos += 1
            # sheet.write_number(row_pos, col_pos, subtotal_ending_credit, line_header_light_total)

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

        else:
            col_pos = 1
            for a, b in first_value['comparision'].items():
                sheet.set_column(col_pos, col_pos, 15)
                sheet.write_string(row_pos, col_pos, _('Initial Balance'), format_header1)
                col_pos += 1
                sheet.set_column(col_pos, col_pos, 15)
                sheet.set_column(col_pos + 1, col_pos + 1, 15)
                sheet.merge_range(row_pos, col_pos, row_pos, col_pos + 1, a,
                                   format_header2)
                col_pos += 2
                sheet.set_column(col_pos, col_pos, 15)
                sheet.write_string(row_pos, col_pos, _('Ending Balance'), format_header3)
                col_pos += 1


            row_pos += 1 #R

            sheet.write_string(row_pos, 0, _('Account'),
                               format_header)
            col_pos = 1
            for tup in first_value['comparision']:
                col_pos += 1
                sheet.write_string(row_pos, col_pos, _('Debit'),
                                   format_header)
                col_pos += 1
                sheet.write_string(row_pos, col_pos, _('Credit'),
                                   format_header)
                col_pos += 2

            subtotal_initial_debit = 0.0
            subtotal_initial_credit = 0.0
            subtotal_ending_debit = 0.0
            subtotal_ending_credit = 0.0

            for line in move_lines.values():  # Normal lines
                row_pos += 1 #R
                col_pos = 1

                sheet.write_string(row_pos, 0, line.get('code') + ' ' + line.get('name'), line_header_light_left)

                for a, b in line.get('comparision').items():
                    sheet.write_number(row_pos, col_pos, float(b['initial_balance']), line_header_light)
                    col_pos += 1
                    sheet.write_number(row_pos, col_pos, float(b.get('debit')), line_header_light)
                    col_pos += 1
                    sheet.write_number(row_pos, col_pos, float(b.get('credit')), line_header_light)
                    col_pos += 1
                    sheet.write_number(row_pos, col_pos, float(b.get('balance')), line_header_light)
                    col_pos += 1


            row_pos += 2
            sheet.write_string(row_pos, 0,
                            subtotal['SUBTOTAL'].get('code') + ' ' + subtotal['SUBTOTAL'].get('name'),
                            line_header_left_total)

            # # Subtotal initial balance calculation
            # sheet.write_number(row_pos, 1, subtotal_initial_debit, line_header_light_total)
            # sheet.write_number(row_pos, 2, subtotal_initial_credit, line_header_light_total)

            col_pos = 1
            for a,b in subtotal['SUBTOTAL']['subtotal_comparision'].items():
                sheet.write_number(row_pos, col_pos, float(b.get('ks_total_initial_bln')), line_header_light_total)
                col_pos += 1
                sheet.write_number(row_pos, col_pos, float(b.get('ks_total_deb')), line_header_light_total)
                col_pos += 1
                sheet.write_number(row_pos, col_pos, float(b.get('ks_total_cre')), line_header_light_total)
                col_pos += 1
                sheet.write_number(row_pos, col_pos, float(b.get('ks_total_bln')), line_header_light_total)
                col_pos += 1

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
