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
            obj.display_name = obj.name.split(". . ")[-1]

    @api.depends('account_ids')
    def _compute_no_child(self):
        for obj in self:
            if not obj.account_ids:
                obj.no_child = True
            else:
                obj.no_child = False

    name = fields.Char('Name', required=True)
    display_name = fields.Char(compute=_compute_name, string='Display Name')
    note = fields.Char('Note')
    bal_curr_year = fields.Char('Balance (S$)')
    bal_prev_year = fields.Char('Balance (S$))')
    statement_id = fields.Many2one('director.statement')
    content = fields.Text('Content')
    ref_id = fields.Integer('Ref ID')
    is_parent = fields.Boolean('Is Parent')
    no_child = fields.Boolean(compute=_compute_no_child, string='No Child')
    account_ids = fields.One2many('pl.account.lines', 'line_id', 'Accounts', default=False)

class ProfiltLossAccountLines(models.Model):
    _name = 'pl.account.lines'
    _description = 'Profit/ (Loss) Account lines'
    
    name = fields.Char('Account', required=True)
    bal_curr_year = fields.Char('(S$) (Current Year)', required=True)
    bal_prev_year = fields.Char('(S$) (Previous Year)', required=True)
    line_id = fields.Many2one('pl.lines')

class BalanceSheetLines(models.Model):
    _name = 'bs.lines'
    _description = 'Balance Sheet Lines'
    
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

    name = fields.Char('Name', required=True)
    display_name = fields.Char(compute=_compute_name, string='Display Name')
    note = fields.Char('Note')
    bal_curr_year = fields.Char('Balance (S$)')
    bal_prev_year = fields.Char('Balance (S$))')
    statement_id = fields.Many2one('director.statement')
    content = fields.Text('Content')
    ref_id = fields.Integer('Ref ID')
    is_parent = fields.Boolean('Is Parent')
    no_child = fields.Boolean(compute=_compute_no_child, string='No Child')
    account_ids = fields.One2many('bs.account.lines', 'line_id', 'Accounts', default=False)

class BalanceSheetAccountLines(models.Model):
    _name = 'bs.account.lines'
    _description = 'Balance Sheet Account lines'
    
    name = fields.Char('Account', required=True)
    bal_curr_year = fields.Char('(S$) (Current Year)', required=True)
    bal_prev_year = fields.Char('(S$) (Previous Year)', required=True)
    line_id = fields.Many2one('bs.lines')

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

    name = fields.Char('Name', required=True)
    display_name = fields.Char(compute=_compute_name, string='Display Name')
    note = fields.Char('Note')
    bal_curr_year = fields.Char('Balance (S$)')
    bal_prev_year = fields.Char('Balance (S$))')
    statement_id = fields.Many2one('director.statement')
    content = fields.Text('Content')
    ref_id = fields.Integer('Ref ID')
    is_parent = fields.Boolean('Is Parent')
    no_child = fields.Boolean(compute=_compute_no_child, string='No Child')
    account_ids = fields.One2many('cf.account.lines', 'line_id', 'Accounts', default=False)

class CashFlowAccountLines(models.Model):
    _name = 'cf.account.lines'
    _description = 'Cash Flow Account lines'
    
    name = fields.Char('Account', required=True)
    bal_curr_year = fields.Char('(S$) (Current Year)', required=True)
    bal_prev_year = fields.Char('(S$) (Previous Year)', required=True)
    line_id = fields.Many2one('cf.lines')

class ConfigDirectorNames(models.Model):
    _name = 'config.director.names'
    _description = 'Director Names'
    
    name = fields.Char('Director Name', required=True)
    config_id = fields.Many2one('director.statement.config')
    required_signature = fields.Boolean('Required Signature?')