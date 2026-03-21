# -*- coding: utf-8 -*-

import base64
from pyparsing import line
import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.res_bank import sanitize_account_number
import io
import psycopg2
import logging
import tempfile
import binascii
from datetime import datetime


_logger = logging.getLogger(__name__)

try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')

try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    _order="date, id"

    # Ensure transactions can be imported only once (if the import format provides unique transaction ids)
    unique_import_id = fields.Char(string='Import ID', readonly=True, copy=False)

    _sql_constraints = [
        ('unique_import_id', 'unique (unique_import_id)', 'A bank account transactions can be imported only once !')
    ]

    account_code = fields.Char(string='Auto Reconcile Account Code')
    tax_name = fields.Char(string='Tax Name')

    # def _prepare_move_line_vals(self, amount):
    #     print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>method called333")
    #     """Override to inject payment_ref into move line name."""
    #     res = super()._prepare_move_line_vals(amount)

    #     # Set 'name' (label) in the journal entry line from the statement line
    #     if self.payment_ref:
    #         res['name'] = self.payment_ref
    #     elif self.name:
    #         res['name'] = self.name  # fallback to label if payment_ref not set
    #     return res


class AccountBankStatementImport(models.TransientModel):
    _name = 'account.bank.statement.import'
    _description = 'Import Bank Statement'

    attachment_ids = fields.Many2many('ir.attachment', string='Files', required=True,
                                      help='Get you bank statements in electronic format from your bank and'
                                           ' select them here.')
    bank_select = fields.Selection([('UOB','UOB'),('DBS IDEAL','DBS IDEAL'),('OCBC','OCBC'),('CIMB','CIMB'),('YOUBIZ','YOUBIZ'),('AIRWALLEX', 'AIRWALLEX'),('MAYBANK','MAYBANK'),('HSBC', 'HSBC'),('CUSTOM BANK','CUSTOM BANK')], string='Select Bank Template', default='UOB')

    def action_download_templates(self):
        attachment = self.env['ir.attachment'].search([
            ('name', '=', 'account_bank_statement_template.xlsx'),
            ('public', '=', True),
        ], limit=1)

        if not attachment or not attachment.datas:
            raise UserError(_("Bank Statement Template not found or file is missing. Please contact the administrator."))

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self'
        }

    # def action_account_bank_statement(self):
    #     action = self.env["ir.actions.actions"]._for_xml_id("account.action_bank_statement_tree")
    #     action.update({
    #         'views': [[False, 'form']],
    #         'context': "{'default_journal_id': " + str(
    #             self.env.context.get('journal_id')) + ", 'default_manual_reconciliation': True}",
    #     })
    #     return action
   


    def get_partner(self, value):
        partner = self.env['res.partner'].search([('name', '=', value)])
        return partner.id if partner else False

    def get_currency(self, value):
        currency = self.env['res.currency'].search([('name', '=', value)])
        return currency.id if currency else False
    
    def create_statement(self, values):
        statement = self.env['account.bank.statement'].create(values)
        return statement
    
    def import_file_custom(self):
        # In case of CSV files, only one file can be imported at a time.
        if len(self.attachment_ids) > 1:
            raise UserError(_('Only one CSV file can be selected.'))

        allowed_mime_types = ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','text/csv']
        if self.attachment_ids.mimetype not in allowed_mime_types:
            raise UserError(_('Please Upload XLSX file or CSV file.'))
        ctx = dict(self.env.context)
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'account.bank.statement.line',
            'file': base64.b64decode(self.attachment_ids.datas),
            'file_name': self.attachment_ids.name,
            'file_type': 'text/csv'
        })
        ctx['wizard_id'] = import_wizard.id
        return {
            'type': 'ir.actions.client',
            'tag': 'import_bank_stmt',
            'params': {
                'model': 'account.bank.statement.line',
                'context': ctx,
                'filename': self.attachment_ids.name,
            }
        }
    

    def import_file(self):
        if self.bank_select == 'UOB':
            for data_file in self.attachment_ids:
                file_name = data_file.name.lower()
                if file_name.strip().endswith(('.csv','.xls')): #TODO or file_name.strip().endswith('.xlsx')
                    statement = False
                    if file_name.strip().endswith('.csv'):
                        keys = ['date', 'payment_ref', 'narration', 'amount']
                        try:
                            csv_data = base64.b64decode(data_file.datas)
                            data_file = io.StringIO(csv_data.decode("utf-8"))
                            data_file.seek(0)
                            file_reader = []
                            values = {}
                            csv_reader = csv.reader(data_file, delimiter=',')
                            file_reader.extend(csv_reader)
                        except:
                            raise UserError(_("UOB Invalid CSV file!"))
                        vals_list = []
                        values = {}
                        currency_id = False
                        print("len(file_reader) ===",len(file_reader))
                        for i in range(len(file_reader)):
                            print("\ni ===",i)
                            field = list(map(str, file_reader[i]))
                            # values = dict(zip(keys, field))
                            print("field ===",field)
                            # print("values ===",values,"\n")

                            if vals_list and not field[0]: # When the bank statement ends.
                                print("breaks.......")
                                break
                            if i == 5:
                                if field[0] == 'Account Currency:': # To get the currency
                                    currency_id = self.get_currency(field[1])
                            elif i <= 10: # Skip the processing of Bank statements starts for these lines
                                continue
                            else: # Start the processing from line 11
                                try:
                                    date_obj = datetime.strptime(field[0], '%d/%m/%Y')
                                except Exception as e:
                                    raise ValidationError(_(repr(e)))
                                narration = field[1] + " " + field[2]
                                print(field[4]," ", field[5])
                                try:
                                    # deposit = float(field[4])
                                    deposit = float(field[4].replace(",", ""))
                                except ValueError:
                                    deposit = 0.0
                                try:
                                    # withdraw = float(field[5])
                                    withdraw = float(field[5].replace(",", ""))
                                except ValueError:
                                    withdraw = 0.0
                                print(deposit," ", withdraw)

                                if deposit > 0.0:
                                    amount = deposit
                                elif withdraw > 0.0:
                                    amount = withdraw * -1
                                else:
                                    amount = 0.0
                                values = {
                                    'date': date_obj.strftime('%Y-%m-%d'),
                                    'narration': narration,
                                    'payment_ref': field[3],
                                    'amount': amount,
                                }
                                if currency_id:
                                    values.update({'currency_id': currency_id})
                                vals_list.append((0, 0, values))
                        statement_vals = {
                            # 'name': 'Statement Of ' + str(datetime.today().date()),
                            'journal_id': self.env.context.get('active_id'),
                            'line_ids': vals_list
                        }
                        if len(vals_list) != 0:
                            statement = self.create_statement(statement_vals)

                   
                    elif file_name.strip().endswith('.xls'):
                        try:
                            fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xls")
                            fp.write(binascii.a2b_base64(data_file.datas))
                            fp.seek(0)
                            values = {}
                            workbook = xlrd.open_workbook(fp.name)
                            sheet = workbook.sheet_by_index(0)
                        except:
                            raise UserError(_("UOB IDEAL Invalid XLS file!"))
                       
                        vals_list = []
                        line = []
                        for row_no in range(sheet.nrows):
                            val = {}
                            values = {}
                            if row_no <= 0:
                                fields = list(map(lambda row: row.value, sheet.row(row_no)))
                            else:
                                # Convert map to a list
                                line = list(map(
                                    lambda row: isinstance(row.value, bytes) and row.value.decode('utf-8') or str(row.value), sheet.row(row_no)))
                                if vals_list and not line[0]: # When the bank statement ends.
                                    print("breaks.......")
                                    break
                                if row_no == 5:
                                    if line[0] == 'Account Currency:': # To get the currency
                                        currency_id = self.get_currency(line[1])
                                elif row_no <= 10: # Skip the processing of Bank statements starts for these lines
                                    continue
                                else: # Start the processing from line 11
                                    try:
                                        date_obj = datetime.strptime(line[0], '%d/%m/%Y')
                                    except Exception as e:
                                        raise ValidationError(_(repr(e)))
                                    narration = line[1] + " " + line[2]
                                    print(line[4]," ", line[5])
                                    try:
                                        # deposit = float(field[4])
                                        deposit = float(line[4].replace(",", ""))
                                    except ValueError:
                                        deposit = 0.0
                                    try:
                                        # withdraw = float(field[5])
                                        withdraw = float(line[5].replace(",", ""))
                                    except ValueError:
                                        withdraw = 0.0
                                    print(deposit," ", withdraw)

                                    if deposit > 0.0:
                                        amount = deposit
                                    elif withdraw > 0.0:
                                        amount = withdraw * -1
                                    else:
                                        amount = 0.0
                                    values = {
                                        'date': date_obj.strftime('%Y-%m-%d'),
                                        'narration': narration,
                                        'payment_ref': line[3],
                                        'amount': amount,
                                    }
                                    if currency_id:
                                        values.update({'currency_id': currency_id})
                                    vals_list.append((0, 0, values))
                        statement_vals = {
                            # 'name': 'Statement Of ' + str(datetime.today().date()),
                            'journal_id': self.env.context.get('active_id'),
                            'line_ids': vals_list
                        }
                        if len(vals_list) != 0:
                            statement = self.create_statement(statement_vals)

                    if statement:
                        return {
                            'type': 'ir.actions.act_window',
                            'res_model': 'account.bank.statement',
                            'view_mode': 'form',
                            'res_id': statement.id,
                            'views': [(False, 'form')],
                        }
                else:
                    raise ValidationError(_("Unsupported File Type. Current allowed file format is CSV only."))
                
        
        

        elif self.bank_select == 'DBS IDEAL':
            for data_file in self.attachment_ids:
                file_name = data_file.name.lower()
                if file_name.strip().endswith(('.csv', '.xls')):
                    statement = False
                    if file_name.strip().endswith('.csv'):
                        keys = ['date', 'payment_ref', 'transaction_type', 'amount']
                        try:
                            csv_data = base64.b64decode(data_file.datas)
                            data_file = io.StringIO(csv_data.decode("utf-8"))
                            data_file.seek(0)
                            file_reader = []
                            values = {}
                            csv_reader = csv.reader(data_file, delimiter=',')
                            file_reader.extend(csv_reader)
                        except:
                            raise UserError(_("DBS IDEAL Invalid CSV file!"))


                        vals_list = []
                        values = {}
                        print("len(file_reader) ===",len(file_reader))
                        for i in range(len(file_reader)):
                            print("\ni ===",i)
                            field = list(map(str, file_reader[i]))
                            print("field ===",field)
                            if field and field[0] == 'Printed By':
                                print("DBS IDEAL processing stops...")
                                break

                            elif i <= 5: # Skip the processing of Bank statements starts for these lines
                                continue

                            try:
                                date_obj = datetime.strptime(field[0], '%d-%b-%Y')
                            except Exception as e:
                                raise ValidationError(_(repr(e)))

                            transaction_type = field[2]
                            print(field[2])

                            try:
                                credit = float(field[5].replace(",", ""))
                            except ValueError:
                                credit = 0.0

                            try:
                                debit = float(field[4].replace(",", ""))
                            except ValueError:
                                debit = 0.0

                            print(credit, " ", debit)

                            if credit > 0.0:
                                amount = credit
                            elif debit > 0.0:
                                amount = debit * -1
                            else:
                                amount = 0.0

                            values = {
                                'date': date_obj.strftime('%Y-%m-%d'),
                                'transaction_type': transaction_type,
                                'payment_ref': field[3],
                                'amount': amount,
                            }

                            vals_list.append((0, 0, values))

                        statement_vals = {
                            'journal_id': self.env.context.get('active_id'),
                            'line_ids': vals_list
                        }

                        if len(vals_list) != 0:
                            statement = self.create_statement(statement_vals)

                    elif file_name.strip().endswith('.xls'):
                        keys = ['date', 'payment_ref', 'transaction_type', 'amount']
                        try:
                            fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xls")
                            fp.write(binascii.a2b_base64(data_file.datas))
                            fp.seek(0)
                            values = {}
                            workbook = xlrd.open_workbook(fp.name)
                            sheet = workbook.sheet_by_index(0)
                        except:
                            raise UserError(_("DBS IDEAL Invalid XLS file!"))

                        vals_list = []
                        line = []
                        for row_no in range(sheet.nrows):
                            val = {}
                            values = {}
                            if row_no <= 0:
                                fields = list(map(lambda row: row.value, sheet.row(row_no)))
                            else:
                                # Convert map to a list
                                line = list(map(
                                    lambda row: isinstance(row.value, bytes) and row.value.decode('utf-8') or str(row.value), sheet.row(row_no)))

                            if line and line[0] == 'Printed By':
                                print("DBS IDEAL processing stops...")
                                break

                            elif row_no <= 5:  # Skip the processing of Bank statements starts for these lines
                                continue

                            try:
                                date_obj = datetime.strptime(line[0], '%d-%b-%Y')
                            except Exception as e:
                                raise ValidationError(_(repr(e)))

                            transaction_type = line[2]
                            print(line[2])

                            try:
                                credit = float(line[5].replace(",", "")) if line[5] and line[5] != "-" else 0.0
                            except ValueError:
                                credit = 0.0

                            try:
                                debit = float(line[4].replace(",", "")) if line[4] and line[4] != "-" else 0.0
                            except ValueError:
                                debit = 0.0

                            print(credit, " ", debit)

                            if credit > 0.0:
                                amount = credit
                            elif debit > 0.0:
                                amount = debit * -1
                            else:
                                amount = 0.0

                            values = {
                                'date': date_obj.strftime('%Y-%m-%d'),
                                'transaction_type': transaction_type,
                                'payment_ref': line[3],
                                'amount': amount,
                            }

                            vals_list.append((0, 0, values))

                        statement_vals = {
                            'journal_id': self.env.context.get('active_id'),
                            'line_ids': vals_list
                        }

                        if len(vals_list) != 0:
                            statement = self.create_statement(statement_vals)

                    if statement:
                        return {
                            'type': 'ir.actions.act_window',
                            'res_model': 'account.bank.statement',
                            'view_mode': 'form',
                            'res_id': statement.id,
                            'views': [(False, 'form')],
                        }

                else:
                    raise ValidationError(_("Unsupported File Type. Current allowed file format is CSV only."))
        

        elif self.bank_select == 'OCBC':
            for data_file in self.attachment_ids:
                file_name = data_file.name.lower()
                if file_name.strip().endswith('.csv'):
                    statement = False
                    if file_name.strip().endswith('.csv'):
                        keys = ['currency_id','date','transaction_type','payment_ref','ref', 'amount']
                        try:
                            csv_data = base64.b64decode(data_file.datas)
                            data_file = io.StringIO(csv_data.decode("utf-8"))
                            data_file.seek(0)
                            file_reader = []
                            values = {}
                            csv_reader = csv.reader(data_file, delimiter=',')
                            file_reader.extend(csv_reader)
                        except:
                            raise UserError(_("OCBC Invalid CSV file!"))
                        vals_list = []
                        values = {}
                        currency_id = False
                        print("len(file_reader) ===",len(file_reader))
                        for i in range(len(file_reader)):
                            print("\ni ===",i)
                            field = list(map(str, file_reader[i]))
                            print("field ===",field)

                            if vals_list and not field[0]: # When the bank statement ends.
                                print("breaks.......")
                                break
                
                            elif i <= 0: # Skip the processing of Bank statements starts for these lines
                                continue
                            else: # Start the processing from line 1
                                try:
                                    date_obj = datetime.strptime(field[7], '%Y%m%d')
                                except Exception as e:
                                    raise ValidationError(_(repr(e)))
                                ref = field[18] + " " + field[19]
                                print(field[18]," ", field[19])
                                transaction_type = field[15]
                                print(field[2])

                                try:
                                    credit = float(field[14].replace(",", ""))
                                except ValueError:
                                    credit = 0.0

                                try:
                                    debit = float(field[13].replace(",", ""))
                                except ValueError:
                                    debit = 0.0

                                print(credit, " ", debit)

                                if credit > 0.0:
                                    amount = credit
                                elif debit > 0.0:
                                    amount = debit * -1
                                else:
                                    amount = 0.0

                                values = {
                                    'date': date_obj.strftime('%Y-%m-%d'),
                                    'transaction_type': transaction_type,
                                    'ref': ref,
                                    'payment_ref': field[17],
                                    'amount': amount,
                                    'currency_id':  self.get_currency(field[1])
                                }
                                vals_list.append((0, 0, values))
                        statement_vals = {
                            'journal_id': self.env.context.get('active_id'),
                            'line_ids': vals_list
                        }
                        if len(vals_list) != 0:
                            statement = self.create_statement(statement_vals)


                    if statement:
                        return {
                            'type': 'ir.actions.act_window',
                            'res_model': 'account.bank.statement',
                            'view_mode': 'form',
                            'res_id': statement.id,
                            'views': [(False, 'form')],
                        }

                else:
                    raise ValidationError(_("Unsupported File Type. Current allowed file format is CSV only."))
        
        if self.bank_select == 'CIMB':
            for data_file in self.attachment_ids:
                file_name = data_file.name.lower()
                if file_name.strip().endswith('.csv'): #TODO or file_name.strip().endswith('.xlsx')
                    statement = False
                    if file_name.strip().endswith('.csv'):
                        keys = ['date', 'payment_ref', 'narration', 'amount']
                        try:
                            csv_data = base64.b64decode(data_file.datas)
                            data_file = io.StringIO(csv_data.decode("utf-8"))
                            data_file.seek(0)
                            file_reader = []
                            values = {}
                            csv_reader = csv.reader(data_file, delimiter=',')
                            file_reader.extend(csv_reader)
                        except:
                            raise UserError(_("CIMB Invalid CSV file!"))
                        vals_list = []
                        values = {}
                        currency_id = False
                        print("len(file_reader) ===",len(file_reader))
                        for i in range(len(file_reader)):
                            print("\ni ===",i)
                            field = list(map(str, file_reader[i]))
                            # values = dict(zip(keys, field))
                            print("field ===",field)
                            # print("values ===",values,"\n")

                            if vals_list and not field[0]: # When the bank statement ends.
                                print("breaks.......")
                                break
                            if i == 5:
                                if field[0] == 'Account Currency:': # To get the currency
                                    currency_id = self.get_currency(field[1])
                            elif i <= 5: # Skip the processing of Bank statements starts for these lines
                                continue
                            else: # Start the processing from line 6
                                try:
                                    date_obj = datetime.strptime(field[1], '%d-%b-%Y')
                                except Exception as e:
                                    raise ValidationError(_(repr(e)))
                                narration = field[2]
                                try:
                                    # deposit = float(field[4])
                                    deposit = float(field[8].replace(",", ""))
                                except ValueError:
                                    deposit = 0.0
                                try:
                                    # withdraw = float(field[5])
                                    withdraw = float(field[7].replace(",", ""))
                                except ValueError:
                                    withdraw = 0.0
                                print(deposit," ", withdraw)

                                if deposit > 0.0:
                                    amount = deposit
                                elif withdraw > 0.0:
                                    amount = withdraw * -1
                                else:
                                    amount = 0.0
                                values = {
                                    'date': date_obj.strftime('%Y-%m-%d'),
                                    'narration': narration,
                                    'payment_ref': field[4],
                                    'ref': field[3],
                                    'amount': amount,
                                }
                                if currency_id:
                                    values.update({'currency_id': currency_id})
                                vals_list.append((0, 0, values))
                        statement_vals = {
                            # 'name': 'Statement Of ' + str(datetime.today().date()),
                            'journal_id': self.env.context.get('active_id'),
                            'line_ids': vals_list
                        }
                        if len(vals_list) != 0:
                            statement = self.create_statement(statement_vals)

                    if statement:
                        return {
                            'type': 'ir.actions.act_window',
                            'res_model': 'account.bank.statement',
                            'view_mode': 'form',
                            'res_id': statement.id,
                            'views': [(False, 'form')],
                        }
                else:
                    raise ValidationError(_("Unsupported File Type. Current allowed file format is CSV only."))
        

        elif self.bank_select == 'YOUBIZ':
            for data_file in self.attachment_ids:
                file_name = data_file.name.lower()
                if file_name.strip().endswith('.csv'):
                    statement = False
                    if file_name.strip().endswith('.csv'):
                        keys = ['currency_id','date','transaction_type','payment_ref','ref','narration','amount']
                        try:
                            csv_data = base64.b64decode(data_file.datas)
                            data_file = io.StringIO(csv_data.decode("utf-8"))
                            data_file.seek(0)
                            file_reader = []
                            values = {}
                            csv_reader = csv.reader(data_file, delimiter=',')
                            file_reader.extend(csv_reader)
                        except:
                            raise UserError(_("YOUBIZ Invalid CSV file!"))
                        vals_list = []
                        values = {}
                        currency_id = False
                        print("len(file_reader) ===",len(file_reader))
                        for i in range(len(file_reader)):
                            print("\ni ===",i)
                            field = list(map(str, file_reader[i]))
                            print("field ===",field)

                            if vals_list and not field[0]: # When the bank statement ends.
                                print("breaks.......")
                                break
                
                            elif i <= 0: # Skip the processing of Bank statements starts for these lines
                                continue
                            else: # Start the processing from line 1
                                # Skip cancelled transactions based on transaction_status (field[6])
                                if field[6].strip().lower() == 'cancelled':
                                    continue  # skip this line
                                
                                try:
                                    date_obj = datetime.strptime(field[2], '%Y-%m-%d')
                                except Exception as e:
                                    raise ValidationError(_(repr(e)))
                                
                                transaction_type = field[4] + " " + field[5]
                                print(field[2])

                                # try:
                                #     credit = float(field[14].replace(",", ""))
                                # except ValueError:
                                #     credit = 0.0

                                # try:
                                #     debit = float(field[13].replace(",", ""))
                                # except ValueError:
                                #     debit = 0.0

                                # print(credit, " ", debit)

                                # if credit > 0.0:
                                #     amount = credit
                                # elif debit > 0.0:
                                #     amount = debit * -1
                                # else:
                                #     amount = 0.0

                                values = {
                                    'date': date_obj.strftime('%Y-%m-%d'),
                                    'transaction_type': transaction_type,
                                    'payment_ref': field[21],
                                    'ref': field[15],
                                    'narration': field[24],
                                    'amount': field[8],
                                    'currency_id':  self.get_currency(field[1])
                                }
                                vals_list.append((0, 0, values))
                        statement_vals = {
                            'journal_id': self.env.context.get('active_id'),
                            'line_ids': vals_list
                        }
                        if len(vals_list) != 0:
                            statement = self.create_statement(statement_vals)


                    if statement:
                        return {
                            'type': 'ir.actions.act_window',
                            'res_model': 'account.bank.statement',
                            'view_mode': 'form',
                            'res_id': statement.id,
                            'views': [(False, 'form')],
                        }

                else:
                    raise ValidationError(_("Unsupported File Type. Current allowed file format is CSV only."))

        # prakash
        elif self.bank_select == 'AIRWALLEX':
            for data_file in self.attachment_ids:
                file_name = data_file.name.lower()
                if file_name.strip().endswith('.csv'):
                    statement = False
                    if file_name.strip().endswith('.csv'):
                        keys = ['currency_id', 'date', 'transaction_type', 'payment_ref', 'amount']
                        try:
                            csv_data = base64.b64decode(data_file.datas)
                            data_file = io.StringIO(csv_data.decode("utf-8"))
                            data_file.seek(0)
                            file_reader = []
                            values = {}
                            csv_reader = csv.reader(data_file, delimiter=',')
                            file_reader.extend(csv_reader)
                        except:
                            raise UserError(_("AIRWALLEX Invalid CSV file!"))
                        vals_list = []
                        values = {}
                        currency_id = False
                        for i in range(len(file_reader)):
                            field = list(map(str, file_reader[i]))
                            print("field ===", field)

                            if vals_list and not field[0]:  # When the bank statement ends.
                                print("breaks.......")
                                break

                            elif i <= 0:  # Skip the processing of Bank statements starts for these lines
                                continue
                            else:  # Start the processing from line 1
                                # Skip cancelled transactions based on transaction_status (field[6])
                                # if field[6].strip().lower() == 'cancelled':
                                #     continue  # skip this line

                                try:
                                    date_obj = datetime.strptime(field[0], "%Y-%m-%dT%H:%M:%S%z").date()
                                    # date_obj = datetime.strptime(field[0], '%Y-%m-%d')
                                except Exception as e:
                                    raise ValidationError(_(repr(e)))

                                transaction_type = field[1]

                                try:
                                    credit = float(field[13].replace(",", ""))
                                except ValueError:
                                    credit = 0.0

                                try:
                                    debit = float(field[12].replace(",", ""))
                                except ValueError:
                                    debit = 0.0

                                if credit > 0.0:
                                    amount = credit
                                elif debit > 0.0:
                                    amount = debit * -1
                                else:
                                    amount = 0.0

                                values = {
                                    'date': date_obj.strftime('%Y-%m-%d'),
                                    'transaction_type': transaction_type,
                                    'payment_ref': field[4],
                                    'amount': amount,
                                    # 'currency_id': self.get_currency(field[5])
                                }
                                vals_list.append((0, 0, values))
                        statement_vals = {
                            'journal_id': self.env.context.get('active_id'),
                            'line_ids': vals_list
                        }
                        if len(vals_list) != 0:
                            statement = self.create_statement(statement_vals)

                    if statement:
                        return {
                            'type': 'ir.actions.act_window',
                            'res_model': 'account.bank.statement',
                            'view_mode': 'form',
                            'res_id': statement.id,
                            'views': [(False, 'form')],
                        }

                else:
                    raise ValidationError(_("Unsupported File Type. Current allowed file format is CSV only."))


        elif self.bank_select == 'HSBC':
            for data_file in self.attachment_ids:
                file_name = data_file.name.lower()
                
                if file_name.strip().endswith('.xlsx'):
                    statement = False
                    if file_name.strip().endswith('.xlsx'):
                        keys = ['currency_id', 'date', 'transaction_type', 'payment_ref', 'amount','account_number']
                        try:
                            fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                            fp.write(binascii.a2b_base64(data_file.datas))
                            fp.seek(0)
                            values = {}
                            workbook = xlrd.open_workbook(fp.name)
                            sheet = workbook.sheet_by_index(0)
                        except:
                            raise UserError(_("HCBC Invalid xlsx file!"))
                        
                        vals_list = []
                        line = []
                        for row_no in range(sheet.nrows):
                            val = {}
                            values = {}
                            if row_no <= 0:
                                fields = list(map(lambda row: row.value, sheet.row(row_no)))
                            else:
                                # Convert map to a list
                                line = list(map(
                                    lambda row: isinstance(row.value, bytes) and row.value.decode('utf-8') or str(row.value), sheet.row(row_no)))
                                if vals_list and not line[0]: # When the bank statement ends.
                                    break
                               
                                elif row_no <= 0: # Skip the processing of Bank statements starts for these lines
                                    continue
                                else: # Start the processing from line 1
                                    try:
                                        date_obj = datetime.strptime(line[17], '%d/%m/%Y')
                                    except Exception as e:
                                        raise ValidationError(_(repr(e)))
                                    narration = line[19]
                                
                                    try:
                                        # deposit = float(field[4])
                                        deposit = float(line[20].replace(",", ""))
                                    except ValueError:
                                        deposit = 0.0
                                    try:
                                        # withdraw = float(field[5])
                                        withdraw = float(line[21].replace(",", ""))
                                    except ValueError:
                                        withdraw = 0.0

                                    if deposit > 0.0:
                                        amount = deposit
                                    elif withdraw > 0.0:
                                        amount = withdraw * -1
                                    else:
                                        amount = 0.0
                                    values = {
                                        'date': date_obj.strftime('%Y-%m-%d'),
                                        'narration': narration,
                                        'payment_ref': line[18],
                                        'account_number': line[1],
                                        'ref': line[23],
                                        'transaction_type': line[24],
                                        'amount': amount,
                                        'currency_id': self.get_currency(line[3]),
                                    }
                                   
                                    vals_list.append((0, 0, values))
                        statement_vals = {
                            'journal_id': self.env.context.get('active_id'),
                            'line_ids': vals_list
                        }
                        if len(vals_list) != 0:
                            statement = self.create_statement(statement_vals)

                    if statement:
                        return {
                            'type': 'ir.actions.act_window',
                            'res_model': 'account.bank.statement',
                            'view_mode': 'form',
                            'res_id': statement.id,
                            'views': [(False, 'form')],
                        }

                else:
                    raise ValidationError(_("Unsupported File Type. Current allowed file format is xlsx only."))



        elif self.bank_select == 'MAYBANK':
            for data_file in self.attachment_ids:
                file_name = data_file.name.lower()
                
                if file_name.strip().endswith('.csv'):
                    statement = False
                    if file_name.strip().endswith('.csv'):
                        keys = ['currency_id','date','transaction_type','payment_ref','ref', 'amount']
                        try:
                            csv_data = base64.b64decode(data_file.datas)
                            data_file = io.StringIO(csv_data.decode("utf-8"))
                            data_file.seek(0)
                            file_reader = []
                            values = {}
                            csv_reader = csv.reader(data_file, delimiter=',')
                            file_reader.extend(csv_reader)
                        except:
                            raise UserError(_("MAYBANK Invalid CSV file!"))
                        
                        vals_list = []
                        values = {}
                        currency_id = False
                        for i in range(len(file_reader)):
                            field = list(map(str, file_reader[i]))
                            if vals_list and not field[0]: # When the bank statement ends.
                                break
                            
                            elif i <= 2: # Skip the processing of Bank statements starts for these lines
                                continue

                            else: # Start the processing from line 3
                                try:
                                    date_obj = datetime.strptime(field[0], '%d %b %Y')
                                except Exception as e:
                                    raise ValidationError(_(repr(e)))
                                ref = field[1]
                                # transaction_type = field[15]

                                try:
                                    credit = float(field[3].replace(",", ""))
                                except ValueError:
                                    credit = 0.0

                                try:
                                    debit = float(field[2].replace(",", ""))
                                except ValueError:
                                    debit = 0.0

                                print(credit, " ", debit)

                                if credit > 0.0:
                                    amount = credit
                                elif debit > 0.0:
                                    amount = debit * -1
                                else:
                                    amount = 0.0

                                values = {
                                    'date': date_obj.strftime('%Y-%m-%d'),
                                    # 'transaction_type': transaction_type,
                                    # 'ref': ref,
                                    'payment_ref': field[1],
                                    'amount': amount,
                                    'currency_id':  self.get_currency(field[1])
                                }
                                vals_list.append((0, 0, values))
                        statement_vals = {
                            'journal_id': self.env.context.get('active_id'),
                            'line_ids': vals_list
                        }
                        if len(vals_list) != 0:
                            statement = self.create_statement(statement_vals)


                    if statement:
                        return {
                            'type': 'ir.actions.act_window',
                            'res_model': 'account.bank.statement',
                            'view_mode': 'form',
                            'res_id': statement.id,
                            'views': [(False, 'form')],
                        }

                else:
                    raise ValidationError(_("Unsupported File Type. Current allowed file format is CSV only."))           

                        
        else:
            for data_file in self.attachment_ids:
                file_name = data_file.name.lower()
                if file_name.strip().endswith('.csv') or file_name.strip().endswith('.xlsx'):
                    statement = False
                    if file_name.strip().endswith('.csv'):
                        keys = ['date', 'payment_ref', 'partner_id', 'amount', 'currency_id']
                        try:
                            csv_data = base64.b64decode(data_file.datas)
                            data_file = io.StringIO(csv_data.decode("utf-8"))
                            data_file.seek(0)
                            file_reader = []
                            values = {}
                            csv_reader = csv.reader(data_file, delimiter=',')
                            file_reader.extend(csv_reader)
                        except:
                            raise UserError(_("Invalid file!"))
                        vals_list = []
                        date = False
                        for i in range(len(file_reader)):                        
                            field = list(map(str, file_reader[i]))
                            values = dict(zip(keys, field))
                            if values:
                                if i == 0:
                                    continue
                                else:
                                    if not date:
                                        date = field[0]
                                    values.update({
                                        'date': field[0],
                                        'payment_ref': field[1],
                                        'ref': field[2],
                                        'partner_id': self.get_partner(field[3]),
                                        'amount': field[4],
                                        'currency_id':  self.get_currency(field[5])
                                    })
                                    vals_list.append((0, 0, values))
                        statement_vals = {
                            'name': 'Statement Of ' + str(datetime.today().date()),
                            'journal_id': self.env.context.get('active_id'),
                            'line_ids': vals_list
                        }
                        if len(vals_list) != 0:
                            statement = self.create_statement(statement_vals)
                    elif file_name.strip().endswith('.xlsx'):
                        try:
                            fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                            fp.write(binascii.a2b_base64(data_file.datas))
                            fp.seek(0)
                            values = {}
                            workbook = xlrd.open_workbook(fp.name)
                            sheet = workbook.sheet_by_index(0)
                        except:
                            raise UserError(_("Invalid file!"))
                        vals_list = []
                        for row_no in range(sheet.nrows):
                            val = {}
                            values = {}
                            if row_no <= 0:
                                fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))
                            else:
                                line = list(map(
                                    lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(
                                        row.value), sheet.row(row_no)))
                                print("line ===",line)
                                values.update({
                                    'date': line[0],
                                    'payment_ref': line[1],
                                    'ref': line[2],
                                    'partner_id': self.get_partner(line[3]),
                                    'amount': line[4],
                                    'currency_id': self.get_currency(line[5])
                                })
                                vals_list.append((0, 0, values))
                        statement_vals = {
                            'name': 'Statement Of ' + str(datetime.today().date()),
                            'journal_id': self.env.context.get('active_id'),
                            'line_ids': vals_list
                        }
                        print("statement_vals ===",statement_vals)
                        if len(vals_list) != 0:
                            statement = self.create_statement(statement_vals)
                    if statement:
                        return {
                            'type': 'ir.actions.act_window',
                            'res_model': 'account.bank.statement',
                            'view_mode': 'form',
                            'res_id': statement.id,
                            'views': [(False, 'form')],
                        }
                else:
                    raise ValidationError(_("Unsupported File Type. Allowed file formats are CSV & XLSX only."))

    # def import_file(self):
    #     """ Process the file chosen in the wizard, create bank statement(s) and go to reconciliation. """
    #     self.ensure_one()
    #     statement_line_ids_all = []
    #     notifications_all = []
    #     # Let the appropriate implementation module parse the file and return the required data
    #     # The active_id is passed in context in case an implementation module requires information about the wizard state (see QIF)
    #     for data_file in self.attachment_ids:
    #         currency_code, account_number, stmts_vals = self.with_context(active_id=self.ids[0])._parse_file(base64.b64decode(data_file.datas))
    #         # Check raw data
    #         self._check_parsed_data(stmts_vals, account_number)
    #         # Try to find the currency and journal in odoo
    #         currency, journal = self._find_additional_data(currency_code, account_number)
    #         # If no journal found, ask the user about creating one
    #         if not journal:
    #             # The active_id is passed in context so the wizard can call import_file again once the journal is created
    #             return self.with_context(active_id=self.ids[0])._journal_creation_wizard(currency, account_number)
    #         if not journal.default_debit_account_id or not journal.default_credit_account_id:
    #             raise UserError(_('You have to set a Default Debit Account and a Default Credit Account for the journal: %s') % (journal.name,))
    #         # Prepare statement data to be used for bank statements creation
    #         stmts_vals = self._complete_stmts_vals(stmts_vals, journal, account_number)
    #         # Create the bank statements
    #         statement_line_ids, notifications = self._create_bank_statements(stmts_vals)
    #         statement_line_ids_all.extend(statement_line_ids)
    #         notifications_all.extend(notifications)
    #         # Now that the import worked out, set it as the bank_statements_source of the journal
    #         if journal.bank_statements_source != 'file_import':
    #             # Use sudo() because only 'account.group_account_manager'
    #             # has write access on 'account.journal', but 'account.group_account_user'
    #             # must be able to import bank statement files
    #             journal.sudo().bank_statements_source = 'file_import'
    #     # Finally dispatch to reconciliation interface
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'bank_statement_reconciliation_view',
    #         'context': {'statement_line_ids': statement_line_ids_all,
    #                     'company_ids': self.env.user.company_ids.ids,
    #                     'notifications': notifications_all,
    #         },
    #     }

    def _journal_creation_wizard(self, currency, account_number):
        """ Calls a wizard that allows the user to carry on with journal creation """
        return {
            'name': _('Journal Creation'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.import.journal.creation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'statement_import_transient_id': self.env.context['active_id'],
                'default_bank_acc_number': account_number,
                'default_name': _('Bank') + ' ' + account_number,
                'default_currency_id': currency and currency.id or False,
                'default_type': 'bank',
            }
        }

    def _parse_file(self, data_file):

        raise UserError(_('Could not make sense of the given file.\nDid you install the module to support this type of file ?'))

    def _check_parsed_data(self, stmts_vals, account_number):
        """ Basic and structural verifications """
        extra_msg = _('If it contains transactions for more than one account, it must be imported on each of them.')
        if len(stmts_vals) == 0:
            raise UserError(
                _('This file doesn\'t contain any statement for account %s.') % (account_number,)
                + '\n' + extra_msg
            )

        no_st_line = True
        for vals in stmts_vals:
            if vals['transactions'] and len(vals['transactions']) > 0:
                no_st_line = False
                break
        if no_st_line:
            raise UserError(
                _('This file doesn\'t contain any transaction for account %s.') % (account_number,)
                + '\n' + extra_msg
            )

    def _check_journal_bank_account(self, journal, account_number):
        # Needed for CH to accommodate for non-unique account numbers
        sanitized_acc_number = journal.bank_account_id.sanitized_acc_number
        if " " in sanitized_acc_number:
            sanitized_acc_number = sanitized_acc_number.split(" ")[0]
        return sanitized_acc_number == account_number

    def _find_additional_data(self, currency_code, account_number):
        """ Look for a res.currency and account.journal using values extracted from the
            statement and make sure it's consistent.
        """
        company_currency = self.env.company.currency_id
        journal_obj = self.env['account.journal']
        currency = None
        sanitized_account_number = sanitize_account_number(account_number)

        if currency_code:
            currency = self.env['res.currency'].search([('name', '=ilike', currency_code)], limit=1)
            if not currency:
                raise UserError(_("No currency found matching '%s'.") % currency_code)
            if currency == company_currency:
                currency = False

        journal = journal_obj.browse(self.env.context.get('journal_id', []))
        if account_number:
            # No bank account on the journal : create one from the account number of the statement
            if journal and not journal.bank_account_id:
                journal.set_bank_account(account_number)
            # No journal passed to the wizard : try to find one using the account number of the statement
            elif not journal:
                journal = journal_obj.search([('bank_account_id.sanitized_acc_number', '=', sanitized_account_number)])
            # Already a bank account on the journal : check it's the same as on the statement
            else:
                if not self._check_journal_bank_account(journal, sanitized_account_number):
                    raise UserError(_('The account of this statement (%s) is not the same as the journal (%s).') % (account_number, journal.bank_account_id.acc_number))

        # If importing into an existing journal, its currency must be the same as the bank statement
        if journal:
            journal_currency = journal.currency_id
            if currency is None:
                currency = journal_currency
            if currency and currency != journal_currency:
                statement_cur_code = not currency and company_currency.name or currency.name
                journal_cur_code = not journal_currency and company_currency.name or journal_currency.name
                raise UserError(_('The currency of the bank statement (%s) is not the same as the currency of the journal (%s).') % (statement_cur_code, journal_cur_code))

        # If we couldn't find / can't create a journal, everything is lost
        if not journal and not account_number:
            raise UserError(_('Cannot find in which journal import this statement. Please manually select a journal.'))

        return currency, journal

    def _complete_stmts_vals(self, stmts_vals, journal, account_number):
        for st_vals in stmts_vals:
            st_vals['journal_id'] = journal.id
            if not st_vals.get('reference'):
                st_vals['reference'] = " ".join(self.attachment_ids.mapped('name'))
            if st_vals.get('number'):
                #build the full name like BNK/2016/00135 by just giving the number '135'
                st_vals['name'] = journal.sequence_id.with_context(ir_sequence_date=st_vals.get('date')).get_next_char(st_vals['number'])
                del(st_vals['number'])
            for line_vals in st_vals['transactions']:
                unique_import_id = line_vals.get('unique_import_id')
                if unique_import_id:
                    sanitized_account_number = sanitize_account_number(account_number)
                    line_vals['unique_import_id'] = (sanitized_account_number and sanitized_account_number + '-' or '') + str(journal.id) + '-' + unique_import_id

                if not line_vals.get('bank_account_id'):
                    # Find the partner and his bank account or create the bank account. The partner selected during the
                    # reconciliation process will be linked to the bank when the statement is closed.
                    identifying_string = line_vals.get('account_number')
                    if identifying_string:
                        partner_bank = self.env['res.partner.bank'].search([('acc_number', '=', identifying_string)], limit=1)
                        if partner_bank:
                            line_vals['bank_account_id'] = partner_bank.id
                            line_vals['partner_id'] = partner_bank.partner_id.id
        return stmts_vals

    def _create_bank_statements(self, stmts_vals):
        """ Create new bank statements from imported values, filtering out already imported transactions, and returns data used by the reconciliation widget """
        BankStatement = self.env['account.bank.statement']
        BankStatementLine = self.env['account.bank.statement.line']

        # Filter out already imported transactions and create statements
        statement_line_ids = []
        ignored_statement_lines_import_ids = []
        for st_vals in stmts_vals:
            filtered_st_lines = []
            for line_vals in st_vals['transactions']:
                if 'unique_import_id' not in line_vals \
                   or not line_vals['unique_import_id'] \
                   or not bool(BankStatementLine.sudo().search([('unique_import_id', '=', line_vals['unique_import_id'])], limit=1)):
                    filtered_st_lines.append(line_vals)
                else:
                    ignored_statement_lines_import_ids.append(line_vals['unique_import_id'])
                    if 'balance_start' in st_vals:
                        st_vals['balance_start'] += float(line_vals['amount'])

            if len(filtered_st_lines) > 0:
                # Remove values that won't be used to create records
                st_vals.pop('transactions', None)
                # Create the statement
                st_vals['line_ids'] = [[0, False, line] for line in filtered_st_lines]
                statement_line_ids.extend(BankStatement.create(st_vals).line_ids.ids)
        if len(statement_line_ids) == 0:
            raise UserError(_('You already have imported that file.'))

        # Prepare import feedback
        notifications = []
        num_ignored = len(ignored_statement_lines_import_ids)
        if num_ignored > 0:
            notifications += [{
                'type': 'warning',
                'message': _("%d transactions had already been imported and were ignored.") % num_ignored if num_ignored > 1 else _("1 transaction had already been imported and was ignored."),
                'details': {
                    'name': _('Already imported items'),
                    'model': 'account.bank.statement.line',
                    'ids': BankStatementLine.search([('unique_import_id', 'in', ignored_statement_lines_import_ids)]).ids
                }
            }]
        return statement_line_ids, notifications


class AccountBankStmtImportCSV(models.TransientModel):

    _inherit = 'base_import.import'

    @api.model
    def get_fields(self, model, depth=2):
        fields_list = super(AccountBankStmtImportCSV, self).get_fields(model, depth=depth)
        if self._context.get('bank_stmt_import', False):
            add_fields = [{
                'id': 'balance',
                'name': 'balance',
                'string': 'Cumulative Balance',
                'required': False,
                'fields': [],
                'type': 'monetary',
            }, {
                'id': 'debit',
                'name': 'debit',
                'string': 'Debit',
                'required': False,
                'fields': [],
                'type': 'monetary',
            }, {
                'id': 'credit',
                'name': 'credit',
                'string': 'Credit',
                'required': False,
                'fields': [],
                'type': 'monetary',
            },{
                'id': 'amount',
                'name': 'amount',
                'string': 'Amount',  # <-- User-friendly column label
                'required': False,
                'fields': [],
                'type': 'monetary',
            },{
                'id': 'account_code',
                'name': 'account_code',
                'string': 'Auto Reconcile Account Code',
                'required': False,
                'fields': [],
                'type': 'char',
            },{
                'id': 'tax_name',
                'name': 'tax_name',
                'string': 'Tax Name',
                'required': False,
                'fields': [],
                'type': 'char',
            },]
            fields_list.extend(add_fields)
        return fields_list

    def _convert_to_float(self, value):
        return float(value) if value else 0.0

    def _parse_import_data(self, data, import_fields, options):
        data = super(AccountBankStmtImportCSV, self)._parse_import_data(data, import_fields, options)
        statement_id = self._context.get('bank_statement_id', False)
        if not statement_id:
            return data
        statement = self.env['account.bank.statement'].browse(statement_id)
        currency = statement.currency_id or statement.company_id.currency_id
        currency_name = currency.name if currency else False

        ret_data = []

        vals = {}
        import_fields.append('statement_id/.id')
        import_fields.append('sequence')

        # ✅ Handle 'name' from import
        name_index = False
        if 'name' in import_fields:
            name_index = import_fields.index('name')
            statement_name = data[0][name_index]
            vals['name'] = statement_name
            import_fields.remove('name')  # So it doesn't go into line fields
            for row in data:
                row.pop(name_index)

        index_balance = False
        convert_to_amount = False
        if 'debit' in import_fields and 'credit' in import_fields:
            index_debit = import_fields.index('debit')
            index_credit = import_fields.index('credit')
            self._parse_float_from_data(data, index_debit, 'debit', options)
            self._parse_float_from_data(data, index_credit, 'credit', options)
            import_fields.append('amount')
            convert_to_amount = True
        # add starting balance and ending balance to context
        if 'balance' in import_fields:
            index_balance = import_fields.index('balance')
            self._parse_float_from_data(data, index_balance, 'balance', options)
            vals['balance_start'] = self._convert_to_float(data[0][index_balance])
            vals['balance_start'] -= self._convert_to_float(data[0][import_fields.index('amount')]) \
                                            if not convert_to_amount \
                                            else abs(self._convert_to_float(data[0][index_credit]))-abs(self._convert_to_float(data[0][index_debit]))
            vals['balance_end_real'] = data[len(data)-1][index_balance]
            import_fields.remove('balance')
        # Remove debit/credit field from import_fields
        if convert_to_amount:
            import_fields.remove('debit')
            import_fields.remove('credit')

            
        if 'foreign_currency_id' not in import_fields:
                import_fields.append('foreign_currency_id')
        foreign_currency_id_index = import_fields.index('foreign_currency_id')

        for index, line in enumerate(data):
            line.append(statement_id)
            line.append(index)
            remove_index = []
            if convert_to_amount:
                line.append(
                    abs(self._convert_to_float(line[index_credit]))
                    - abs(self._convert_to_float(line[index_debit]))
                )
                remove_index.extend([index_debit, index_credit])
            if index_balance:
                remove_index.append(index_balance)
            # Remove added field debit/credit/balance
            for i in sorted(remove_index, reverse=True):
                line.pop(i)


            if foreign_currency_id_index >= len(line):
                line.append(currency_name)
            elif not line[foreign_currency_id_index]:
                line[foreign_currency_id_index] = currency_name

            # ➕ Add statement_id and sequence
            line.append(statement_id)
            line.append(index)

            if line[import_fields.index('amount')]:
                ret_data.append(line)
            # Don't set the currency_id on statement line if the currency is the same as the company one.
            
        if 'date' in import_fields:
            vals['date'] = data[len(data)-1][import_fields.index('date')]

        # add starting balance and date if there is one set in fields
        if vals:
            statement.write(vals)
        return ret_data

    
        
    def parse_preview(self, options, count=10):
        record = self[:1]  # Get only one record safely
        if not record:
            return {}  # Or suitable empty response to avoid breaking frontend

        if options.get('bank_stmt_import', False):
            record = record.with_context(bank_stmt_import=True)

        return super(AccountBankStmtImportCSV, record).parse_preview(options, count=count)

    # def parse_preview(self, options, count=10):
    #     if options.get('bank_stmt_import', False):
    #         self = self.with_context(bank_stmt_import=True)
    #     return super(AccountBankStmtImportCSV, self).parse_preview(options, count=count)

    def do(self, fields, columns, options, dryrun=False):
        if options.get('bank_stmt_import', False):
            self._cr.execute('SAVEPOINT import_bank_stmt')
            vals = {
                'journal_id': self._context.get('journal_id', False),
                'reference': self.file_name
            }
            statement = self.env['account.bank.statement'].create(vals)

            res = super(AccountBankStmtImportCSV, self.with_context(bank_statement_id=statement.id)).do(
                fields, columns, options, dryrun=dryrun
            )

            try:
                if dryrun:
                    self._cr.execute('ROLLBACK TO SAVEPOINT import_bank_stmt')
                else:
                    self._cr.execute('RELEASE SAVEPOINT import_bank_stmt')

                    # Add statement_id to result
                    res['statement_id'] = statement.id
                    res['messages'].append({
                        'statement_id': statement.id,
                        'type': 'bank_statement'
                    })

                    lines = self.env['account.bank.statement.line'].search([
                        ('statement_id', '=', statement.id),
                        ('account_code', '!=', False),
                        ('move_id', '!=', False) 
                    ])
                    for line in lines:
                        code = line.account_code
                        if not code:
                            continue

                        account = self.env['account.account'].search([
                            ('code', '=', code),
                            ('company_id', '=', statement.company_id.id),
                        ], limit=1)

                        if not account:
                            raise UserError(f"Account with code '{code}' not found for line {line.name}")

                        journal = statement.journal_id
                        default_account = journal.default_account_id
                        if not default_account:
                            raise UserError(f"Default account not set for journal {journal.name}")

                        amount = line.amount  # total including tax
                        currency = statement.currency_id or statement.company_id.currency_id

                        amount_total = line.amount  # Total including tax
                        tax_ids = []
                        tax_name = line.tax_name
                        currency = statement.currency_id or statement.company_id.currency_id
                        base_amount = amount_total  # Default if no tax
                        tax_amount = 0.0

                        if tax_name:
                            tax = self.env['account.tax'].search([
                                ('name', '=', tax_name),
                                ('company_id', '=', statement.company_id.id)
                            ], limit=1)

                            if not tax:
                                raise UserError(f"Tax '{tax_name}' not found for line {line.name}")

                            if tax.amount_type != 'percent' or not tax.price_include:
                                raise UserError(f"Tax '{tax_name}' must be percentage-based and price-included")

                            tax_ids = [(6, 0, [tax.id])]
                            tax_rate = tax.amount / 100.0
                            base_amount = amount_total / (1 + tax_rate)
                            base_amount = currency.round(base_amount)
                            tax_amount = currency.round(amount_total - base_amount)

                        bank_debit = amount_total if amount_total > 0 else 0.0
                        bank_credit = -amount_total if amount_total < 0 else 0.0
                        acct_debit = 0.0
                        acct_credit = 0.0

                        if amount_total > 0:
                            acct_credit = base_amount
                        else:
                            acct_debit = abs(base_amount)

                        # Set correct debit/credit
                        # if amount >= 0:
                        #     debit = amount
                        #     credit = 0.0
                        # else:
                        #     debit = 0.0
                        #     credit = -amount
                        # Delete old draft move if custom account is provided
                        

                        move_vals = {
                            'journal_id': journal.id,
                            'date': line.date,
                            'ref': line.ref or line.name,
                            'narration': line.narration or line.name,
                            'line_ids': [
                                # Bank or Cash
                                (0, 0, {
                                    'name': line.payment_ref or line.name,
                                    'account_id': default_account.id,
                                    'debit': bank_debit,
                                    'credit': bank_credit,
                                    'partner_id': line.partner_id.id,
                                }),
                                # Receivable/Sales with tax
                                (0, 0, {
                                    'name': line.payment_ref or line.name,
                                    'account_id': account.id,
                                    'debit': acct_debit,
                                    'credit': acct_credit,
                                    'tax_ids': tax_ids,
				                    'is_tax_line': True,
                                    'partner_id': line.partner_id.id,
                                }),
                            ]
                        }

                        if tax_ids:
                            tax_account = tax.invoice_repartition_line_ids.filtered(
                                lambda l: l.repartition_type == 'tax' and l.account_id
                            ).mapped('account_id')
                            
                            if not tax_account:
                                raise UserError("There is no account configured on the tax. Please configure the account.")

                            tax_account = tax_account[0]
                            move_vals['line_ids'].append((0, 0, {
                                'name': f"{tax.name} - Tax",
                                'account_id': tax_account.id,
                                'debit': 0.0,
                                'credit': tax_amount,
                                'partner_id': line.partner_id.id,
                            }))
                            move = self.env['account.move'].create(move_vals)

                        else:
                            move = self.env['account.move'].with_context({'default_move_type':'entry'}).create(move_vals)
                        move.action_post()

                        # Save the original move (possibly auto-created draft)
                        old_move = line.move_id if line.move_id and line.move_id.state == 'draft' else None

                        line.write({'move_id': move.id})
                        
                        if old_move:
                            old_move.unlink()

                        # Reconcile with statement
                        statement_move_lines = line.move_id.line_ids
                        created_move_lines = move.line_ids
                        to_reconcile = statement_move_lines.filtered(lambda l: l.account_id == account) + \
                                    created_move_lines.filtered(lambda l: l.account_id == account)

                        if to_reconcile:
                            to_reconcile.reconcile()
                           


            except psycopg2.InternalError:
                _logger.error("Bank statement import failed: %s", e)

            return res
        else:
            return super(AccountBankStmtImportCSV, self).do(fields, columns, options, dryrun=dryrun)
