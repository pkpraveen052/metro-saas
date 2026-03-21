# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_tax_line = fields.Boolean('Is Tax Line?')

class AccountMove(models.Model):
    _inherit = 'account.move'

    pay_to = fields.Char(string='Pay To')

    @api.model
    def create(self, vals):
        """Inherited the method to explicitly call the _onchange_recompute_dynamic_lines() that 
        performs the auto creation of journal items. 
        Whenever the items are imported through excel this method helps in fixing the tax lines issues. """
        print("\nCUSTOM AccountMove ..... vals ==",vals)
        res = super(AccountMove,self).create(vals)
        ctx = self._context or {}
        if ctx.get('import_file', False) and ctx.get('default_move_type','') == 'entry':
            r = res.read()     
            lis1 = self.env['account.move.line'].browse(r[0]['line_ids']).read()

            res._onchange_recompute_dynamic_lines()

            r = res.read() 
            lis2 = self.env['account.move.line'].browse(r[0]['line_ids']).read()

            filtered_lis = []
            for item in lis2:
                if item.get('tax_ids'):
                    filtered_lis.append(item)

            tax_ids_processed = []
            for dic in filtered_lis:                
                
                if dic['tax_ids'][0] in tax_ids_processed:
                    continue

                dic_obj = self.env['account.move.line'].browse(dic['id'])

                if dic_obj.tax_ids[0].amount == 0.0: # If the tax line from the excel is ZERO Tax, then no need to process.
                    continue

                is_debit = True and dic_obj.debit > 0.0 or False # To know whether it is debit entry or credit entry.

                # To get the auto created tax line item
                filt_lis = [item for item in lis2 if item.get('tax_line_id', False) and item['tax_line_id'][0] == dic['tax_ids'][0]]
                if filt_lis:
                    d_lis2 = filt_lis[0]
                else:
                    raise ValidationError("Something went wrong in finding the automatic created tax line.")

                # Finding the user entered tax line item
                matched_lis1_item = False

                for d in sorted(lis1, key=lambda x: x['is_tax_line']):

                    tax_line_found = False
                    if d['is_tax_line']:
                        if not d['tax_ids'] and ((is_debit and d['debit'] == d_lis2['debit']) or (not is_debit and d['credit'] == d_lis2['credit'])):
                            matched_lis1_item = d
                            break
                    else:
                        if not d['tax_ids'] and ((is_debit and d['debit'] == d_lis2['debit']) or (not is_debit and d['credit'] == d_lis2['credit'])):
                            if not matched_lis1_item:
                                matched_lis1_item = d
                            else:
                                raise ValidationError("The entry '" + str(dic['move_name']) + "' cannot have more than one matched Tax value. Please recheck the data you are importing.")

                if matched_lis1_item:
                    self.env['account.move.line'].browse(matched_lis1_item['id']).unlink()

                    self.env['account.move.line'].browse(d_lis2['id']).write({
                        'name': matched_lis1_item['name'],
                        'account_id': matched_lis1_item['account_id'][0],
                        'account_internal_type': matched_lis1_item['account_internal_type'],
                        'account_internal_group': matched_lis1_item['account_internal_group'],
                        'account_root_id': matched_lis1_item['account_root_id'][0],
                        })

                tax_ids_processed.append(dic['tax_ids'][0])
   
            res._check_balanced()
        return res
