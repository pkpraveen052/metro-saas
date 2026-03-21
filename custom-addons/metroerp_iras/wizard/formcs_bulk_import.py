# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
import tempfile
import binascii
from odoo.tools.translate import _
from datetime import datetime

try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')


class FormCSBulkImport(models.TransientModel):
    _name = "formcs.bulk.import"
    _description = "FormCS Bulk Import"

    file_data = fields.Binary('Import File')

    def import_file(self):
        try:
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.file_data))
                fp.seek(0)
                values = {}
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
            except:
                raise UserError(_("Invalid XLSX file! (or) File Extension is incorrect!"))

            cell_value = sheet.cell_value(4, 0)
            if cell_value == 'Profit & Loss Details':
                template_lis = ['Year of Assessment', 'Period Start Date', 'Period End Date', 'UEN', '', 'Total Revenue', 'Cost of Goods Sold', 'Interest income', 'Dividend Income - One-tier/ Tax Exempt', 'Gross Rental Income', 'Other Taxable Income', 'Other non Taxable Income', 'Bank Charges', 'Commission (Other than Expenses incurred to derive Rental Income)', 'Depreciation Expense', "Director's fees", "Director's Remuneration (excluding Director's fees)", 'Donations', 'CPF contribution', 'Entertainment Expenses', 'Expenses incurred to derive Rental Income - Commission', 'Expenses incurred to derive Rental Income - Insurance', 'Expenses incurred to derive Rental Income - Interest', 'Expenses incurred to derive Rental Income - Property tax', 'Expenses incurred to derive Rental Income - Repair and maintenance', 'Expenses incurred to derive Rental Income - Others', 'Fixed assets expensed off', 'Amortisation Expense', 'Insurance (other than medical expenses and expenses incurred to derive Rental Income)', 'Interest expenses (other than expenses incurred to derive rental Income)', 'Impairment loss/ reversal of impairment loss for bad debts', 'Medical expenses (including medical insurance)', 'Net Gains/ Losses on disposal of property, plant and equipment', 'Net Gains/ Losses on foreign exchange adjustment', 'Net Gains/ Losses on Other Items', 'Miscellaneous Expenses', 'Other private/ capital expenses', 'Other Finance Cost', 'Penalties/ Fine', 'Professional fees', 'Property tax (other than expenses incurred to derive rental income)', 'Rent expense', 'Repairs and Maintenance (excluding private motor vehicles and expenses incurred to derive rental income)', 'Repairs and Maintenance (private motor vehicles)', 'Sales and Marketing', 'Skills Development Levy/ Foreign Worker Levy', "Staff remuneration (other than director's remuneration)", 'Staff Welfare', 'Telecommunication/ Utilities', 'Training', 'Transport/ Travelling Expenses', 'Upkeep Of Non-private Motor Vehicles', 'Upkeep Of Private Motor Vehicles - Private', '', 'Inventories', 'Trade Receivables']
                is_pl = True
            else:
                template_lis = [
                    'Year of Assessment', 'Period Start Date', 'Period End Date', 'UEN', '',
                    "Revenue",
                    "Gross Profit/ Loss",
                    "Directors' Fees and Remuneration",
                    "Total Remuneration excluding Directors' Fees",
                    "Medical Expenses",
                    "Transport/ Travelling Expenses",
                    "Entertainment Expenses",
                    "Inventories",
                    "Trade Receivables",
                    "",
                    "Net Profit/ Loss before Tax as per Financial Statements",
                    "Separate Source Income",
                    "Non-Taxable Income",
                    "Non-Tax Deductible Expenses",
                    "Adjusted Profit/ Loss before Other Deductions",
                    "Deduction for Renovation or Refurbishment Works under Section 14N",
                    "Enhanced Deductions under Enterprise Innovation Scheme (EIS) for Training; Innovation Projects carried out with Partner Institutions; Licensing of Intellectual Property Rights; Registration of Intellectual Property; Qualfiying R&D undertaken in Singapore",
                    "Further Deductions/ Other Deductions including revenue expenses capitalised or expenses incurred under Section 14R",
                    "Adjusted Profit/ Loss before Capital Allowances",
                    "Balancing Charge",
                    "Unutilised Capital Allowances brought forward",
                    "Current Year Capital Allowances",
                    "Unutilised Losses brought forward",
                    "",
                    "Gross Rental Income",
                    "Less: Deductible Expenses",
                    "Net Rental Income",
                    "Interest Income",
                    "Other Taxable Income",
                    "Total Income/ Losses (before Donations)",
                    "Unutilised Donations brought forward",
                    "Current Year Donations",
                    "Total Income/ Losses (after Donations)",
                    "Unutilised Capital Allowances carried forward",
                    "Unutilised Losses carried forward",
                    "Unutilised Donations carried forward"]
                is_pl = False

            template_position = {item: str(index + 1) for index, item in enumerate(template_lis)}

            fmt_string = "\n".join(f"{value and value or '<EMPTY CELL>'}" for value in template_lis)
            for col_no in range(sheet.ncols):
                column_data = []
                if col_no < 1:
                    continue                
                for row_no in range(sheet.nrows):
                    cell_value = sheet.cell_value(row_no, col_no)
                    
                    if sheet.cell_type(row_no, col_no) == xlrd.XL_CELL_DATE: # Check if the cell is a date
                        cell_value = xlrd.xldate_as_datetime(cell_value, workbook.datemode)
                        column_data.append(cell_value.strftime('%Y-%m-%d'))
                    else:
                        if col_no >= 2 and row_no > 5 and isinstance(cell_value, str) and ',' in cell_value:
                            cleaned_value = float(cell_value.replace(',', ''))
                            column_data.append(cleaned_value)
                        else:
                            column_data.append(cell_value)

                print(f"\nColumn {col_no + 1}: {column_data}")

                if col_no == 0:
                    trimmed_given_lis = [item.strip() for item in column_data]
                    column_data = list(set(trimmed_given_lis))

                    for item in column_data:
                        if item in template_lis:
                            fmt_string = "\n".join(f"{value}" for value in template_lis)
                            raise UserError(_("The data under the Column A is suppose to be present under the Column B but not under Column A. Please follow the standard template format. Expected format under the Column B is \n\n%s" % fmt_string))

                elif col_no == 1:
                    if column_data[0].strip() == '':
                        raise UserError(_("Column B is expected with the labels in the order as mentioned below: \n\n %s" % fmt_string))

                    for i in range(0,len(template_lis)):

                        if i > len(column_data) - 1:
                            raise UserError(_("There seems to be few or more labels missing under the Column B. Please follow the standard template format. Expected format under the Column B is: \n\n" + fmt_string))
                        item = column_data[i]
                        if item.strip() not in template_lis:
                            error_msg = "'" + str(item) + "' is not the label expected to be present under the Column B. Please follow the standard template format. Expected format under the Column B is: \n\n" + fmt_string
                            raise UserError(_(error_msg))
                        elif template_lis[i] == '' and item.strip() != '':
                            error_msg = "The value at the Row " + str(i+1) + " is expected to be empty under the Column B. Please follow the standard template format. Expected format under the Column B is: \n\n" + fmt_string
                            raise UserError(_(error_msg)) 
                        elif template_lis[i] != '' and item.strip() == '':
                            error_msg = "The Row " + str(i + 1) + " cannot be empty under the Column B. Please follow the standard template format. Expected format under the Column B is: \n\n" + fmt_string
                            raise UserError(_(error_msg))
                        elif item.strip() != template_lis[i]:
                            if item.strip() in template_lis:
                                error_msg = "The label in the cell label at Row " + str(i+1) + " under the Column B must be '" + str(template_lis[i]) + "'. Please follow the standard template format. Expected format under the Column B is: \n\n" + fmt_string
                            else:
                                error_msg = "'" + str(item) + "' is not in the right cell position under the Column B.\n The right position must be at the Row: " + template_position[item.strip()] + ". Expected format under the Column B is: \n\n" + fmt_string
                            raise UserError(_(error_msg))

                elif col_no > 1:

                    if column_data[0] == '':
                        raise UserError(_("The 'Year of Assessment' is empty for one or more Columns. Please correct the file."))
                    elif column_data[1] == '':
                        raise UserError(_("The 'Period Start Date' is empty for one or more Columns. Please correct the file."))
                    elif column_data[2] == '':
                        raise UserError(_("The 'Period End Date' is empty for one or more Columns. Please correct the file."))
                    elif column_data[3] == '':
                        raise UserError(_("The 'UEN' is empty for one or more Columns. Please correct the file."))

                    column_data[5:] = [int(x and x or 0) for x in column_data[5:]]
                    if is_pl:
                        obj = self.env['form.cs'].create({
                            'ya': str(int(column_data[0])),
                            'basisPeriodFrom': column_data[1],
                            'basisPeriodTo': column_data[2],
                            'uen': str(column_data[3]).split('.')[0],
                            'totalRevenue': column_data[5],
                            'costOfGoodsSold': column_data[6],
                            'sgIntDisc': column_data[7],
                            'oneTierTaxDividendIncome': column_data[8],
                            'c1_GrossRent': column_data[9],
                            'sgOtherI': column_data[10],
                            'otherNonTaxableIncome': column_data[11],
                            'bankCharges': column_data[12],
                            'commissionOther': column_data[13],
                            'depreciationExpense': column_data[14],
                            'directorsFees': column_data[15],
                            'directorsRemunerationExcludingDirectorsFees': column_data[16],
                            'donations': column_data[17],
                            'cpfContribution': column_data[18],
                            'c1_EntertainExp': column_data[19],
                            'commissionExpRentalIncome': column_data[20],
                            'insuranceExpRentalIncome': column_data[21],
                            'interestExpRentalIncome': column_data[22],
                            'propertyTaxExpRentalIncome': column_data[23],
                            'repairMaintenanceExpRentalIncome': column_data[24],
                            'otherExpRentalIncome': column_data[25],
                            'fixedAssetsExpdOff': column_data[26],
                            'amortisationExpense': column_data[27],
                            'insuranceExpOther': column_data[28],
                            'interestExpOther': column_data[29],
                            'impairmentLossReversalOfImpairmentLossForBadDebts': column_data[30],
                            'medicalExpIncludingMedicalInsurance': column_data[31],
                            'netGainsOrLossesOnDisposalOfPPE': column_data[32],
                            'netGainsOrLossesOnForex': column_data[33],
                            'netGainsOrLossesOnOtherItems': column_data[34],
                            'miscExp': column_data[35],
                            'otherPrivateOrCapitalExp': column_data[36],
                            'otherFinanceCost': column_data[37],
                            'penaltiesOrFine': column_data[38],
                            'professionalFees': column_data[39],
                            'propertyTaxOther': column_data[40],
                            'rentExp': column_data[41],
                            'repairMaintenanceExcludingUpkeepOfPrivateVehiclesAndExp': column_data[42],
                            'repairsMaintenanceForPrivateVehicles': column_data[43],
                            'salesAndMarketingExpense': column_data[44],
                            'skillsDevelopmentForeignWorkerLevy': column_data[45],
                            'staffRemunerationOtherThanDirectorsRemuneration': column_data[46],
                            'staffWelfare': column_data[47],
                            'telecommunicationOrUtilities': column_data[48],
                            'training': column_data[49],
                            'c1_TransportExp': column_data[50],
                            'upkeepNonPrivateVehicles': column_data[51],
                            'upkeepPrivateVehicles': column_data[52],
                            'inventories': column_data[54],
                            'tradeReceivables': column_data[55]
                            })
                        obj.message_post(body=_('Record created from Bulk Import of Detailed Profit & Loss'))
                    else:
                        obj = self.env['form.cs'].with_context({'bulk_import': False}).create({
                            'ya': str(int(column_data[0])),
                            'basisPeriodFrom': column_data[1],
                            'basisPeriodTo': column_data[2],
                            'uen': str(column_data[3]).split('.')[0],
                            'DataFormCS_totalRevenue': column_data[5],
                            'DataFormCS_grossPL': column_data[6],
                            'DataFormCS_directorFee': column_data[7],
                            'DataFormCS_totRemuneration': column_data[8],
                            'DataFormCS_medicalExp': column_data[9],
                            'DataFormCS_c1_TransportExp': column_data[10],
                            'DataFormCS_c1_EntertainExp': column_data[11],
                            'DataFormCS_inventories': column_data[12],
                            'DataFormCS_tradeReceivables': column_data[13],
                            'DataFormCS_profitLossBeforeTaxation': column_data[15],
                            'DataFormCS_sepSrcIncome': column_data[16],
                            'DataFormCS_receiptNotTxAmt': column_data[17],
                            'DataFormCS_c1_NTDeductibleExp': column_data[18],
                            'DataFormCS_adjPLBefDed': column_data[19],
                            'DataFormCS_renoWorksExpS14Q': column_data[20],
                            'DataFormCS_c1_EnhancedEISDed': column_data[21],
                            'DataFormCS_c1_FurtherDed': column_data[22],
                            'DataFormCS_sgAdjPLAft': column_data[23],
                            'DataFormCS_c1_BC': column_data[24],
                            'DataFormCS_unutilCABFNorm': column_data[25],
                            'DataFormCS_cyCANorm': column_data[26],
                            'DataFormCS_unutilLossBFNorm': column_data[27],
                            'DataFormCS_c1_GrossRent': column_data[29],
                            'DataFormCS_c1_DedExp': column_data[30],
                            'DataFormCS_sgRent': column_data[31],
                            'DataFormCS_sgIntDisc': column_data[32],
                            'DataFormCS_sgOtherI': column_data[33],
                            'DataFormCS_totSgFI': column_data[34],
                            'DataFormCS_unutilDonationBFNorm': column_data[35],
                            'DataFormCS_cyDonation': column_data[36],
                            'DataFormCS_ci': column_data[37],
                            'DataFormCS_unutilCACFNorm': column_data[38],
                            'DataFormCS_unutilLossCFNorm': column_data[39],
                            'DataFormCS_unutilDonationCFNorm': column_data[40],
                            'DataFormCS_uCALDChangePrinAct': '2',
                            'DataFormCS_sholderChange': '2',
                            'DataFormCS_fullTxX': '2',
                            'DataFormCS_appStockConvAsset': '2',
                            'DataFormCS_eis_ClaimCashPayout': '2',
                            'DataFormCS_eis_ClaimDedAll': '2',
                            'skip_tax_conversion': True
                        })
                        obj.message_post(body=_('Record created from Bulk Import of Tax Computation'))

        except Exception as error:
            error_traceback = error.__traceback__
            error_dict = {
                "errorType": type(error).__name__,
                "message": str(error),
                "fileName": error_traceback.tb_frame.f_code.co_filename,
                "handlerName": error_traceback.tb_frame.f_code.co_name,
                "lineNumber": error_traceback.tb_lineno,
            }
            if error_dict['errorType'] in ['UserError','ValidationError']:
                raise UserError(_("%s") % str(error_dict['message']))
            else:
                error_string = "\n".join(f"{key}: {value}" for key, value in error_dict.items())
                raise UserError(_("Technical Error:: \n%s" % error_string))
        finally:
            fp.close()

        action = self.env.ref('metroerp_iras.form_cs_action').sudo()
        return {
            'type': 'ir.actions.act_window',
            'name': action.name,
            'res_model': action.res_model,
            'view_mode': 'kanban,tree,form',
            'target': 'current',
        }
