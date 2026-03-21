# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import ValidationError, UserError
import uuid
import logging

logger = logging.getLogger(__name__)


class PeppolManualSendPaymentWizard(models.TransientModel):
    _name = 'peppol.manual.send.payment.wizard'
    _description = 'PEPPOL Manual Send Payment Wizard'

    message = fields.Text(readonly=True)


    def action_send_payment(self):
        ctx = self._context
        print('\nctxctxctx', ctx)
        payment_ids = ctx.get('active_ids', [])
        if ctx.get('active_model') == 'account.move':
            documents = self.env['account.move'].browse(payment_ids)
        else:
            documents = self.env['account.payment'].browse(payment_ids)
        if all(spend_money.journal_id.type == 'cash' for spend_money in documents) and ctx.get('active_model') == 'account.move':
            pcp_id = self._create_petty_cash_spend_money(invoices=documents)
            print('\n\npcp_id', pcp_id)
            documents.write({'pcp_outgoing_inv_doc_ref': pcp_id.id})
            return {
                'name': self.sudo().env.ref('metro_einvoice_datapost.action_petty_cash_purchase').name,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': pcp_id.id,
                'res_model': 'pcp.outgoing.invoices',
            }
        elif documents.pos_order_ids:
            b2c_invoice = self._create_b2c_outgoing_invoice(invoices=documents)
            documents.write({'b2c_outgoing_inv_doc_ref': b2c_invoice.id})
            return {
                'name': self.sudo().env.ref('metro_einvoice_datapost.action_b2c_outgoing_invoices').name,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_id': b2c_invoice.id,
                'view_type': 'form',
                'res_model': 'b2c.outgoing.invoices',
            }
        elif all(payment.journal_id.type == 'cash' for payment in documents):
            pcp_id = self._create_petty_cash_payment(payments=documents)
            documents.write({'pcp_outgoing_inv_doc_ref': pcp_id.id})
            return {
                'name': self.sudo().env.ref('metro_einvoice_datapost.action_petty_cash_purchase').name,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': pcp_id.id,
                'res_model': 'pcp.outgoing.invoices',
            }
        else:
            raise ValidationError('Only those Petty Cash payment will be sent to peppol')


    def _create_petty_cash_spend_money(self,invoices):
        company = invoices[0].company_id  # Take company from first invoice
        currency = invoices[0].currency_id  # Use currency from invoices

        # Aggregate amounts

        tax_amount = sum(invoice.amount_tax for invoice in invoices)
        taxable_amount = sum(invoice.amount_untaxed for invoice in invoices)
        total_amount = sum(invoice.amount_total for invoice in invoices)

        # Get the latest invoice date
        issue_date = max(invoices.mapped('date')) if invoices else fields.Date.today()
        pcp_invoices_obj = self.env['pcp.outgoing.invoices']
        # Create the PCP invoice record
        pcp_invoice = pcp_invoices_obj.create({
            'company_id': company.id,
            'partner_id': company.partner_id.id,
            'receiver': 'IRAS',
            'tax_amount': tax_amount,
            'taxable_amount': taxable_amount,
            'tax_inclusive_amount': total_amount,
            'invoice_date': issue_date,
            'uuid': str(uuid.uuid4()),  # Generate random UUID
            'note': f'As Of {issue_date}',
            'currency_id': currency.id,
        })
        return pcp_invoice

    def _create_petty_cash_payment(self,payments):
        company = payments[0].company_id  # Take company from first invoice
        currency = payments[0].currency_id  # Use currency from invoices

        # Aggregate amounts

        total_amount = sum(invoice.amount for invoice in payments)
        tax_amount = total_amount * 0.09
        taxable_amount = total_amount * 0.91

        # Get the latest invoice date
        issue_date = max(payments.mapped('date')) if payments else fields.Date.today()
        pcp_invoices_obj = self.env['pcp.outgoing.invoices']
        # Create the PCP invoice record
        pcp_invoice = pcp_invoices_obj.create({
            'company_id': company.id,
            'partner_id': company.partner_id.id,
            'receiver': 'IRAS',
            'tax_amount': tax_amount,
            'taxable_amount': taxable_amount,
            'tax_inclusive_amount': total_amount,
            'invoice_date': issue_date,
            'uuid': str(uuid.uuid4()),  # Generate random UUID
            'note': f'As Of {issue_date}',
            'currency_id': currency.id,
        })
        return pcp_invoice

    def _create_b2c_outgoing_invoice(self, invoices):
        company = invoices[0].company_id  # Take company from first invoice
        currency = invoices[0].currency_id  # Use currency from invoices

        # Aggregate amounts
        tax_amount = sum(invoice.amount_tax for invoice in invoices)
        taxable_amount = sum(invoice.amount_untaxed for invoice in invoices)
        total_amount = sum(invoice.amount_total for invoice in invoices)

        # Get the latest invoice date
        issue_date = max(invoices.mapped('invoice_date')) if invoices else fields.Date.today()
        b2c_invoices_obj = self.env['b2c.outgoing.invoices']
        # Create the B2C invoice record
        b2c_invoice = b2c_invoices_obj.create({
            'company_id': company.id,
            'partner_id': company.partner_id.id,
            'receiver': 'POS/STI',
            'tax_amount': tax_amount,
            'taxable_amount': taxable_amount,
            'tax_inclusive_amount': total_amount,
            'invoice_date': issue_date,
            'uuid': str(uuid.uuid4()),  # Generate random UUID
            'note': f'POS/STI for {issue_date}',
            'currency_id': currency.id,
        })
        return b2c_invoice
