# -*- coding: utf-8 -*-
import base64
import traceback
from lxml import etree
import logging
import requests
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_round
from datetime import date, datetime, time
import json
from odoo.exceptions import ValidationError, UserError
import re

logger = logging.getLogger(__name__)

TIMEOUT = 20

class SaleOrder(models.Model):
    _inherit = "sale.order"

    document_type = fields.Selection([
        ('initial', 'Initial'),
        ('balance', 'Balance'),
        ('variation', 'Variation'),
        ('cancel', 'Cancel')], string="Document Type", default='initial')
    outgoing_order_change_doc_ref = fields.Many2one('order.change.queue.out',
                                                    string="Peppol Outgoing Document Change Ref", copy=False)
    outgoing_order_cancel_doc_ref = fields.Many2one('order.cancel.queue.out',
                                                    string="Peppol Outgoing Document Cancel Ref", copy=False)
    outgoing_order_balance_doc_ref = fields.Many2one('order.balance.queue.out',
                                                     string="Peppol Outgoing Document Balance Ref", copy=False)
    incoming_order_id = fields.Many2one("order.queue.in", string="Peppol Incoming Document Ref", readonly=True)

    # @api.model
    # def default_get(self, fields):
    #     res = super(SaleOrder, self).default_get(fields)
    #     ctx = self._context or {}
    #     active_model = ctx.get('active_model')
    #     active_id = ctx.get('active_id')
    #     if active_model and active_id and active_model in ('order.queue.in', 'order.change.in', 'order.balance.in'):
    #         queue_obj = self.env[active_model].browse(active_id)
    #         res['origin'] = queue_obj.order_no
    #         res['company_id'] = queue_obj.company_id.id
    #         if queue_obj.buyer_reference:
    #             res['client_order_ref'] = queue_obj.buyer_reference
    #         if queue_obj.requested_delivery_enddate:
    #             if not queue_obj.requested_delivery_enddate.split(" "):
    #                 requested_delivery_enddate = queue_obj.requested_delivery_enddate + " 00:00:00"
    #             else:
    #                 requested_delivery_enddate = queue_obj.requested_delivery_enddate
    #             res['commitment_date'] = requested_delivery_enddate
    #
    #         if queue_obj.payment_terms:
    #             pobjs = self.env['account.payment.term'].sudo().search([('name', 'ilike', queue_obj.payment_terms)], limit=1)
    #             print("pobjs ==",pobjs)
    #             if pobjs:
    #                 res['payment_term_id'] = pobjs.id
    #             else:
    #                 res['payment_term_id'] = self.env['account.payment.term'].sudo().create({'name': queue_obj.payment_terms}).id
    #
    #
    #         partner = self.env['res.partner'].search([('company_id','=',queue_obj.company_id.id),'|',('peppol_identifier', '=', queue_obj.extracted_senderid.split(":")[1]),
    #             ('peppol_identifier', 'ilike', queue_obj.extracted_senderid.split(":")[1])], limit=1)
    #         if partner:
    #             res['partner_id'] = partner.id
    #         else:
    #             country_obj, child_dic = False, {}
    #             if queue_obj.sender_address_country:
    #                 country_obj = self.env['res.country'].search(['|',('name','=',queue_obj.sender_address_country), ('code','=',queue_obj.sender_address_country)], limit=1)
    #             if queue_obj.sender_contact_name:
    #                 child_dic = {'type': 'contact', 'name': queue_obj.sender_contact_name, 'email': queue_obj.sender_contact_email, 'phone': queue_obj.sender_contact_phone}
    #             partner = self.env['res.partner'].create({
    #                 'company_type': 'company',
    #                 'name': queue_obj.sender_party_name,
    #                 'street': queue_obj.sender_address_line1,
    #                 'street2': queue_obj.sender_address_line2,
    #                 'city':queue_obj.sender_address_city,
    #                 'zip': queue_obj.sender_address_zip,
    #                 'country_id': country_obj and country_obj.id or False,
    #                 'peppol_identifier': queue_obj.extracted_senderid.split(":")[1],
    #                 'peppol_scheme': '0195',
    #                 'child_ids': child_dic and [(0,0,child_dic)] or False
    #                 })
    #             res['partner_id'] = partner.id
    #
    #         delivery_contact_dic = {}
    #         if queue_obj.delivery_party_name:
    #             delivery_contact_dic = {'type': 'delivery'}
    #             if queue_obj.delivery_party_contact_name:
    #                 delivery_contact_dic['name'] = queue_obj.delivery_party_contact_name
    #             else:
    #                 delivery_contact_dic['name'] = queue_obj.delivery_party_name
    #
    #             country_obj = False
    #             if queue_obj.delivery_party_country:
    #                 country_obj = self.env['res.country'].search(['|',('name','=',queue_obj.delivery_party_country), ('code','=',queue_obj.delivery_party_country)], limit=1)
    #
    #             delivery_contact_dic.update({
    #                 'street': queue_obj.delivery_party_street1,
    #                 'street2': queue_obj.delivery_party_street2,
    #                 'city': queue_obj.delivery_party_city,
    #                 'zip': queue_obj.delivery_party_zip,
    #                 'country_id': country_obj and country_obj.id or False,
    #                 'email': queue_obj.delivery_party_contact_email,
    #                 'phone': queue_obj.delivery_party_contact_phone,
    #                 'parent_id': partner.id
    #                 })
    #
    #         if delivery_contact_dic:
    #             delivery_contact_present = False
    #             for child in partner.sudo().child_ids.filtered(lambda x: x.type == 'delivery'):
    #                 if child.name == delivery_contact_dic['name']:
    #                     delivery_contact_present = child
    #                     break;
    #             if not delivery_contact_present:
    #                 delivery_contact_present = self.env['res.partner'].create(delivery_contact_dic)
    #             res['partner_shipping_id'] = delivery_contact_present.id
    #
    #         if queue_obj.validity_date:
    #             res['validity_date'] = queue_obj.validity_date
    #         payment_term = self.env['account.payment.term'].search([('name','=',queue_obj.payment_terms)])
    #         if payment_term:
    #             res['payment_term_id'] = payment_term.id
    #         if queue_obj.note:
    #             res['note'] = queue_obj.note
    #         order_lines = []
    #         for line in queue_obj.order_line_ids:
    #             default_codes, barcodes = [], []
    #             if line.buyers_item_identification:
    #                 product = self.env['product.product'].search([('company_id','=',queue_obj.company_id.id),'|',('default_code', '=', line.buyers_item_identification), ('barcode', '=', line.buyers_item_identification)], limit=1)
    #             elif line.sellers_item_identification:
    #                 product = self.env['product.product'].search([('company_id','=',queue_obj.company_id.id),'|',('default_code', '=', line.sellers_item_identification), ('barcode', '=', line.sellers_item_identification)], limit=1)
    #             elif line.manufacturers_item_identification:
    #                 product = self.env['product.product'].search([('company_id','=',queue_obj.company_id.id),'|',('default_code', '=', line.manufacturers_item_identification), ('barcode', '=', line.manufacturers_item_identification)], limit=1)
    #             elif line.standard_item_identification:
    #                 product = self.env['product.product'].search([('company_id','=',queue_obj.company_id.id),'|',('default_code', '=', line.standard_item_identification), ('barcode', '=', line.standard_item_identification)], limit=1)
    #             elif line.item_classification_identifier:
    #                 product = self.env['product.product'].search([('company_id','=',queue_obj.company_id.id),'|',('default_code', '=', line.item_classification_identifier), ('barcode', '=', line.item_classification_identifier)], limit=1)
    #             else:
    #                 product = self.env['product.product'].search([('company_id','=',queue_obj.company_id.id),'|',('name', '=', line.name), ('name', 'ilike', line.name)], limit=1)
    #
    #             order_line_values = {
    #                 'product_id': product.id if product else False,
    #                 'name': line.description or line.name,
    #                 'product_uom_qty': line.quantity,
    #                 'price_unit': line.price_amount,
    #                 # 'date_planned': line.create_date,
    #                 # 'price_subtotal': line.amount_excluding_tax,
    #                 # 'product_uom': product.uom_id.id if product and product.uom_id else False,
    #                 'incoming_order_line_id': line.id,
    #                 'tax_id': False
    #             }
    #             if line.unit_code:
    #                 uom_obj = self.env['uom.uom'].sudo().search([('unece_code','=',line.unit_code)], limit=1)
    #                 if uom_obj:
    #                     order_line_values.update({'product_uom': uom_obj.id})
    #                 else:
    #                     raise ValidationError("Please configure '" + str(line.unit_code) + "' in Units of Measure master list.")
    #
    #             discount = (line.quantity * line.price_amount) - line.amount_excluding_tax
    #             if discount > 0.0:
    #                 discount_percentage = (discount / (line.quantity * line.price_amount)) * 100
    #                 order_line_values.update({'discount': discount_percentage})
    #             order_lines.append((0, 0, order_line_values))
    #
    #         res['order_line'] = order_lines
    #         print("res ===",res)
    #     return res

    def map_to_incoming_order(self):
        ctx = self._context
        self.ensure_one()
        active_model = ctx.get('active_model')
        active_id = ctx.get('active_id')
        queue_obj = self.env[active_model].browse(active_id)
        if queue_obj and active_model in ('order.queue.in', 'order.change.in', 'order.balance.in'):
            # queue_obj = self.env['order.queue.in'].browse(ctx['active_id'])
            if not self.partner_id.peppol_identifier:
                raise ValidationError("Peppol Identifier for Customer %s is not defined." % (self.partner_id.name))
            sender_peppol_id = queue_obj.extracted_senderid.split(":")[1]
            if self.partner_id.peppol_identifier.lower() != sender_peppol_id.lower():
                raise ValidationError("Customer's Peppol identifier does not match. Mapping cannot be allowed.")
            mapped_orderlines = []
            for line in queue_obj.order_line_ids:
                for orderline in self.order_line:
                    if line.quantity == orderline.product_uom_qty and line.price_amount == orderline.price_unit and line.id not in mapped_orderlines:
                        mapped_orderlines.append(orderline.id)
            if len(mapped_orderlines) != len(queue_obj.order_line_ids.ids):
                raise ValidationError("The Order lines does not match. Mapping cannot be allowed.")                 
            if self.amount_untaxed != queue_obj.amt_untaxed:
                raise ValidationError("The Total Untaxed Amount does not match. Mapping cannot be allowed.")
            if self.amount_total != queue_obj.amt_including_tax:
                raise ValidationError("The Total Amount does not match. Mapping cannot be allowed.")
            queue_obj.write({
                'so_id': self.id,
                'state': 'success',
                'message': 'Sale Order mapped Successfully!',
            })
            if active_model == 'order.queue.in':
                return {
                    'type': 'ir.actions.act_url',
                    'url': "/web#id=" + str(queue_obj.id) + "&action=" + str(self.env.ref(
                        'metro_einvoice_datapost.action_order_queue_in_view').id) + "&model=order.queue.in&view_type=form&cids=&menu_id=" + str(
                        self.env.ref('metro_einvoice_datapost.menu_sub_order_queue_in').id)
                }
            elif active_model == 'order.balance.in':
                return {
                    'type': 'ir.actions.act_url',
                    'url': "/web#id=" + str(queue_obj.id) + "&action=" + str(self.env.ref(
                        'metro_einvoice_datapost.action_order_balance_in_view').id) + "&model=order.balance.in&view_type=form&cids=&menu_id=" + str(
                        self.env.ref('metro_einvoice_datapost.menu_order_balance_in').id)
                }
            elif active_model == 'order.change.in':
                return {
                    'type': 'ir.actions.act_url',
                    'url': "/web#id=" + str(queue_obj.id) + "&action=" + str(self.env.ref(
                        'metro_einvoice_datapost.action_order_change_in_view').id) + "&model=order.change.in&view_type=form&cids=&menu_id=" + str(
                        self.env.ref('metro_einvoice_datapost.menu_sub_order_change_in').id)
                }

    # @api.model
    # def create(self, vals):
    #     ctx = self._context
    #     print(ctx)
    #     active_model = ctx.get('active_model')
    #     active_id = ctx.get('active_id')
    #     obj =  super(SaleOrder, self).create(vals)
    #     if active_model and active_id and active_model in ('order.queue.in', 'order.change.in', 'order.balance.in'):
    #         queue_obj = self.env[active_model].browse(active_id)
    #         for orderline in obj.order_line:
    #             if orderline.incoming_order_line_id.tax_category_code:
    #                 tax_obj = self.env['account.tax'].sudo().search([('company_id','=',obj.company_id.id), ('type_tax_use','=','sale'), ('amount','=',orderline.incoming_order_line_id.tax_percentage), ()], limit=1)
    #                 print("tax_obj ==",tax_obj)
    #                 if tax_obj and tax_obj.unece_categ_id:
    #                     orderline.tax_id = [(6,0,[tax_obj.id])]
    #                 else:
    #                     raise ValidationError("The Tax Category Code are not configured with the Taxes %s." % (tax_obj.name))
    #             else:
    #                 orderline.write({'tax_id': False})
    #             print("orderline.tax_id ==",orderline.tax_id)
    #         if not obj.partner_id.peppol_identifier:
    #             raise ValidationError("Peppol Identifier for Customer %s is not defined." % (obj.partner_id.name))
    #         sender_peppol_id = queue_obj.extracted_senderid.split(":")[1]
    #         if obj.partner_id.peppol_identifier.lower() != sender_peppol_id.lower():
    #             raise ValidationError("Customer's Peppol identifier does not match. Mapping cannot be allowed.")
    #         mapped_orderlines = []
    #         print('\n\n\nqueue_obj', queue_obj)
    #         for line in queue_obj.order_line_ids:
    #             for orderline in obj.order_line:
    #                 if line.quantity == orderline.product_uom_qty and line.price_amount == orderline.price_unit and line.id not in mapped_orderlines:
    #                     mapped_orderlines.append(orderline.id)
    #         if len(mapped_orderlines) != len(queue_obj.order_line_ids.ids):
    #             raise ValidationError("The Order lines does not match. Mapping cannot be allowed.")
    #         print("obj.amount_untaxed ==",obj.amount_untaxed)
    #         print("obj.amount_total ==",obj.amount_total)
    #         print("queue_obj.amt_untaxed ==",queue_obj.amt_untaxed)
    #         if obj.amount_untaxed != queue_obj.amt_untaxed:
    #             raise ValidationError("The Total Untaxed Amount does not match. Mapping cannot be allowed.")
    #         if obj.amount_total != queue_obj.amt_including_tax:
    #             raise ValidationError("The Total Amount does not match. Mapping cannot be allowed.")
    #         queue_obj.write({
    #             'so_id': obj.id,
    #             'message': "Sale Order mapped successfully!",
    #             'state': 'success'})
    #
    #         if queue_obj.payment_terms and not obj.payment_term_id:
    #             pobjs = self.env['account.payment.term'].sudo().search([('name', 'ilike', queue_obj.payment_terms)], limit=1)
    #             print("pobjs ==",pobjs)
    #             if pobjs:
    #                 obj.write({'payment_term_id': pobjs.id})
    #             else:
    #                 obj.payment_term_id = self.env['account.payment.term'].sudo().create({'name': queue_obj.payment_terms}).id
    #         if queue_obj.note:
    #             obj.note = obj.note +'\n'+ queue_obj.note
    #     return obj


    def action_send_orders(self):
        print('\n\nself', self)
        res_model = ''
        view_id = ''
        if self.document_type == 'balance':
            res_model = 'order.balance.queue.out'
            view_id = 'metro_einvoice_datapost.order_balance_queue_out_action'
        if self.document_type == 'variation':
            res_model = 'order.change.queue.out'
            view_id = 'metro_einvoice_datapost.order_change_queue_out_action'
        if self.document_type == 'cancel':
            res_model = 'order.cancel.queue.out'
            view_id = 'metro_einvoice_datapost.order_cancel_queue_out_action'

        Queue = self.env[res_model]
        print('\n\n\n\nQueue', Queue)
        queue_ref = Queue._add_to_queue(self)
        if res_model == 'order.queue.out':
            self.write({'outgoing_order_doc_ref': queue_ref.id})
        if res_model == 'order.change.queue.out':
            self.write({'outgoing_order_change_doc_ref': queue_ref.id})
        if res_model == 'order.balance.queue.out':
            self.write({'outgoing_order_balance_doc_ref': queue_ref.id})
        if res_model == 'order.cancel.queue.out':
            self.write({'outgoing_order_cancel_doc_ref': queue_ref.id})
        return {
            'name': self.sudo().env.ref(view_id).name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': res_model,
            'domain': [('id', '=', queue_ref.id)]
        }

    def _create_invoices(self, grouped=False, final=False, date=None):
        # 1️⃣ Call original Odoo logic
        invoices = super(SaleOrder, self)._create_invoices(
            grouped=grouped,
            final=final,
            date=date
        )
        if self and len(self) == 1:
            for invoice in invoices:
                if self.incoming_order_id and self.partner_id.is_sg_government_customer:
                    if not self.incoming_order_id.buyer_reference:
                        raise ValidationError(
                            "Business Unit (Buyer Reference) is mandatory for "
                            "Singapore Government invoices."
                        )
                    business_unit = self.env['ministries.statuary.boards'].search(
                        [('business_unit_code', '=', self.incoming_order_id.buyer_reference)],
                        limit=1
                    )
                    invoice.business_unit_id = business_unit.id
                if self.partner_id.child_ids:
                    contact = self.partner_id.child_ids.filtered(lambda x: x.type == 'contact')
                    if contact:
                        contact = contact[0]
                        invoice.customer_contact_person = contact.name

                if self.incoming_order_id:
                    for line in self.incoming_order_id.order_line_ids:
                        inv_line = invoice.invoice_line_ids.filtered(
                            lambda l: l.product_id.name == line.name or l.name == line.name
                        )
                        if inv_line:
                            inv_line.line_item_id = line.line_item_id
                invoice.sale_order_id = self.id
                invoice.vendor_id = self.company_id.partner_id.id
                invoice.supplier_email_address = self.company_id.partner_id.email
                invoice.note = self.note
                invoice.order_ref = self.incoming_order_id.order_reference
        return invoices

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    incoming_order_line_id = fields.Many2one('incoming.order.lines')
    # incoming_order_line_id = fields.Many2one('incoming.balance.order.lines')
    # incoming_order_line_id = fields.Many2one('incoming.change.order.lines')
