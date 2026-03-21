# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo.tools.float_utils import float_round as round
from odoo.modules.module import get_module_resource
from odoo import api, fields, models, _
from datetime import datetime, time, date, timedelta
from dateutil.relativedelta import relativedelta
from lxml import etree
import base64
import re
from odoo import tools
import calendar
import qrcode
from PIL import Image
from io import BytesIO
import pycrc.algorithms


class Res_Partner(models.Model):
    _inherit = 'res.partner'
    
    def get_cryfwd_customer_initial_balance(self, domain=False):
        self.ensure_one()
        args = [('partner_id','=',self.id),('move_id.initial_carry_fwd_balance','=',True), ('move_id.statement_type','=','customer')]
        if domain:
            args.append(domain)
        move_line_objs = self.env['account.move.line'].sudo().search(args)
        move_objs = move_line_objs.mapped('move_id')
        if move_objs:
            bal = 0.0
            for obj in move_objs:
                bal += obj.amount_total_signed
            return bal
        else:
            return 0.0

    def get_cryfwd_supplier_initial_balance(self, domain=False):
        print("\n\nget_cryfwd_supplier_initial_balance() >>>>>>>>")
        self.ensure_one()
        args = [('partner_id','=',self.id),('move_id.initial_carry_fwd_balance','=',True), ('move_id.statement_type','=','supplier')]
        if domain:
            args.append(domain)
        move_line_objs = self.env['account.move.line'].sudo().search(args)
        move_objs = move_line_objs.mapped('move_id')
        if move_objs:
            bal = 0.0
            for obj in move_objs:
                bal += obj.amount_total_signed
            print("Before returning >>>>> bal==",bal)
            return -1 * bal
        else:
            return 0.0

    def _get_amounts_and_date_amount(self):     
        current_date = datetime.now().date()

        for partner in self:
            amount_due = amount_overdue = 0.0
            
            # Customer Statement
            amount_due += partner.get_cryfwd_customer_initial_balance()
            amount_overdue += partner.get_cryfwd_customer_initial_balance(domain=('date','<=',current_date))

            for aml in partner.balance_invoice_ids:
                if aml.adjust_in_carry_fwd_bal:
                    amount_due -= aml.amount_total
                else:
                    date_maturity = aml.invoice_date_due or aml.date
                    amount_due += aml.result
               
                    if (date_maturity <= current_date):
                        amount_overdue += aml.result
            
            partner.payment_amount_due_amt= amount_due
            partner.payment_amount_overdue_amt =  amount_overdue
            # Ends

            # Supplier Statement
            supplier_amount_due = supplier_amount_overdue = 0.0

            supplier_amount_due += partner.get_cryfwd_supplier_initial_balance()
            supplier_amount_overdue += partner.get_cryfwd_supplier_initial_balance(domain=('date','<=',current_date))

            for aml in partner.supplier_invoice_ids:
                # date_maturity = aml.invoice_date_due or aml.date
                # supplier_amount_due += aml.result
                # if (date_maturity <= current_date):
                #   supplier_amount_overdue += aml.result

                if aml.adjust_in_carry_fwd_bal:
                    supplier_amount_due += aml.amount_total
                else:
                    date_maturity = aml.invoice_date_due or aml.date
                    supplier_amount_due += aml.result
               
                    if (date_maturity <= current_date):
                        supplier_amount_overdue += aml.result

            partner.payment_amount_due_amt_supplier= supplier_amount_due
            partner.payment_amount_overdue_amt_supplier =  supplier_amount_overdue
            # Ends
            
            # Customer Monthly Statement 
            monthly_amount_due_amt = monthly_amount_overdue_amt = 0.0
            for aml in partner.monthly_statement_line_ids:
                date_maturity = aml.invoice_date_due
                monthly_amount_due_amt += aml.result
                if date_maturity and (date_maturity <= current_date):
                    monthly_amount_overdue_amt += aml.result

            partner.monthly_payment_amount_due_amt = monthly_amount_due_amt         
            partner.monthly_payment_amount_overdue_amt = monthly_amount_overdue_amt
            # Ends

    def get_dates(self):
        for record in self:
            today = date.today()
            d = today - relativedelta(months=1)

            start_date = date(d.year, d.month,1)
            end_date = date(today.year, today.month,1) - relativedelta(days=1)

            record.start_date = str(start_date) or False
            record.end_date = str(end_date) or False
            record.year = str(start_date.year) or False

    # Overdue Summary Table on Customer Statement
    @api.depends('balance_invoice_ids')
    def compute_days(self):
        today = fields.date.today()
        for partner in self:
            partner.first_thirty_day = 0
            partner.thirty_sixty_days = 0
            partner.sixty_ninty_days = 0
            partner.ninty_plus_days = 0

            if partner.balance_invoice_ids:
                for line in partner.balance_invoice_ids.filtered(lambda r: not r.adjust_in_carry_fwd_bal):
                    diff = today - line.invoice_date_due
                    result = line.result
                    
                    if diff.days <= 30 and diff.days >= 0:
                        partner.first_thirty_day = partner.first_thirty_day + result
                    elif diff.days > 30 and diff.days<=60:
                        partner.thirty_sixty_days = partner.thirty_sixty_days + result
                    elif diff.days > 60 and diff.days<=90:
                        partner.sixty_ninty_days = partner.sixty_ninty_days + result
                    else:
                        if diff.days > 90:
                            partner.ninty_plus_days = partner.ninty_plus_days + result
        return

    start_date = fields.Date('Start Date', compute='get_dates')
    month_name = fields.Char('Month')
    end_date = fields.Date('End Date', compute='get_dates')
    year = fields.Char(string='Year', compute='get_dates')

    month_start_date = fields.Date('Start Date')
    month_end_date = fields.Date('End Date')

    monthly_statement_line_ids = fields.One2many('monthly.statement.line', 'partner_id', 'Monthly Statement Lines')
    supplier_invoice_ids = fields.One2many('account.move', 'partner_id', 'Customer move lines', 
        domain=['|',('move_type', 'in', ['in_invoice','in_refund']),'&',('adjust_in_carry_fwd_bal','=',True),('payment_id.payment_type','=','outbound'),('state', 'in', ['posted'])])

    balance_invoice_ids = fields.One2many('account.move', 'partner_id', 'Customer move lines', 
        domain=['|',('move_type', 'in', ['out_invoice','out_refund']),'&',('adjust_in_carry_fwd_bal','=',True),('payment_id.payment_type','=','inbound'),('state', 'in', ['posted'])])
    
    payment_amount_due_amt=fields.Float(compute = '_get_amounts_and_date_amount', string="Balance Due")
    payment_amount_overdue_amt = fields.Float(compute='_get_amounts_and_date_amount',
                                                  string="Total Overdue Amount"  )
    payment_amount_due_amt_supplier=fields.Float(compute = '_get_amounts_and_date_amount', string="Supplier Balance Due")
    payment_amount_overdue_amt_supplier = fields.Float(compute='_get_amounts_and_date_amount',
                                                  string="Total Supplier Overdue Amount"  )
    
    monthly_payment_amount_due_amt = fields.Float(compute='_get_amounts_and_date_amount', string="Balance Due")
    monthly_payment_amount_overdue_amt = fields.Float(compute='_get_amounts_and_date_amount',
                                                  string="Total Overdue Amount")                                                  
    current_date = fields.Date(default=fields.date.today())

    first_thirty_day = fields.Float(string="0-30",compute="compute_days")
    thirty_sixty_days = fields.Float(string="30-60",compute="compute_days")
    sixty_ninty_days = fields.Float(string="60-90",compute="compute_days")
    ninty_plus_days = fields.Float(string="90+",compute="compute_days")
    total = fields.Float(string="Total",compute="compute_total")

    month_end_balance = fields.Float(string="Month End Balance (Technical Field)")

    def compute_ending_balance_asof(self, month_end=False):
        print("\ncompute_ending_balance_asof() >>>>")
        self.ensure_one()
        if not month_end:
            month_end = self.month_start_date
        amount = 0.0

        move_line_objs = self.env['account.move.line'].sudo().search(
            [('partner_id','=',self.id), ('move_id.initial_carry_fwd_balance','=',True), ('move_id.statement_type','=','customer')], limit=1)
        move_obj = move_line_objs.mapped('move_id')
        amount = move_obj.amount_total

        processed_moves = []
        for obj in self.env['account.payment'].search([('adjust_in_carry_fwd_bal','=',True),('payment_type','=','inbound'),('partner_id','=',self.id),
            ('state','=','posted'),('offset_carry_fwd_bal_date','<',str(month_end))]):
            amount -= obj.amount_total
            processed_moves.append(obj.move_id.id)
        
        for obj in self.env['account.move'].search([('partner_id','=',self.id),('state','!=','cancel'),('date','<',str(month_end))]):
            print(obj, obj.name, obj.move_type, obj.amount_total, obj.state)
            if obj.id in processed_moves:
                continue
            if obj.state == 'posted':
                if obj.move_type == 'out_invoice':
                    amount += obj.amount_total
                elif obj.move_type == 'out_refund':
                    amount -= obj.amount_total
                elif obj.payment_id and obj.payment_id.payment_type == 'inbound':
                    amount -= obj.amount_total
        self.month_end_balance = amount
        return amount

    def generate_monthly_statement_lines(self):
        print("\ngenerate_monthly_statement_lines() >>>>>>")
        print("self.month_end_balance ==",self.month_end_balance)
        self.ensure_one()
        line_dic = []

        balance = self.month_end_balance # Ending Balance of the last month
        print("STARTING BALANCE ==", balance)

        move_ids1 = self.env['account.move'].search([('adjust_in_carry_fwd_bal','=',True),
                                    ('partner_id','=',self.id),
                                    ('payment_id.payment_type','=','inbound'),
                                    ('state','=','posted'),
                                    ('payment_id.offset_carry_fwd_bal_date','>=',str(self.month_start_date)),
                                    ('payment_id.offset_carry_fwd_bal_date','<=',str(self.month_end_date))]).ids
        print("move_ids1 ==",move_ids1)

        move_ids2 = self.env['account.move'].search([('adjust_in_carry_fwd_bal','=',False),
                                    ('partner_id','=',self.id),
                                    ('state','!=','cancel'),
                                    ('date','>=',str(self.month_start_date)),
                                    ('date','<=',str(self.month_end_date)),
                                    ('state', 'in', ['posted'])], order='date, name').ids
        print("move_ids2 ==",move_ids2)
        move_objs = self.env['account.move'].browse(move_ids1 + move_ids2)
        print("Before sorting (move_objs1 + move_objs1) ==",move_objs)
        move_objs.sorted(lambda m: (m.date, m.name))
        print("After sorting ===",move_objs.sorted(lambda m: (m.invoice_date, m.name)))

        for obj in move_objs.sorted(lambda m: (m.invoice_date, m.name)):
            if obj.adjust_in_carry_fwd_bal:
                balance -= obj.amount_total
                name = obj.name
                if obj.ref:
                    name += " - " + obj.ref
                dic = {
                    'date': obj.payment_id.offset_carry_fwd_bal_date, 
                    'name': name, 
                    'ref': obj.payment_id.ref, 
                    'invoice_amt': 0.0, 
                    'payment': obj.amount_total, 
                    'balance': balance,
                    'priority': 1}
                line_dic.append(dic)
            else:
                name = obj.name
                if obj.ref:
                    name += " - " + obj.ref
                dic = {'date': obj.date, 'name': name, 'ref': obj.ref, 'invoice_amt': 0.0, 'payment': 0.0, 'balance': 0.0}
                print("name =",obj.name)
                print(obj.move_type, obj.payment_id, obj.payment_id.payment_type)
                if obj.move_type == 'out_invoice':
                    dic['invoice_amt'] = obj.amount_total
                    dic['priority'] = 0
                elif obj.move_type == 'out_refund':
                    dic['payment'] = obj.amount_total
                    dic['priority'] = 1
                elif obj.payment_id and obj.payment_id.payment_type == 'inbound':
                    dic['payment'] = obj.amount_total
                    dic['priority'] = 1
                else:
                    continue

                if dic['invoice_amt'] != 0.0:
                    balance += dic['invoice_amt']
                elif dic['payment'] != 0.0:
                    balance -= dic['payment']
                    if balance == -0.0:
                        balance = 0.0
                dic['balance'] = balance
                line_dic.append(dic)
                print(dic)

        print("\nFINALLLY line_dic ===",line_dic)
        return line_dic

    def get_month_labels(self):
        print("\nget_month_labels() >>>>>")
        self.ensure_one()

        def get_month_label(given_date):
            return calendar.month_abbr[given_date.month].upper() + " " + str(given_date.year)[-2:]

        month_start = self.month_start_date
        print("month_start =",month_start)

        first_day_current_month = month_start.replace(day=1)        
        first_day_previous_month = (first_day_current_month - timedelta(days=1)).replace(day=1)     
        first_day_previous_two_months = (first_day_previous_month - timedelta(days=1)).replace(day=1)
        first_day_previous_three_months = (first_day_previous_two_months - timedelta(days=1)).replace(day=1)

        print(first_day_current_month, first_day_previous_month, first_day_previous_two_months, first_day_previous_three_months)

        print(get_month_label(first_day_current_month), get_month_label(first_day_current_month), get_month_label(first_day_previous_month), get_month_label(first_day_previous_two_months), get_month_label(first_day_previous_three_months))
        return [get_month_label(first_day_current_month), get_month_label(first_day_previous_month), get_month_label(first_day_previous_two_months), get_month_label(first_day_previous_three_months)]

    def get_balance_of_month(self, start_date_month, last_month=False):
        print("\nget_balance_of_month() >>>> start_date_month =")
        amount = 0.0
        invoice_ids = []

        year = start_date_month.year
        month = start_date_month.month
        end_date_month = start_date_month.replace(day=calendar.monthrange(year, month)[1])

        print("start_date_month ==",start_date_month)
        print("end_date_month ==",end_date_month)

        if last_month:
            start_date_month = '1900-01-01'

        print("0...........")

        carryfwd_move_obj = self.env['account.move.line'].sudo().search([
                                                                ('partner_id','=',self.id), 
                                                                ('move_id.initial_carry_fwd_balance','=',True), 
                                                                ('move_id.statement_type','=','customer')], limit=1).mapped('move_id')
        if carryfwd_move_obj:
            if self.company_id.inital_carry_fwd_balance_plus_oneday:
                move_date = carryfwd_move_obj.date + relativedelta(days=1)
            else:
                move_date = carryfwd_move_obj.date
            if str(move_date) >= str(start_date_month) and str(move_date) <= str(end_date_month):
                amount += carryfwd_move_obj.amount_total
        print("amount =",amount)

        print("1.........")
        for pobj in self.env['account.payment'].search([
                                                ('partner_id','=',self.id),
                                                ('state','=','posted'),
                                                # ('offset_carry_fwd_bal_date','>=',str(start_date_month)),
                                                # ('offset_carry_fwd_bal_date','<=',str(end_date_month)),
                                                ('offset_carry_fwd_bal_date','<=',str(self.month_end_date)),
                                                ('adjust_in_carry_fwd_bal','=',True),('payment_type','=','inbound')]):
            if amount > 0.0:
                amount -= pobj.amount
                print("amount =",amount)

        print("2........")
        for obj in self.env['account.move'].search([
                                            ('partner_id','=',self.id),
                                            ('state','=','posted'),
                                            ('move_type','in',['out_invoice','out_refund']),
                                            ('date','>=',str(start_date_month)),
                                            ('date','<=',str(end_date_month))]):
            print("obj ==",obj,obj.name,obj.move_type)
            if obj.move_type == 'out_invoice':
                amount += obj.amount_total
                invoice_ids.append(obj.id)
            elif obj.move_type == 'out_refund':
                amount -= obj.amount_total
            print(amount)
            invoice_ids.append(obj.id)

        print("3.............")
        for obj in self.env['account.move'].search([
                                            ('partner_id','=',self.id),
                                            ('state','=','posted'),
                                            ('payment_id.payment_type','=','inbound'),
                                            ('date','<=',str(self.month_end_date))]):
            print("obj ==",obj,obj.name,obj.payment_id.reconciled_invoice_ids)
            if obj.payment_id.reconciled_invoice_ids and obj.payment_id.reconciled_invoice_ids[0].id in invoice_ids:
                amount -= obj.amount_total
                print(amount)

        if amount < 0.0:
            amount = 0.0
        return amount

    # Balance summry Table  - On Monthly Statement
    def compute_monthwise_monthly_statement_summary(self):
        print("\ncompute_monthwise_monthly_statement_summary() >>>>>>")
        self.ensure_one()
        current_month = 0.0
        current_month_minus_one = 0.0
        current_month_minus_two = 0.0
        current_month_minus_three_beyond = 0.0

        month_start = self.month_start_date
        print("month_start =",month_start)

        first_day_current_month = month_start.replace(day=1)        
        first_day_previous_month = (first_day_current_month - timedelta(days=1)).replace(day=1)     
        first_day_month_before_previous = (first_day_previous_month - timedelta(days=1)).replace(day=1)
        last_month_beyond = (first_day_month_before_previous - timedelta(days=1)).replace(day=1)
        print(first_day_current_month, first_day_previous_month, first_day_month_before_previous, last_month_beyond)

        current_month = self.get_balance_of_month(first_day_current_month)
        current_month_minus_one = self.get_balance_of_month(first_day_previous_month)
        current_month_minus_two = self.get_balance_of_month(first_day_month_before_previous)
        current_month_minus_three_beyond = self.get_balance_of_month(last_month_beyond, True)

        print(" FINALLY ===",current_month, current_month_minus_one, current_month_minus_two, current_month_minus_three_beyond, current_month + current_month_minus_one + current_month_minus_two + current_month_minus_three_beyond)
        return [current_month, current_month_minus_one, current_month_minus_two, current_month_minus_three_beyond, current_month + current_month_minus_one + current_month_minus_two + current_month_minus_three_beyond]

    # Invoice Summary Table - On Monthly Statement
    def compute_days_wise_invamt(self):
        self.ensure_one()
        month_end = self.month_end_date
        first_thirty_day = 0
        thirty_sixty_days = 0
        sixty_ninty_days = 0
        ninty_plus_days = 0
        if self.balance_invoice_ids:
            for line in self.balance_invoice_ids.filtered(lambda r: not r.adjust_in_carry_fwd_bal):
                diff = month_end - line.invoice_date
                if diff.days <= 30 and diff.days >= 0:
                    first_thirty_day = first_thirty_day + line.amount_total_signed
                elif diff.days > 30 and diff.days<=60:
                    thirty_sixty_days = thirty_sixty_days + line.amount_total_signed
                elif diff.days > 60 and diff.days<=90:
                    sixty_ninty_days = sixty_ninty_days + line.amount_total_signed
                else:
                    if diff.days > 90:
                        ninty_plus_days = ninty_plus_days + line.amount_total_signed
            return [first_thirty_day, thirty_sixty_days, sixty_ninty_days, ninty_plus_days, first_thirty_day + thirty_sixty_days + sixty_ninty_days + ninty_plus_days]
        return [0.00, 0.00, 0.00, 0.00, 0.00]

    # Balance summry Table  - On Supplier Statement
    def compute_dayswise_supplier_balance_summary(self):
        print("\ncompute_dayswise_supplier_balance_summary() >>>>>>")
        self.ensure_one()
        first_thirty_day = 0
        thirty_sixty_days = 0
        sixty_ninty_days = 0
        ninty_plus_days = 0
        
        current_date = datetime.now()
        last_day = calendar.monthrange(current_date.year, current_date.month)[1]        
        month_end = current_date.replace(day=last_day).date()
        print("month_end ===",month_end)

        move_line_objs = self.env['account.move.line'].sudo().search(
            [('partner_id','=',self.id), ('move_id.initial_carry_fwd_balance','=',True), ('move_id.statement_type','=','supplier')])
        move_objs = move_line_objs.mapped('move_id')
        print("move_objs ===",move_objs)

        if self.supplier_invoice_ids:
            for line in (self.supplier_invoice_ids + move_objs).sorted(key=lambda r: r.invoice_date):
                print("\nline ==",line,"Name: ",line.name)
                if line.initial_carry_fwd_balance:
                    print("Is a INITIAL MOVE LINE = line.invoice_date:", line.invoice_date)
                    invoice_date = line.invoice_date + relativedelta(days=1)
                    print("Converted to invoice_date:",invoice_date)
                else:
                    invoice_date = line.invoice_date

                if line.move_type in ['in_invoice','in_refund']:
                    print("Is a Invoice / Credit notes:",line.move_type)
                    amount = line.result

                elif line.adjust_in_carry_fwd_bal:
                    amount = 1 * line.amount_total
                    
                elif line.initial_carry_fwd_balance:
                    amount = -1 * line.amount_total_signed

                diff = month_end - invoice_date

                if diff.days <= 30 and diff.days >= 0:
                    first_thirty_day += amount
                elif diff.days > 30 and diff.days<=60:
                    thirty_sixty_days += amount
                elif diff.days > 60 and diff.days<=90:
                    sixty_ninty_days += amount
                else:
                    if diff.days > 90:
                        ninty_plus_days += amount

                print(first_thirty_day, thirty_sixty_days, sixty_ninty_days, ninty_plus_days)
            return [first_thirty_day, thirty_sixty_days, sixty_ninty_days, ninty_plus_days, first_thirty_day + thirty_sixty_days + sixty_ninty_days + ninty_plus_days, month_end]
        return [0.00, 0.00, 0.00, 0.00, 0.00, month_end]

    # Balance summry Table  - On Customer Statement
    def compute_dayswise_customer_balance_summary(self):
        print("\ncompute_dayswise_customer_balance_summary() >>>>>>")
        self.ensure_one()
        first_thirty_day = 0
        thirty_sixty_days = 0
        sixty_ninty_days = 0
        ninty_plus_days = 0
        
        current_date = datetime.now()
        last_day = calendar.monthrange(current_date.year, current_date.month)[1]        
        month_end = current_date.replace(day=last_day).date()
        print("month_end ===",month_end)

        move_line_objs = self.env['account.move.line'].sudo().search([('partner_id','=',self.id),('move_id.initial_carry_fwd_balance','=',True), ('move_id.statement_type','=','customer')])
        move_objs = move_line_objs.mapped('move_id')
        print("move_objs ===",move_objs)

        if self.balance_invoice_ids:
            for line in (self.balance_invoice_ids + move_objs).sorted(key=lambda r: r.invoice_date):
                print("\nline ==",line,"Name: ",line.name)
                if line.initial_carry_fwd_balance:
                    print("Is a INITIAL MOVE LINE = line.invoice_date:", line.invoice_date)
                    invoice_date = line.invoice_date + relativedelta(days=1)
                    print("Converted to invoice_date:",invoice_date)
                else:
                    invoice_date = line.invoice_date

                if line.move_type in ['out_invoice','out_refund']:
                    print("Is a Invoice / Credit notes:",line.move_type)
                    amount = line.result
                elif line.adjust_in_carry_fwd_bal:
                    amount = -1 * line.amount_total
                elif line.initial_carry_fwd_balance:
                    amount = line.amount_total_signed

                diff = month_end - invoice_date

                if diff.days <= 30 and diff.days >= 0:
                    first_thirty_day += amount
                elif diff.days > 30 and diff.days<=60:
                    thirty_sixty_days += amount
                elif diff.days > 60 and diff.days<=90:
                    sixty_ninty_days += amount
                else:
                    if diff.days > 90:
                        ninty_plus_days += amount

                print(first_thirty_day, thirty_sixty_days, sixty_ninty_days, ninty_plus_days)
            return [first_thirty_day, thirty_sixty_days, sixty_ninty_days, ninty_plus_days, first_thirty_day + thirty_sixty_days + sixty_ninty_days + ninty_plus_days, month_end]
        return [0.00, 0.00, 0.00, 0.00, 0.00, month_end]



    # Temporarily Commented
    # def compute_overdue_days_amt(self):
    #   self.ensure_one()
    #   month_end = self.month_end_date
    #   first_thirty_day = 0
    #   thirty_sixty_days = 0
    #   sixty_ninty_days = 0
    #   ninty_plus_days = 0
    #   if self.balance_invoice_ids:
    #       for line in self.balance_invoice_ids.filtered(lambda r: not r.adjust_in_carry_fwd_bal):
    #           print("line....",line.name)
    #           diff = month_end - line.invoice_date_due
    #           print("diff.....",diff)
    #           if diff.days <= 30 and diff.days >= 0:
    #               first_thirty_day = first_thirty_day + line.result
    #           elif diff.days > 30 and diff.days<=60:
    #               thirty_sixty_days = thirty_sixty_days + line.result
    #           elif diff.days > 60 and diff.days<=90:
    #               sixty_ninty_days = sixty_ninty_days + line.result
    #           else:
    #               if diff.days > 90:
    #                   ninty_plus_days = ninty_plus_days + line.result
    #       return [first_thirty_day, thirty_sixty_days, sixty_ninty_days, ninty_plus_days, first_thirty_day + thirty_sixty_days + sixty_ninty_days + ninty_plus_days]
        # return [0.00, 0.00, 0.00, 0.00, 0.00]

    @api.depends('ninty_plus_days','sixty_ninty_days','thirty_sixty_days','first_thirty_day')
    def compute_total(self):
        for partner in self:
            partner.total = 0.0
            partner.total = partner.ninty_plus_days + partner.sixty_ninty_days + partner.thirty_sixty_days + partner.first_thirty_day
        return  

    def _cron_send_customer_statement(self):
        partners = self.env['res.partner'].search([])
        # partner_search_mode = self.env.context.get('res_partner_search_mode')
        # if partner_search_mode == 'customer':
        if self.env.user.company_id.period == 'monthly':
            partners.do_process_monthly_statement_filter()
            partners.customer_monthly_send_mail()
        else:
            partners.customer_send_mail()
        return True

    def customer_monthly_send_mail(self):
        unknown_mails = 0
        for partner in self:
            partners_to_email = [child for child in partner.child_ids if child.type == 'invoice' and child.email]
            if not partners_to_email and partner.email:
                partners_to_email = [partner]
            if partners_to_email:
                for partner_to_email in partners_to_email:
                    mail_template_id = self.env['ir.model.data'].xmlid_to_object('account_statement.email_template_customer_monthly_statement')
                    if mail_template_id:
                        mail_template_id.send_mail(partner_to_email.id)
                if partner not in partner_to_email:
                    self.message_post([partner.id], body=_('Customer Monthly Statement email sent to %s' % ', '.join(['%s <%s>' % (partner.name, partner.email) for partner in partners_to_email])))
        return unknown_mails

    def do_process_monthly_statement_filter(self):
        account_invoice_obj = self.env['account.move']
        account_payment_obj = self.env['account.payment']
        statement_line_obj = self.env['monthly.statement.line']
        # for record in self:
        #   today = date.today()
        #   d = today - relativedelta(months=1)
        #
        #   start_date = date(d.year, d.month,1)
        #   end_date = date(today.year, today.month,1) - relativedelta(days=1)
        #
        #   from_date = str(start_date)
        #   to_date = str(end_date)
        #
        #   domain = [('move_type', 'in', ['out_invoice','out_refund']), ('state', 'in', ['posted']), ('partner_id', '=', record.id)]
        #   if record.month_start_date:
        #       print('\n\n\n\n\n\n\nrecord.month_start_date', record.month_start_date)
        #       domain.append(('invoice_date', '>=', record.month_start_date))
        #   if record.month_end_date:
        #       domain.append(('invoice_date', '<=', record.month_end_date))
        #   lines_to_be_delete = statement_line_obj.search([('partner_id', '=', record.id)])
        #   lines_to_be_delete.unlink()
        #   invoices = account_invoice_obj.search(domain)
        #   print('\n\n\n\n\n\n\ninvoicesinvoices', invoices)
        #   for invoice in invoices.sorted(key=lambda r: r.name):
        #       vals = {
        #               'partner_id':invoice.partner_id.id or False,
        #               'state':invoice.state or False,
        #               'invoice_date':invoice.invoice_date,
        #               'invoice_date_due':invoice.invoice_date_due,
        #               'result':invoice.result or 0.0,
        #               'name':invoice.name or '',
        #               'amount_total':invoice.amount_total or 0.0,
        #               'credit_amount':invoice.credit_amount or 0.0,
        #               'invoice_id' : invoice.id,
        #           }
        #       ob = statement_line_obj.create(vals)
        #       print('\n\n\n\n\n\n\nobobobobobob', ob)

            
        """ #AGREGO TODOS LOS PAGOS DEL CLIENTE
        domain = [('partner_id', '=', record.id),('state', '=', 'posted'),('payment_type', '=', 'inbound')]
        if from_date:
            domain.append(('payment_date', '>=', from_date))
        if to_date:
            domain.append(('payment_date', '<=', to_date))
        payment = account_payment_obj.search(domain)
        for pay in payment.sorted(key=lambda r: r.name):
            vals = {
                    'partner_id':pay.partner_id.id or False,
                    'state':pay.state or False,
                    'invoice_date':pay.payment_date,
                    'invoice_date_due': False,
                    'result': False,
                    'name':pay.name or '',
                    'amount_total':False,
                    'credit_amount':pay.amount or 0.0,
                    #'invoice_id' : pay.id,
                }
            ob = statement_line_obj.create(vals)  """

    def button_print_monthly_statement(self):
        context = self.env.context.copy() or {}
        today = date.today()
        d = today - relativedelta(months=1)

        start_date = date(d.year, d.month, 1)
        end_date = date(today.year, today.month, 1) - relativedelta(days=1)

        from_date = str(start_date)
        to_date = str(end_date)
        context.update({
            'default_date_from': from_date,
            'default_date_to': to_date,
            'default_partner_id': self.id,
        })
        view = self.env.ref('account_statement.view_customer_monthly_statement_wizard')
        return {
            'name': _('Customer Monthly Filter'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'customer.monthly.statement.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    def button_print_monthly_statement_supplier(self):
        context = self.env.context.copy() or {}
        today = date.today()
        d = today - relativedelta(months=1)

        start_date = date(d.year, d.month, 1)
        end_date = date(today.year, today.month, 1) - relativedelta(days=1)

        from_date = str(start_date)
        to_date = str(end_date)
        context.update({
            'default_date_from': from_date,
            'default_date_to': to_date,
            'default_partner_id': self.id,
        })
        view = self.env.ref('account_statement.view_supplier_monthly_statement_wizard')
        return {
            'name': _('Supplier Monthly Filter'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'supplier.monthly.statement.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    def print_partner_activity_statement(self):
        ctx = self.env.context.copy()
        ctx.update({'default_account_type': 'receivable'})
        action = self.env["ir.actions.actions"]._for_xml_id("partner_statement.activity_statement_wizard_action")
        action['context'] = ctx
        return action

    def print_partner_outstanding_statement(self):
        ctx = self.env.context.copy()
        ctx.update({'default_account_type': 'receivable'})
        action = self.env["ir.actions.actions"]._for_xml_id("partner_statement.outstanding_statement_wizard_action")
        action['context'] = ctx
        return action

    def print_partner_activity_supplier_statement(self):
        ctx = self.env.context.copy()
        ctx.update({'default_account_type': 'payable'})
        action = self.env["ir.actions.actions"]._for_xml_id("partner_statement.activity_statement_wizard_action")
        action['context'] = ctx
        return action

    def print_partner_outstanding_supplier_statement(self):
        ctx = self.env.context.copy()
        ctx.update({'default_account_type': 'payable'})
        action = self.env["ir.actions.actions"]._for_xml_id("partner_statement.outstanding_statement_wizard_action")
        action['context'] = ctx
        return action


    def customer_send_mail(self):
        unknown_mails = 0
        for partner in self:
            partners_to_email = [child for child in partner.child_ids if child.type == 'invoice' and child.email]
            if not partners_to_email and partner.email:
                partners_to_email = [partner]
            if partners_to_email:
                for partner_to_email in partners_to_email:
                    mail_template_id = self.env['ir.model.data'].xmlid_to_object('account_statement.email_template_customer_statement')
                    mail_template_id.send_mail(partner_to_email.id)
                if partner not in partner_to_email:
                    self.message_post([partner.id], body=_('Customer Statement email sent to %s' % ', '.join(['%s <%s>' % (partner.name, partner.email) for partner in partners_to_email])))
        return unknown_mails
    
    def supplier_send_mail(self):
        unknown_mails = 0
        for partner in self:
            partners_to_email = [child for child in partner.child_ids if child.type == 'invoice' and child.email]
            if not partners_to_email and partner.email:
                partners_to_email = [partner]
            if partners_to_email:
                for partner_to_email in partners_to_email:
                    mail_template_id = self.env['ir.model.data'].xmlid_to_object('account_statement.email_template_supplier_statement')
                    mail_template_id.send_mail(partner_to_email.id)
                #if partner not in partner_to_email:
                    #self.message_post([partner.id], body=_('Customer Statement email sent to %s' % ', '.join(['%s <%s>' % (partner.name, partner.email) for partner in partners_to_email])))
        return unknown_mails
    

    def do_button_print_statement(self):
        return self.env.ref('account_statement.report_customert_print').report_action(self)
        
    def do_button_print_statement_vendor(self) : 
        return self.env.ref('account_statement.report_supplier_print').report_action(self)

    def compute_ending_balance_asof_supplier(self, month_end=False):
        print("\ncompute_ending_balance_asof_supplier() >>>>")
        self.ensure_one()
        if not month_end:
            month_end = self.month_start_date
        amount = 0.0

        move_line_objs = self.env['account.move.line'].sudo().search(
            [('partner_id', '=', self.id), ('move_id.initial_carry_fwd_balance', '=', True),
             ('move_id.statement_type', '=', 'supplier')], limit=1)
        move_obj = move_line_objs.mapped('move_id')
        amount = move_obj.amount_total

        processed_moves = []
        for obj in self.env['account.payment'].search(
                [('adjust_in_carry_fwd_bal', '=', True), ('payment_type', '=', 'outbound'), ('partner_id', '=', self.id),
                 ('state', '=', 'posted'), ('offset_carry_fwd_bal_date', '<', str(month_end))]):
            amount -= obj.amount_total
            processed_moves.append(obj.move_id.id)

        for obj in self.env['account.move'].search(
                [('partner_id', '=', self.id), ('state', '!=', 'cancel'), ('date', '<', str(month_end))]):
            print(obj, obj.name, obj.move_type, obj.amount_total, obj.state)
            if obj.id in processed_moves:
                continue
            if obj.state == 'posted':
                if obj.move_type == 'in_invoice':
                    amount += obj.amount_total
                elif obj.move_type == 'in_refund':
                    amount -= obj.amount_total
                elif obj.payment_id and obj.payment_id.payment_type == 'outbound':
                    amount -= obj.amount_total
        self.month_end_balance = amount
        return amount

    def generate_monthly_supplier_statement_lines(self):
        print("\ngenerate_monthly_supplier_statement_lines() >>>>>>")
        print("self.month_end_balance ==",self.month_end_balance)
        self.ensure_one()
        line_dic = []

        balance = self.month_end_balance # Ending Balance of the last month
        print("STARTING BALANCE ==", balance)

        move_ids1 = self.env['account.move'].search([('adjust_in_carry_fwd_bal','=',True),
                                    ('partner_id','=',self.id),
                                    ('payment_id.payment_type','=','outbound'),
                                    ('state','=','posted'),
                                    ('payment_id.offset_carry_fwd_bal_date','>=',str(self.month_start_date)),
                                    ('payment_id.offset_carry_fwd_bal_date','<=',str(self.month_end_date))]).ids
        print("move_ids1 ==",move_ids1)

        move_ids2 = self.env['account.move'].search([('adjust_in_carry_fwd_bal','=',False),
                                    ('partner_id','=',self.id),
                                    ('state','!=','cancel'),
                                    ('date','>=',str(self.month_start_date)),
                                    ('date','<=',str(self.month_end_date)),
                                    ('state', 'in', ['posted'])], order='date, name').ids
        print("move_ids2 ==",move_ids2)
        move_objs = self.env['account.move'].browse(move_ids1 + move_ids2)
        print("Before sorting (move_objs1 + move_objs1) ==",move_objs)
        move_objs.sorted(lambda m: (m.date, m.name))
        print("After sorting ===",move_objs.sorted(lambda m: (m.invoice_date, m.name)))

        for obj in move_objs.sorted(lambda m: (m.invoice_date, m.name)):
            if obj.adjust_in_carry_fwd_bal:
                balance -= obj.amount_total
                name = obj.name
                if obj.ref:
                    name += " - " + obj.ref
                dic = {
                    'date': obj.payment_id.offset_carry_fwd_bal_date,
                    'name': name,
                    'ref': obj.payment_id.ref,
                    'invoice_amt': 0.0,
                    'payment': obj.amount_total,
                    'balance': balance,
                    'priority': 1}
                line_dic.append(dic)
            else:
                name = obj.name
                if obj.ref:
                    name += " - " + obj.ref
                dic = {'date': obj.date, 'name': name, 'ref': obj.ref, 'invoice_amt': 0.0, 'payment': 0.0, 'balance': 0.0}
                print("name =",obj.name)
                print(obj.move_type, obj.payment_id, obj.payment_id.payment_type)
                if obj.move_type == 'in_invoice':
                    dic['invoice_amt'] = obj.amount_total
                    dic['priority'] = 0
                elif obj.move_type == 'in_refund':
                    dic['payment'] = obj.amount_total
                    dic['priority'] = 1
                elif obj.payment_id and obj.payment_id.payment_type == 'outbound':
                    dic['payment'] = obj.amount_total
                    dic['priority'] = 1
                else:
                    continue

                if dic['invoice_amt'] != 0.0:
                    balance += dic['invoice_amt']
                elif dic['payment'] != 0.0:
                    balance -= dic['payment']
                    if balance == -0.0:
                        balance = 0.0
                dic['balance'] = balance
                line_dic.append(dic)
                print(dic)

        print("\nFINALLLY line_dic ===",line_dic)
        return line_dic

    def get_balance_of_month_supplier(self, start_date_month, last_month=False):
        print("\nget_balance_of_month_supplier() >>>> start_date_month =")
        amount = 0.0
        invoice_ids = []

        year = start_date_month.year
        month = start_date_month.month
        end_date_month = start_date_month.replace(day=calendar.monthrange(year, month)[1])

        print("start_date_month ==",start_date_month)
        print("end_date_month ==",end_date_month)

        if last_month:
            start_date_month = '1900-01-01'

        print("0...........")

        carryfwd_move_obj = self.env['account.move.line'].sudo().search([
                                                                ('partner_id','=',self.id),
                                                                ('move_id.initial_carry_fwd_balance','=',True),
                                                                ('move_id.statement_type','=','supplier')], limit=1).mapped('move_id')
        if carryfwd_move_obj:
            if self.company_id.inital_carry_fwd_balance_plus_oneday:
                move_date = carryfwd_move_obj.date + relativedelta(days=1)
            else:
                move_date = carryfwd_move_obj.date
            if str(move_date) >= str(start_date_month) and str(move_date) <= str(end_date_month):
                amount += carryfwd_move_obj.amount_total
        print("amount =",amount)

        print("1.........")
        for pobj in self.env['account.payment'].search([
                                                ('partner_id','=',self.id),
                                                ('state','=','posted'),
                                                # ('offset_carry_fwd_bal_date','>=',str(start_date_month)),
                                                # ('offset_carry_fwd_bal_date','<=',str(end_date_month)),
                                                ('offset_carry_fwd_bal_date','<=',str(self.month_end_date)),
                                                ('adjust_in_carry_fwd_bal','=',True),('payment_type','=','outbound')]):
            if amount > 0.0:
                amount -= pobj.amount
                print("amount =",amount)

        print("2........")
        for obj in self.env['account.move'].search([
                                            ('partner_id','=',self.id),
                                            ('state','=','posted'),
                                            ('move_type','in',['in_invoice','in_refund']),
                                            ('date','>=',str(start_date_month)),
                                            ('date','<=',str(end_date_month))]):
            print("obj ==",obj,obj.name,obj.move_type)
            if obj.move_type == 'in_invoice':
                amount += obj.amount_total
                invoice_ids.append(obj.id)
            elif obj.move_type == 'in_refund':
                amount -= obj.amount_total
            print(amount)
            invoice_ids.append(obj.id)

        print("3.............")
        for obj in self.env['account.move'].search([
                                            ('partner_id','=',self.id),
                                            ('state','=','posted'),
                                            ('payment_id.payment_type','=','outbound'),
                                            ('date','<=',str(self.month_end_date))]):
            print("obj ==",obj,obj.name,obj.payment_id.reconciled_invoice_ids)
            if obj.payment_id.reconciled_invoice_ids and obj.payment_id.reconciled_invoice_ids[0].id in invoice_ids:
                amount -= obj.amount_total
                print(amount)

        if amount < 0.0:
            amount = 0.0
        return amount

    # Balance summry Table  - On Monthly Statement
    def compute_monthwise_monthly_statement_summary_supplier(self):
        print("\ncompute_monthwise_monthly_statement_summary() >>>>>>")
        self.ensure_one()
        current_month = 0.0
        current_month_minus_one = 0.0
        current_month_minus_two = 0.0
        current_month_minus_three_beyond = 0.0

        month_start = self.month_start_date
        print("month_start =",month_start)

        first_day_current_month = month_start.replace(day=1)
        first_day_previous_month = (first_day_current_month - timedelta(days=1)).replace(day=1)
        first_day_month_before_previous = (first_day_previous_month - timedelta(days=1)).replace(day=1)
        last_month_beyond = (first_day_month_before_previous - timedelta(days=1)).replace(day=1)
        print(first_day_current_month, first_day_previous_month, first_day_month_before_previous, last_month_beyond)

        current_month = self.get_balance_of_month_supplier(first_day_current_month)
        current_month_minus_one = self.get_balance_of_month_supplier(first_day_previous_month)
        current_month_minus_two = self.get_balance_of_month_supplier(first_day_month_before_previous)
        current_month_minus_three_beyond = self.get_balance_of_month_supplier(last_month_beyond, True)

        print(" FINALLY ===",current_month, current_month_minus_one, current_month_minus_two, current_month_minus_three_beyond, current_month + current_month_minus_one + current_month_minus_two + current_month_minus_three_beyond)
        return [current_month, current_month_minus_one, current_month_minus_two, current_month_minus_three_beyond, current_month + current_month_minus_one + current_month_minus_two + current_month_minus_three_beyond]



    def generate_paynow_qr_for_soa(self):
        """
        Generate PayNow QR code for Statement of Account (SOA)
        No transaction amount included.
        """

        self.ensure_one()

        PayNow_ID = str(self.company_id.l10n_sg_unique_entity_number or "")
        Merchant_name = self.company_id.name or ""
        Bill_number = self.name or ""      # SOA ref: use partner name

        # CONSTANT FIELDS
        Can_edit_amount = "1"              # Allow user to key-in amount
        Merchant_category = "0000"
        Transaction_currency = "702"
        Country_code = "SG"
        Merchant_city = "Singapore"
        Globally_Unique_ID = "SG.PAYNOW"
        Proxy_type = "2"

        start_string = "010212"
        Dynamic_PayNow_QR = "000201"

        # *** FIELD LENGTHS ***
        Globally_Unique_ID_field = "00"
        Globally_Unique_ID_length = str(len(Globally_Unique_ID)).zfill(2)

        Proxy_type_field = "01"
        Proxy_type_length = str(len(Proxy_type)).zfill(2)

        PayNow_ID_field = "02"
        PayNow_ID_Length = str(len(PayNow_ID)).zfill(2)

        Can_edit_amount_field = "03"
        Can_edit_amount_length = str(len(Can_edit_amount)).zfill(2)

        Merchant_category_field = "52"
        Merchant_category_length = str(len(Merchant_category)).zfill(2)

        Transaction_currency_field = "53"
        Transaction_currency_length = str(len(Transaction_currency)).zfill(2)

        # Merchant account composite field
        Merchant_Account_Info_field = "26"
        Merchant_Account_Info_length = str(
            len(
                Globally_Unique_ID_field + Globally_Unique_ID_length + Globally_Unique_ID +
                Proxy_type_field + Proxy_type_length + Proxy_type +
                PayNow_ID_field + PayNow_ID_Length + PayNow_ID +
                Can_edit_amount_field + Can_edit_amount_length + Can_edit_amount
            )
        ).zfill(2)

        Country_code_field = "58"
        Country_code_length = str(len(Country_code)).zfill(2)

        Merchant_name_field = "59"
        Merchant_name_length = str(len(Merchant_name)).zfill(2)

        Merchant_city_field = "60"
        Merchant_city_length = str(len(Merchant_city)).zfill(2)

        # BILL NUMBER — optional reference
        Bill_number_field = "62"
        Bill_number_sub_length = str(len(Bill_number)).zfill(2)
        Bill_number_length = str(len("01" + Bill_number_sub_length + Bill_number)).zfill(2)

        # *** BUILD STRING FOR CRC ***
        data_for_crc = (
            Dynamic_PayNow_QR +
            start_string +
            Merchant_Account_Info_field + Merchant_Account_Info_length +
            Globally_Unique_ID_field + Globally_Unique_ID_length + Globally_Unique_ID +
            Proxy_type_field + Proxy_type_length + Proxy_type +
            PayNow_ID_field + PayNow_ID_Length + PayNow_ID +
            Can_edit_amount_field + Can_edit_amount_length + Can_edit_amount +
            Merchant_category_field + Merchant_category_length + Merchant_category +
            Transaction_currency_field + Transaction_currency_length + Transaction_currency +
            Country_code_field + Country_code_length + Country_code +
            Merchant_name_field + Merchant_name_length + Merchant_name +
            Merchant_city_field + Merchant_city_length + Merchant_city +
            Bill_number_field + Bill_number_length + "01" + Bill_number_sub_length + Bill_number +
            "6304"
        )

        # *** GENERATE CRC ***
        crc = pycrc.algorithms.Crc(
            width=16, poly=0x1021, reflect_in=False,
            xor_in=0xffff, reflect_out=False, xor_out=0x0000
        )
        crc_hex = "{:04X}".format(crc.bit_by_bit_fast(data_for_crc))

        final_string = data_for_crc + crc_hex

        # *** GENERATE QR CODE IMAGE ***
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=5,
            border=2,
        )
        qr.add_data(final_string)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#57004700")

        # Add PayNow logo
        paynow_logo_path = get_module_resource(
            'account_statement', 'static/img', 'paynow.png'
        )
        logo = Image.open(paynow_logo_path)

        max_size = 100
        scale = max_size / max(logo.size)
        resized_logo = logo.resize(
            (int(logo.size[0] * scale), int(logo.size[1] * scale)),
            Image.ANTIALIAS
        )

        qr_width, qr_height = img.size
        logo_w, logo_h = resized_logo.size
        x = (qr_width - logo_w) // 2
        y = (qr_height - logo_h) // 2

        img.paste(resized_logo, (x, y))

        # Convert to base64
        temp = BytesIO()
        img.save(temp, format="PNG")
        return base64.b64encode(temp.getvalue())
