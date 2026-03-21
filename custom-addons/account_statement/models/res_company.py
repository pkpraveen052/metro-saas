# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class Company(models.Model):
    _inherit = 'res.company'
    
    send_statement = fields.Boolean("Send Customer Statement")
    period = fields.Selection([('monthly', 'Monthly'),('all', "All")],'Period',default='monthly')
    statement_days = fields.Integer("Statement Send Date")
    show_aging_bucket_table = fields.Boolean('Show Overdue Summary on Customer statement', default=True)
    show_invoice_summary_monthly_statement = fields.Boolean('Show Account Summary on Monthly Statement')
    show_balance_summary_statement = fields.Boolean('Show Summary on Customer Statement')
    show_supplier_summary_statement = fields.Boolean('Show Summary on Supplier Statement')
    inital_carry_fwd_balance_plus_oneday = fields.Boolean('Make the Initial Carry Forward Balance Date to Next Month')

    show_tc_customer_statement = fields.Boolean('Show T&C on Customer Statement')
    customer_overdue_statement_tc = fields.Text('T&C Customer Statement')
    show_paynow_qrcode_cs = fields.Boolean(' Show QR Code on Customer Statement')

class AccountConfig(models.TransientModel):
    _inherit = "res.config.settings"
    
    send_statement = fields.Boolean(related='company_id.send_statement',string="Send Customer Statement",readonly=False)
    period = fields.Selection([('monthly', 'Monthly'),('all', "All")],'Period',related='company_id.period',readonly=False)
    statement_days = fields.Integer(related='company_id.statement_days',string="Statement Date",readonly=False)
    show_aging_bucket_table = fields.Boolean(related='company_id.show_aging_bucket_table', string='Show Overdue Summary on Customer statement', readonly=False)
    show_invoice_summary_monthly_statement = fields.Boolean(related='company_id.show_invoice_summary_monthly_statement', string='Show Account Summary on Monthly Statement', readonly=False)
    show_balance_summary_statement = fields.Boolean(related='company_id.show_balance_summary_statement', string='Show Summary on Customer Statement', readonly=False)
    show_supplier_summary_statement = fields.Boolean(related='company_id.show_supplier_summary_statement', string='Show Summary on Supplier Statement', readonly=False)
    inital_carry_fwd_balance_plus_oneday = fields.Boolean(related='company_id.inital_carry_fwd_balance_plus_oneday', string='Make the Initial Carry Forward Balance Date to Next Month', readonly=False)

    show_tc_customer_statement = fields.Boolean(related='company_id.show_tc_customer_statement',string='Show T&C on Customer Statement',readonly=False)
    customer_overdue_statement_tc = fields.Text(related='company_id.customer_overdue_statement_tc',string='T&C Customer Statement',readonly=False)
    show_paynow_qrcode_cs = fields.Boolean(related='company_id.show_paynow_qrcode_cs',string='Show QR Code on Customer Statement',readonly=False)