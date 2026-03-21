# -*- coding: utf-8 -*-
from email.policy import default

from odoo import fields, models, _
from odoo.exceptions import ValidationError, UserError
import uuid
import logging

logger = logging.getLogger(__name__)


class PeppolManualSendWizard(models.TransientModel):
    _name = 'peppol.manual.send.wizard'
    _description = 'PEPPOL Manual Send Wizard'

    mode = fields.Selection([('test', 'test'), ('live', 'live')], string="Mode")
    message = fields.Text(readonly=True)
    send_as_Bulk  = fields.Boolean('Send as Bulk', default=False)
    invoice_send_type = fields.Selection([('peppol', 'Peppol'), ('non-peppol', 'Non-Peppol')], string="Type")
    is_both = fields.Boolean('Both', default=False) #this field take by hide and unhide field invoice_send_type
    is_sale_credit = fields.Boolean('Is Credit', default=False)

    def button_inv_send(self):
        self.ensure_one()
        ctx = self._context
        print('\n\n\n\n\nctx', ctx)
        # documents = self.env['account.move'].browse(ctx['active_ids']) if ctx.get('active_ids') else False
        # if all(invoice.journal_id.type == 'sale' and invoice.journal_id.name == 'Point of Sale' for invoice in documents):
        #     b2c_invoice = self._create_b2c_outgoing_invoice(invoices=documents)
        #     documents.write({'b2c_outgoing_inv_doc_ref': b2c_invoice.id})
        #     return {
        #         'name': self.sudo().env.ref('metro_einvoice_datapost.action_b2c_outgoing_invoices').name,
        #         'type': 'ir.actions.act_window',
        #         'view_mode': 'form',
        #         'res_id': b2c_invoice.id,
        #         'view_type': 'form',
        #         'res_model': 'b2c.outgoing.invoices',
        #     }
        # Prakash start
        out_action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'peppol.queue.out',
        }
        c5_out_action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'peppol.queue.c5.out',
        }
        action_mapping = {
            # peppole action
            ('out_invoice', True): 'metro_einvoice_datapost.peppol_queue_out_action',
            ('out_refund', True): 'metro_einvoice_datapost.peppol_queue_out_action',
            ('in_invoice', True, True): 'metro_einvoice_datapost.peppol_bulk_purchase_invoice_queue_c5_action',
            ('in_refund', True, True): 'metro_einvoice_datapost.peppol_bulk_purchase_creditnote_queue_c5_action',

            ('out_invoice', False, True): 'metro_einvoice_datapost.peppol_bulk_sales_invoice_queue_c5_action',
            ('out_refund', False, True): 'metro_einvoice_datapost.peppol_bulk_sales_creditnote_queue_c5_action',
            ('in_invoice', False, True): 'metro_einvoice_datapost.nonpeppol_bulk_purchase_invoice_queue_c5_action',
            ('in_refund', False, True): 'metro_einvoice_datapost.nonpeppol_bulk_purchase_creditnote_queue_c5_action',


            ('in_invoice', True, False): 'metro_einvoice_datapost.peppol_queue_c5_out_action',
            ('in_refund', True, False): 'metro_einvoice_datapost.peppol_credit_queue_c5_out_action',

            ('out_invoice', False, False): 'metro_einvoice_datapost.peppol_sales_invoice_queue_c5_action',
            ('out_refund', False, False): 'metro_einvoice_datapost.peppol_sales_creditnote_queue_c5_action',
            ('in_invoice', False, False): 'metro_einvoice_datapost.non_peppol_queue_c5_purchase_inv_action',
            ('in_refund', False, False): 'metro_einvoice_datapost.non_peppol_queue_c5_purchase_credit_action',
        }


        peppol_invoices = ctx.get('default_peppol_invoices', [])
        print('\n\n\n\n\npeppol_invoices', peppol_invoices)
        non_peppol_invoices = ctx.get('default_nonpeppol_invoices', [])
        print('\n\n\n\n\nnon_peppol_invoices', non_peppol_invoices)

        move_type = ctx.get('default_move_type', '')[0]
        print('\n\n\n\n\nmove_type', move_type)
        is_both = bool(peppol_invoices and non_peppol_invoices)
        print('\n\n\n\n\nis_both', is_both)

        if is_both and not self.invoice_send_type:
            raise ValidationError("Please selecte at least one Type!!")
        elif self.invoice_send_type == 'peppol' or (not is_both and peppol_invoices):
            invoice_ids = peppol_invoices
            is_peppol = True
        elif self.invoice_send_type == 'non-peppol' or (not is_both and non_peppol_invoices):
            invoice_ids = non_peppol_invoices
            is_peppol = False
        print('\n\n\n\n\ninvoice_ids', invoice_ids)
        invoices = self.env['account.move'].browse(invoice_ids)
        for inv in invoices:
            inv.check_nongst_to_peppol()
        peppol_queue_out = self.env['peppol.queue.out']
        peppol_queue_c5_out = self.env['peppol.queue.c5.out']
        if self.send_as_Bulk:
            if is_peppol:
                print('\n\n\n\n\nis_peppol_bulk', is_peppol)

                if move_type in ('out_invoice', 'out_refund'):
                    for invoice in invoices:
                        bulk_queue_ref = peppol_queue_out.create({
                        "invoice_id": invoice.id,
                        "invoice_type": move_type,
                        })
                        invoice.write({'outgoing_inv_doc_ref': bulk_queue_ref.id})
                    action_ref = action_mapping.get((move_type, is_peppol))
                    print('\n\n\n\nis_peppolaction_ref', action_ref)
                    out_action.update({'name': self.sudo().env.ref(action_ref).name,
                                       'domain': [('invoice_type','=', move_type)]})
                    return out_action
                elif move_type in ('in_invoice', 'in_refund'):
                    bulk_queue_c5_ref = peppol_queue_c5_out.create({
                    "invoice_ids": [(6, 0, invoices.ids)],
                    "document_xml_type": "bulk",
                    "invoice_type": move_type,
                    "is_peppol": True,
                    })
                    invoices.write({'outgoing_inv_doc_ref_c5': bulk_queue_c5_ref.id})
                    action_ref = action_mapping.get((move_type, is_peppol, self.send_as_Bulk))
                    print('\n\n\n\nis_peppol_purchase_action_ref', action_ref)
                    c5_out_action.update({'name': self.sudo().env.ref(action_ref).name,
                                          'views': [
                                              (self.env.ref('metro_einvoice_datapost.peppol_queue_c5_bulk_invoice_tree').id, 'tree'),
                                              (self.env.ref('metro_einvoice_datapost.peppol_queue_c5_out_form').id, 'form')],
                                       'domain': [('invoice_type', '=', move_type), ('document_xml_type','=','bulk')]})
                    return c5_out_action
            else:
                bulk_queue_c5_ref = peppol_queue_c5_out.create({
                    "invoice_ids": [(6, 0, invoices.ids)],
                    "document_xml_type": "bulk",
                    "invoice_type": move_type,
                })
                invoices.write({'outgoing_inv_doc_ref_c5': bulk_queue_c5_ref.id})
                action_ref = action_mapping.get((move_type, is_peppol, self.send_as_Bulk))
                print('\n\n\n\nnonopeppol_action_ref', action_ref)
                c5_out_action.update({'name': self.sudo().env.ref(action_ref).name,
                                      'views': [
                                          (self.env.ref('metro_einvoice_datapost.peppol_queue_c5_bulk_invoice_tree').id, 'tree'),
                                          (self.env.ref('metro_einvoice_datapost.peppol_queue_c5_out_form').id, 'form')],
                                      'domain': [('invoice_type', '=', move_type), ('document_xml_type','=','bulk')]})
                return c5_out_action
        else:
            for invoice in invoices:
                if is_peppol:
                    if move_type in ('out_invoice', 'out_refund'):
                        bulk_queue_ref = peppol_queue_out.create({
                            "invoice_id": invoice.id,
                            "invoice_type": move_type,
                        })
                        invoice.write({'outgoing_inv_doc_ref': bulk_queue_ref.id})
                    elif move_type in ('in_invoice', 'in_refund'):
                        bulk_queue_c5_ref = peppol_queue_c5_out.create({
                            "invoice_id": invoice.id,
                            "document_xml_type": "single",
                            "invoice_type": move_type,
                            "is_peppol": True,
                        })
                        invoice.write({'outgoing_inv_doc_ref_c5': bulk_queue_c5_ref.id})
                else:
                    bulk_queue_c5_ref = peppol_queue_c5_out.create({
                        "invoice_id": invoice.id,
                        "document_xml_type": "single",
                        "invoice_type": move_type,
                    })
                    invoice.write({'outgoing_inv_doc_ref_c5': bulk_queue_c5_ref.id})

            if is_peppol and move_type in ('out_invoice', 'out_refund'):
                action_ref = action_mapping.get((move_type, is_peppol))
                print('\n\n\n\nindividule_is_peppole', action_ref)
                out_action.update({'name': self.sudo().env.ref(action_ref).name,
                                   'domain': [('invoice_type', '=', move_type)]})
                return out_action
            else:
                action_ref = action_mapping.get((move_type, is_peppol, False))
                print('\n\n\n\nindividule_both_non_with_pep', action_ref)
                c5_out_action.update({'name': self.sudo().env.ref(action_ref).name,
                                      'domain': [('invoice_type', '=', move_type), ('document_xml_type', '=', 'single')]})
                return c5_out_action
        # old code >>>>>>>>>>>>>>>>>>>>>>>::
        # if self.send_as_Bulk:
        #     print('\n\n\n\n\nself.invoice_send_type', self.invoice_send_type)
        #     if ctx.get('is_nonpeppol') == True:
        #         bulk_queue_ref = self.env['peppol.queue.c5.out'].create({
        #             "invoice_ids": [(6, 0, documents.ids)],
        #             "document_xml_type": "bulk",
        #             "invoice_type": "out_invoice",
        #         })
        #         documents.write({'outgoing_inv_doc_ref_c5': bulk_queue_ref.id})
        #         return {
        #             'name': self.sudo().env.ref('metro_einvoice_datapost.peppol_bulk_sales_invoice_queue_c5_action').name,
        #             'type': 'ir.actions.act_window',
        #             'view_mode': 'tree,form',
        #             'view_type': 'form',
        #             'views': [(self.env.ref('metro_einvoice_datapost.peppol_queue_c5_bulk_invoice_tree').id, 'tree'),
        #                       (self.env.ref('metro_einvoice_datapost.peppol_queue_c5_out_form').id, 'form')],
        #             'res_model': 'peppol.queue.c5.out',
        #             'domain': [('invoice_type','=','out_invoice'),('document_xml_type','=','bulk')],
        #         }
        #     elif ctx.get('is_peppol') == True:
        #         for document in documents:
        #             queue_ref = self.env['peppol.queue.out'].create({
        #                 'invoice_type': document.move_type,
        #                 'invoice_id': document.id
        #             })
        #             print('\n\n\n\nonly_pep', queue_ref)
        #             document.write({'outgoing_inv_doc_ref': queue_ref.id})
        #         # document.write({'outgoing_inv_doc_ref': queue_ref.id, 'bulk_c5_invoice': True})
        #         return {
        #             'name': self.sudo().env.ref('metro_einvoice_datapost.peppol_queue_out_action').name,
        #             'type': 'ir.actions.act_window',
        #             'view_mode': 'tree,form',
        #             'view_type': 'form',
        #             'res_model': 'peppol.queue.out',
        #         }
        #     elif self.is_both and self.invoice_send_type == 'non-peppol':
        #         bulk_queue_ref = self.env['peppol.queue.c5.out'].create({
        #             "invoice_ids": [(6, 0, self.env['account.move'].browse(ctx['cus_nonpeppol_inv']).ids)],
        #             "document_xml_type": "bulk",
        #             "invoice_type": "out_invoice",
        #         })
        #         documents.write({'outgoing_inv_doc_ref_c5': bulk_queue_ref.id})
        #         return {
        #             'name': self.sudo().env.ref('metro_einvoice_datapost.peppol_bulk_sales_invoice_queue_c5_action').name,
        #             'type': 'ir.actions.act_window',
        #             'view_mode': 'tree,form',
        #             'view_type': 'form',
        #             'views': [(self.env.ref('metro_einvoice_datapost.peppol_queue_c5_bulk_invoice_tree').id, 'tree'),
        #                       (self.env.ref('metro_einvoice_datapost.peppol_queue_c5_out_form').id, 'form')],
        #             'res_model': 'peppol.queue.c5.out',
        #             'domain': [('invoice_type','=','out_invoice'),('document_xml_type','=','bulk')],
        #         }
        #     elif self.is_both and self.invoice_send_type == 'peppol':
        #         for inv in self.env['account.move'].browse(ctx['cus_peppol_inv']):
        #             queue_ref = self.env['peppol.queue.out'].create({
        #                 'invoice_type': inv.move_type,
        #                 'invoice_id': inv.id
        #             })
        #             print('\n\n\n\nnonpopboth', queue_ref)
        #
        #             inv.write({'outgoing_inv_doc_ref': queue_ref.id})
        #         return {
        #             'name': self.sudo().env.ref(
        #                 'metro_einvoice_datapost.peppol_queue_out_action').name,
        #             'type': 'ir.actions.act_window',
        #             'view_mode': 'tree,form',
        #             'view_type': 'form',
        #             'res_model': 'peppol.queue.out',
        #         }
        #
        # else:
        #     if ctx.get('is_peppol') == True:
        #         for document in documents:
        #             queue_ref = self.env['peppol.queue.out'].create({
        #                 'invoice_type': document.move_type,
        #                 'invoice_id': document.id
        #             })
        #             print('\n\n\n\nonly_pep', queue_ref)
        #             document.write({'outgoing_inv_doc_ref': queue_ref.id})
        #         # document.write({'outgoing_inv_doc_ref': queue_ref.id, 'bulk_c5_invoice': True})
        #         return {
        #             'name': self.sudo().env.ref('metro_einvoice_datapost.peppol_queue_out_action').name,
        #             'type': 'ir.actions.act_window',
        #             'view_mode': 'tree,form',
        #             'view_type': 'form',
        #             'res_model': 'peppol.queue.out',
        #         }
        #     if ctx.get('is_nonpeppol') == True:
        #         for document in documents:
        #             queue_ref = self.env['peppol.queue.c5.out'].create({
        #                 'invoice_type': document.move_type,
        #                 'invoice_id': document.id
        #             })
        #             document.write({'outgoing_inv_doc_ref_c5': queue_ref.id})
        #         return {
        #             'name': self.sudo().env.ref('metro_einvoice_datapost.peppol_sales_invoice_queue_c5_action').name,
        #             'type': 'ir.actions.act_window',
        #             'view_mode': 'tree,form',
        #             'view_type': 'form',
        #             'res_model': 'peppol.queue.c5.out',
        #             'domain': [('invoice_type','=','out_invoice'),('document_xml_type','=','single')],
        #         }
        #     if self.is_both:
        #         if not self.invoice_send_type:
        #             raise ValidationError("Please selecte at least one Type!!")
        #         elif self.invoice_send_type == 'peppol':
        #             for inv in self.env['account.move'].browse(ctx['cus_peppol_inv']):
        #                 queue_ref = self.env['peppol.queue.out'].create({
        #                     'invoice_type': inv.move_type,
        #                     'invoice_id': inv.id
        #                 })
        #                 print('\n\n\n\npepboth', queue_ref)
        #                 inv.write({'outgoing_inv_doc_ref': queue_ref.id})
        #             return {
        #                 'name': self.sudo().env.ref('metro_einvoice_datapost.peppol_queue_out_action').name,
        #                 'type': 'ir.actions.act_window',
        #                 'view_mode': 'tree,form',
        #                 'view_type': 'form',
        #                 'res_model': 'peppol.queue.out',
        #             }
        #         elif self.invoice_send_type == 'non-peppol':
        #             for inv in self.env['account.move'].browse(ctx['cus_nonpeppol_inv']):
        #                 queue_ref = self.env['peppol.queue.c5.out'].create({
        #                     'invoice_type': inv.move_type,
        #                     'invoice_id': inv.id
        #                 })
        #                 print('\n\n\n\nnonpopboth', queue_ref)
        #
        #                 inv.write({'outgoing_inv_doc_ref_c5': queue_ref.id})
        #             return {
        #                 'name': self.sudo().env.ref(
        #                     'metro_einvoice_datapost.peppol_sales_invoice_queue_c5_action').name,
        #                 'type': 'ir.actions.act_window',
        #                 'view_mode': 'tree,form',
        #                 'view_type': 'form',
        #                 'res_model': 'peppol.queue.c5.out',
        #                 'domain': [('invoice_type','=','out_invoice'),('document_xml_type','=','single')],
        #             }


    # def _create_b2c_outgoing_invoice(self, invoices):
    #     company = invoices[0].company_id  # Take company from first invoice
    #     currency = invoices[0].currency_id  # Use currency from invoices
    #
    #     # Aggregate amounts
    #     tax_amount = sum(invoice.amount_tax for invoice in invoices)
    #     taxable_amount = sum(invoice.amount_untaxed for invoice in invoices)
    #     total_amount = sum(invoice.amount_total for invoice in invoices)
    #
    #     # Get the latest invoice date
    #     issue_date = max(invoices.mapped('invoice_date')) if invoices else fields.Date.today()
    #     b2c_invoices_obj = self.env['b2c.outgoing.invoices']
    #     # Create the B2C invoice record
    #     b2c_invoice = b2c_invoices_obj.create({
    #         'company_id': company.id,
    #         'partner_id': company.partner_id.id,
    #         'receiver': 'POS/STI',
    #         'tax_amount': tax_amount,
    #         'taxable_amount': taxable_amount,
    #         'tax_inclusive_amount': total_amount,
    #         'invoice_date': issue_date,
    #         'uuid': str(uuid.uuid4()),  # Generate random UUID
    #         'note': f'POS/STI for {issue_date}',
    #         'currency_id': currency.id,
    #     })
    #     return b2c_invoice

    # def button_sale_credit_send(self):
    #     self.ensure_one()
    #     ctx = self._context
    #     print('\n\n\n\n\nctx', ctx)
    #     documents = self.env['account.move'].browse(ctx['active_ids']) if ctx.get('active_ids') else False
    #     if self.send_as_Bulk:
    #         if ctx.get('is_nonpeppol') == True:
    #             bulk_queue_ref = self.env['peppol.queue.c5.out'].create({
    #                 "invoice_ids": [(6, 0, documents.ids)],
    #                 "document_xml_type": "bulk",
    #                 "invoice_type": "out_refund",
    #             })
    #             documents.write({'outgoing_inv_doc_ref_c5': bulk_queue_ref.id})
    #             return {
    #                 'name': self.sudo().env.ref('metro_einvoice_datapost.peppol_bulk_sales_creditnote_queue_c5_action').name,
    #                 'type': 'ir.actions.act_window',
    #                 'view_mode': 'tree,form',
    #                 'view_type': 'form',
    #                 'views': [(self.env.ref('metro_einvoice_datapost.peppol_queue_c5_bulk_invoice_tree').id, 'tree'),
    #                           (self.env.ref('metro_einvoice_datapost.peppol_queue_c5_out_form').id, 'form')],
    #                 'res_model': 'peppol.queue.c5.out',
    #                 'domain': [('invoice_type','=','out_refund'),('document_xml_type','=','bulk')],
    #             }
    #         elif ctx.get('is_peppol') == True:
    #             for document in documents:
    #                 queue_ref = self.env['peppol.queue.out'].create({
    #                     'invoice_type': document.move_type,
    #                     'invoice_id': document.id
    #                 })
    #                 print('\n\n\n\nonly_pep', queue_ref)
    #                 document.write({'outgoing_inv_doc_ref': queue_ref.id})
    #             # document.write({'outgoing_inv_doc_ref': queue_ref.id, 'bulk_c5_invoice': True})
    #             return {
    #                 'name': self.sudo().env.ref('metro_einvoice_datapost.peppol_queue_out_action').name,
    #                 'type': 'ir.actions.act_window',
    #                 'view_mode': 'tree,form',
    #                 'view_type': 'form',
    #                 'res_model': 'peppol.queue.out',
    #             }
    #         elif self.is_both and not self.invoice_send_type:
    #             raise ValidationError("Please selecte at least one Type!!")
    #         elif self.is_both and self.invoice_send_type == 'non-peppol':
    #             bulk_queue_ref = self.env['peppol.queue.c5.out'].create({
    #                 "invoice_ids": [(6, 0, self.env['account.move'].browse(ctx['cus_nonpeppol_inv']).ids)],
    #                 "document_xml_type": "bulk",
    #                 "invoice_type": "out_refund",
    #             })
    #             documents.write({'outgoing_inv_doc_ref_c5': bulk_queue_ref.id})
    #             return {
    #                 'name': self.sudo().env.ref('metro_einvoice_datapost.peppol_bulk_sales_creditnote_queue_c5_action').name,
    #                 'type': 'ir.actions.act_window',
    #                 'view_mode': 'tree,form',
    #                 'view_type': 'form',
    #                 'views': [(self.env.ref('metro_einvoice_datapost.peppol_queue_c5_bulk_invoice_tree').id, 'tree'),
    #                           (self.env.ref('metro_einvoice_datapost.peppol_queue_c5_out_form').id, 'form')],
    #                 'res_model': 'peppol.queue.c5.out',
    #                 'domain': [('invoice_type','=','out_refund'),('document_xml_type','=','bulk')],
    #             }
    #         elif self.is_both and self.invoice_send_type == 'peppol':
    #             for inv in self.env['account.move'].browse(ctx['cus_peppol_inv']):
    #                 queue_ref = self.env['peppol.queue.out'].create({
    #                     'invoice_type': inv.move_type,
    #                     'invoice_id': inv.id
    #                 })
    #                 inv.write({'outgoing_inv_doc_ref': queue_ref.id})
    #             return {
    #                 'name': self.sudo().env.ref(
    #                     'metro_einvoice_datapost.peppol_queue_out_action').name,
    #                 'type': 'ir.actions.act_window',
    #                 'view_mode': 'tree,form',
    #                 'view_type': 'form',
    #                 'res_model': 'peppol.queue.out',
    #             }
    #
    #     else:
    #         if ctx.get('is_peppol') == True:
    #             for document in documents:
    #                 queue_ref = self.env['peppol.queue.out'].create({
    #                     'invoice_type': document.move_type,
    #                     'invoice_id': document.id
    #                 })
    #                 print('\n\n\n\nonly_pep', queue_ref)
    #                 document.write({'outgoing_inv_doc_ref': queue_ref.id})
    #             # document.write({'outgoing_inv_doc_ref': queue_ref.id, 'bulk_c5_invoice': True})
    #             return {
    #                 'name': self.sudo().env.ref('metro_einvoice_datapost.peppol_queue_out_action').name,
    #                 'type': 'ir.actions.act_window',
    #                 'view_mode': 'tree,form',
    #                 'view_type': 'form',
    #                 'res_model': 'peppol.queue.out',
    #             }
    #         if ctx.get('is_nonpeppol') == True:
    #             for document in documents:
    #                 queue_ref = self.env['peppol.queue.c5.out'].create({
    #                     'invoice_type': document.move_type,
    #                     'invoice_id': document.id
    #                 })
    #                 document.write({'outgoing_inv_doc_ref_c5': queue_ref.id})
    #             return {
    #                 'name': self.sudo().env.ref('metro_einvoice_datapost.peppol_sales_creditnote_queue_c5_action').name,
    #                 'type': 'ir.actions.act_window',
    #                 'view_mode': 'tree,form',
    #                 'view_type': 'form',
    #                 'res_model': 'peppol.queue.c5.out',
    #                 'domain': [('invoice_type','=','out_refund'),('document_xml_type','=','single')],
    #             }
    #         if self.is_both:
    #             if not self.invoice_send_type:
    #                 raise ValidationError("Please selecte at least one Type!!")
    #             elif self.invoice_send_type == 'peppol':
    #                 for inv in self.env['account.move'].browse(ctx['cus_peppol_inv']):
    #                     queue_ref = self.env['peppol.queue.out'].create({
    #                         'invoice_type': inv.move_type,
    #                         'invoice_id': inv.id
    #                     })
    #                     print('\n\n\n\npepboth', queue_ref)
    #                     inv.write({'outgoing_inv_doc_ref': queue_ref.id})
    #                 return {
    #                     'name': self.sudo().env.ref('metro_einvoice_datapost.peppol_queue_out_action').name,
    #                     'type': 'ir.actions.act_window',
    #                     'view_mode': 'tree,form',
    #                     'view_type': 'form',
    #                     'res_model': 'peppol.queue.out',
    #                 }
    #             elif self.invoice_send_type == 'non-peppol':
    #                 for inv in self.env['account.move'].browse(ctx['cus_nonpeppol_inv']):
    #                     queue_ref = self.env['peppol.queue.c5.out'].create({
    #                         'invoice_type': inv.move_type,
    #                         'invoice_id': inv.id
    #                     })
    #
    #                     inv.write({'outgoing_inv_doc_ref_c5': queue_ref.id})
    #                 return {
    #                     'name': self.sudo().env.ref(
    #                         'metro_einvoice_datapost.peppol_sales_creditnote_queue_c5_action').name,
    #                     'type': 'ir.actions.act_window',
    #                     'view_mode': 'tree,form',
    #                     'view_type': 'form',
    #                     'res_model': 'peppol.queue.c5.out',
    #                     'domain': [('invoice_type','=','out_refund'),('document_xml_type','=','single')],
    #                 }

