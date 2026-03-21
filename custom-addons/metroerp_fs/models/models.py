# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import datetime
from datetime import datetime


class OrdinarySharesLines(models.Model):
    _name = 'ordinary.shares.lines'
    _description = 'Ordinary Shares of the Company'
    _rec_name = 'director_name'
    
    director_name = fields.Char('Director Name', required=True)
    beginning_year_amt = fields.Integer('At beginning of financial year', required=True)
    end_year_amt = fields.Integer('At end of financial year', required=True)
    statement_id = fields.Many2one('director.statement')

class ProfitLossLines(models.Model):
    _name = 'pl.lines'
    _description = 'Profit/ (Loss) Lines'
    
    @api.depends('name')
    def _compute_name(self):
        for obj in self:
            obj.display_name = obj.name and obj.name.split(". . ")[-1] or ''

    @api.depends('name', 'level')
    def _compute_name_with_space(self):
        for record in self:
            dic = {1: 1, 2: 4, 3: 8, 4: 16, 5: 24}
            record.name_display = (dic.get(record.level, 1) * ' ') + (record.name or '')

    @api.depends('account_ids')
    def _compute_no_child(self):
        for obj in self:
            if not obj.account_ids:
                obj.no_child = True
            else:
                obj.no_child = False

    @api.depends('bal_curr_year_temp', 'bal_prev_year_temp')
    def _compute_fmt_balances(self):
        def format_float_custom(value):
            if value == 0:
                return '-'
            elif value < 0:
                formatted_value = f"({abs(value):,})"
            else:
                formatted_value = f"{value:,}"
            return formatted_value

        for obj in self:
            obj.bal_curr_year = format_float_custom(obj.bal_curr_year_temp)
            obj.bal_prev_year = format_float_custom(obj.bal_prev_year_temp)

    name = fields.Char('Name', required=True)
    display_name = fields.Char(compute=_compute_name, string='Display Name')
    name_display = fields.Text(compute=_compute_name_with_space, string='Display Name')
    note = fields.Char('Note')
    bal_curr_year = fields.Char(compute=_compute_fmt_balances, string='Current Year Balance (S$)')
    bal_prev_year = fields.Char(compute=_compute_fmt_balances, string='Previous Year Balance (S$))')
    statement_id = fields.Many2one('director.statement')
    content = fields.Text('Content')
    ref_id = fields.Integer('Ref ID')
    is_parent = fields.Boolean('Is Parent')
    no_child = fields.Boolean(compute=_compute_no_child, string='No Child')
    account_ids = fields.One2many('pl.account.lines', 'line_id', 'Accounts', default=False)
    level = fields.Integer('Level', default=1)
    sequence = fields.Integer(string='Sequence', default=10)
    bal_curr_year_temp = fields.Integer('Current Year Balance', required=True)
    bal_prev_year_temp = fields.Integer('Previous Year Balance', required=True)

class ProfiltLossAccountLines(models.Model):
    _name = 'pl.account.lines'
    _description = 'Profit/ (Loss) Account lines'
    
    @api.depends('bal_curr_year_temp', 'bal_prev_year_temp')
    def _compute_balances(self):
        def format_float_custom(value):
            if value == 0:
                return '-'
            elif value < 0:
                formatted_value = f"({abs(value):,})"
            else:
                formatted_value = f"{value:,}"
            return formatted_value
        for obj in self:
            obj.bal_curr_year = format_float_custom(obj.bal_curr_year_temp)
            obj.bal_prev_year = format_float_custom(obj.bal_prev_year_temp)

    name = fields.Char('Account', required=True)
    bal_curr_year = fields.Char(compute=_compute_balances, string='(S$) (Current Year)')
    bal_prev_year = fields.Char(compute=_compute_balances, string='(S$) (Previous Year)')
    line_id = fields.Many2one('pl.lines')
    bal_curr_year_temp = fields.Integer('Current Year Balance', required=True)
    bal_prev_year_temp = fields.Integer('Previous Year Balance', required=True)
    sequence = fields.Integer(string='Sequence', default=10)

class BalanceSheetLines(models.Model):
    _name = 'bs.lines'
    _description = 'Balance Sheet Lines'
    
    @api.depends('name')
    def _compute_name(self):
        for obj in self:
            obj.display_name = obj.name and obj.name.split(". . ")[-1] or ''

    @api.depends('account_ids')
    def _compute_no_child(self):
        for obj in self:
            if not obj.account_ids:
                obj.no_child = True
            else:
                obj.no_child = False

    @api.depends('name', 'level')
    def _compute_name_with_space(self):
        for record in self:
            dic = {1: 1, 2: 4, 3: 8, 4: 16, 5: 24}
            record.name_display = (dic.get(record.level, 1) * ' ') + (record.name or '')

    @api.depends('bal_curr_year_temp', 'bal_prev_year_temp')
    def _compute_fmt_balances(self):
        def format_float_custom(value):
            if value == 0:
                return '-'
            elif value < 0:
                formatted_value = f"({abs(value):,})"
            else:
                formatted_value = f"{value:,}"
            return formatted_value

        for obj in self:
            obj.bal_curr_year = format_float_custom(obj.bal_curr_year_temp)
            obj.bal_prev_year = format_float_custom(obj.bal_prev_year_temp)

    name = fields.Char('Name', required=True)
    display_name = fields.Char(compute=_compute_name, string='Display Name')
    name_display = fields.Text(compute=_compute_name_with_space, string='Display Name')
    note = fields.Char('Note')
    bal_curr_year = fields.Char(compute=_compute_fmt_balances, string='Current Year Balance (S$)')
    bal_prev_year = fields.Char(compute=_compute_fmt_balances, string='Previous Year Balance (S$))')
    statement_id = fields.Many2one('director.statement')
    content = fields.Text('Content')
    ref_id = fields.Integer('Ref ID')
    is_parent = fields.Boolean('Is Parent')
    no_child = fields.Boolean(compute=_compute_no_child, string='No Child')
    account_ids = fields.One2many('bs.account.lines', 'line_id', 'Accounts', default=False)
    level = fields.Integer('Level', default=1)
    sequence = fields.Integer(string='Sequence', default=10)
    bal_curr_year_temp = fields.Integer('Current Year Balance', required=True)
    bal_prev_year_temp = fields.Integer('Previous Year Balance', required=True)

class BalanceSheetAccountLines(models.Model):
    _name = 'bs.account.lines'
    _description = 'Balance Sheet Account lines'
    
    @api.depends('bal_curr_year_temp', 'bal_prev_year_temp')
    def _compute_balances(self):
        def format_float_custom(value):
            if value == 0:
                return '-'
            elif value < 0:
                formatted_value = f"({abs(value):,})"
            else:
                formatted_value = f"{value:,}"
            return formatted_value
        for obj in self:
            obj.bal_curr_year = format_float_custom(obj.bal_curr_year_temp)
            obj.bal_prev_year = format_float_custom(obj.bal_prev_year_temp)

    name = fields.Char('Account', required=True)
    bal_curr_year = fields.Char(compute=_compute_balances, string='(S$) (Current Year)')
    bal_prev_year = fields.Char(compute=_compute_balances, string='(S$) (Previous Year)')
    line_id = fields.Many2one('bs.lines')
    bal_curr_year_temp = fields.Integer('Current Year Balance', required=True)
    bal_prev_year_temp = fields.Integer('Previous Year Balance', required=True)
    sequence = fields.Integer(string='Sequence', default=10)

class CashFlowLines(models.Model):
    _name = 'cf.lines'
    _description = 'Cash Flow Lines'
    
    @api.depends('name')
    def _compute_name(self):
        for obj in self:
            obj.display_name = obj.name.split(". . ")[-1]

    @api.depends('account_ids')
    def _compute_no_child(self):
        for obj in self:
            if not obj.account_ids:
                obj.no_child = True
            else:
                obj.no_child = False

    @api.depends('name', 'level')
    def _compute_name_with_space(self):
        for record in self:
            dic = {1: 1, 2: 4, 3: 8, 4: 16, 5: 24}
            record.name_display = (dic.get(record.level, 1) * ' ') + (record.name or '')

    @api.depends('bal_curr_year_temp', 'bal_prev_year_temp')
    def _compute_fmt_balances(self):
        def format_float_custom(value):
            if value == 0:
                return '-'
            elif value < 0:
                formatted_value = f"({abs(value):,})"
            else:
                formatted_value = f"{value:,}"
            return formatted_value

        for obj in self:
            obj.bal_curr_year = format_float_custom(obj.bal_curr_year_temp)
            obj.bal_prev_year = format_float_custom(obj.bal_prev_year_temp)

    name = fields.Char('Name', required=True)
    display_name = fields.Char(compute=_compute_name, string='Display Name')
    name_display = fields.Text(compute=_compute_name_with_space, string='Display Name')    
    note = fields.Char('Note')
    bal_curr_year = fields.Char(compute=_compute_fmt_balances, string='Current Year Balance (S$)')
    bal_prev_year = fields.Char(compute=_compute_fmt_balances, string='Previous Year Balance (S$))')
    statement_id = fields.Many2one('director.statement')
    content = fields.Text('Content')
    ref_id = fields.Integer('Ref ID')
    is_parent = fields.Boolean('Is Parent')
    no_child = fields.Boolean(compute=_compute_no_child, string='No Child')
    account_ids = fields.One2many('cf.account.lines', 'line_id', 'Accounts', default=False)
    level = fields.Integer('Level', default=1)
    sequence = fields.Integer(string='Sequence', default=10)
    bal_curr_year_temp = fields.Integer('Current Year Balance', required=True)
    bal_prev_year_temp = fields.Integer('Previous Year Balance', required=True)

class CashFlowAccountLines(models.Model):
    _name = 'cf.account.lines'
    _description = 'Cash Flow Account lines'

    @api.depends('bal_curr_year_temp', 'bal_prev_year_temp')
    def _compute_balances(self):
        def format_float_custom(value):
            if value == 0:
                return '-'
            elif value < 0:
                formatted_value = f"({abs(value):,})"
            else:
                formatted_value = f"{value:,}"
            return formatted_value
        for obj in self:
            obj.bal_curr_year = format_float_custom(obj.bal_curr_year_temp)
            obj.bal_prev_year = format_float_custom(obj.bal_prev_year_temp)

    name = fields.Char('Account', required=True)
    bal_curr_year = fields.Char(compute=_compute_balances, string='(S$) (Current Year)')
    bal_prev_year = fields.Char(compute=_compute_balances, string='(S$) (Previous Year)')
    line_id = fields.Many2one('cf.lines')
    bal_curr_year_temp = fields.Integer('Current Year Balance', required=True)
    bal_prev_year_temp = fields.Integer('Previous Year Balance', required=True)
    sequence = fields.Integer(string='Sequence', default=10)