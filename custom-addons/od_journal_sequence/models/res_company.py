# -*- coding: utf-8 -*-
import os
from odoo import models,api

class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def create(self, vals):
        company_obj = super(ResCompany, self).create(vals)
        company_obj.create_od_journal_sequence()
        return company_obj


    def create_od_journal_sequence(self):
        obj = self
        payment_customer_invoice_sequence = self.env['ir.sequence'].search([('code', '=', 'account.payment.customer.invoice'), ('company_id', '=', obj.id)])
        if not payment_customer_invoice_sequence:
            payment_customer_invoice_sequence = self.env['ir.sequence'].create({
                'name': 'Payments customer invoices sequence - ' + obj.name,
                'code': 'account.payment.customer.invoice',
                'padding': 4,
                'prefix': 'CUST.IN/%(range_year)s/',
                'use_date_range':True,
                'company_id': obj.id
            })

        payment_customer_credit_note_sequence = self.env['ir.sequence'].search(
            [('code', '=', 'account.payment.customer.refund'), ('company_id', '=', obj.id)])
        if not payment_customer_credit_note_sequence:
            payment_customer_credit_note_sequence = self.env['ir.sequence'].create({
                'name': 'Payments customer credit notes sequence - ' + obj.name,
                'code': 'account.payment.customer.refund',
                'padding': 4,
                'prefix': 'CUST.OUT/%(range_year)s/',
                'use_date_range': True,
                'company_id': obj.id
            })

        payment_supplier_invoice_sequence = self.env['ir.sequence'].search(
            [('code', '=', 'account.payment.supplier.invoice'), ('company_id', '=', obj.id)])
        if not payment_supplier_invoice_sequence:
            payment_supplier_invoice_sequence = self.env['ir.sequence'].create({
                'name': 'Payments supplier invoices sequence - ' + obj.name,
                'code': 'account.payment.supplier.invoice',
                'padding': 4,
                'prefix': 'SUPP.OUT/%(range_year)s/',
                'use_date_range': True,
                'company_id': obj.id
            })

        payment_supplier_credit_notes_sequence = self.env['ir.sequence'].search(
            [('code', '=', 'account.payment.supplier.refund'), ('company_id', '=', obj.id)])
        if not payment_supplier_credit_notes_sequence:
            payment_supplier_credit_notes_sequence = self.env['ir.sequence'].create({
                'name': 'Payments supplier credit notes sequence - ' + obj.name,
                'code': 'account.payment.supplier.refund',
                'padding': 4,
                'prefix': 'SUPP.IN/%(range_year)s/',
                'use_date_range': True,
                'company_id': obj.id
            })

        payment_transfer_sequence = self.env['ir.sequence'].search(
            [('code', '=', 'account.payment.transfer'), ('company_id', '=', obj.id)])
        if not payment_transfer_sequence:
            payment_transfer_sequence = self.env['ir.sequence'].create({
                'name': 'Payments transfer sequence - ' + obj.name,
                'code': 'account.payment.transfer',
                'padding': 4,
                'prefix': 'TRANS/%(range_year)s/',
                'use_date_range': True,
                'company_id': obj.id
            })
        receive_money_sequence = self.env['ir.sequence'].search(
            [('code', '=', 'account.move.receive'), ('company_id', '=', obj.id)])
        if not receive_money_sequence:
            receive_money_sequence = self.env['ir.sequence'].create({
                'name': 'Receive Money sequence - ' + obj.name,
                'code': 'account.move.receive',
                'padding': 4,
                'prefix': 'RM/%(range_year)s/',
                'use_date_range': True,
                'company_id': obj.id
            })

        spend_money_sequence = self.env['ir.sequence'].search(
            [('code', '=', 'account.move.spend'), ('company_id', '=', obj.id)])
        if not spend_money_sequence:
            spend_money_sequence = self.env['ir.sequence'].create({
                'name': 'Spend Money sequence - ' + obj.name,
                'code': 'account.move.spend',
                'padding': 4,
                'prefix': 'SM/%(range_year)s/',
                'use_date_range': True,
                'company_id': obj.id
            })
