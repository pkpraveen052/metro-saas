from odoo import fields, models,_,api
from odoo.exceptions import ValidationError, UserError


class OrderReasonNoteWizard(models.TransientModel):
    _name = 'order.reason.note.wizard'
    _description = 'Order Reason Note Wizard'

    note = fields.Char('Note')
    document_type = fields.Selection([
        ('initial', 'Initial'),
        ('balance', 'Balance'),
        ('variation', 'Variation'),
        ('cancel', 'Cancel')], string="Document Type", default='order')


    def action_send(self):
        ctx = self.env.context
        # active_model = ctx.get('active_model')
        # active_id = ctx.get('active_id')
        # res_model = ''
        # view_id = ''
        # res = {}
        # print('\n\n\n\nactive_model', active_model)
        # print('\n\n\n\nactive_id', active_id)
        # print('\n\n\n\nctx', ctx)
        # if self.document_type in ['initial', 'balance', 'variation', 'cancel'] and active_model == 'order.queue.in':
        #     queue_obj = self.env[active_model].browse(active_id)
        #     res['origin'] = queue_obj.order_no
        #     res['company_id'] = queue_obj.company_id.id
        #     res['document_type'] = self.document_type
        #     if queue_obj.buyer_reference:
        #         res['client_order_ref'] = queue_obj.buyer_reference
        #     if queue_obj.requested_delivery_enddate:
        #         if not queue_obj.requested_delivery_enddate.split(" "):
        #             requested_delivery_enddate = queue_obj.requested_delivery_enddate + " 00:00:00"
        #         else:
        #             requested_delivery_enddate = queue_obj.requested_delivery_enddate
        #         res['commitment_date'] = requested_delivery_enddate
        #
        #     if queue_obj.payment_terms:
        #         pobjs = self.env['account.payment.term'].sudo().search([('name', 'ilike', queue_obj.payment_terms)],
        #                                                                limit=1)
        #         print("pobjs ==", pobjs)
        #         if pobjs:
        #             res['payment_term_id'] = pobjs.id
        #         else:
        #             res['payment_term_id'] = self.env['account.payment.term'].sudo().create(
        #                 {'name': queue_obj.payment_terms}).id
        #
        #     partner = self.env['res.partner'].search([('company_id', '=', queue_obj.company_id.id), '|',
        #                                               ('peppol_identifier', '=',
        #                                                queue_obj.extracted_senderid.split(":")[1]),
        #                                               ('peppol_identifier', 'ilike',
        #                                                queue_obj.extracted_senderid.split(":")[1])], limit=1)
        #     if partner:
        #         res['partner_id'] = partner.id
        #     else:
        #         country_obj, child_dic = False, {}
        #         if queue_obj.sender_address_country:
        #             country_obj = self.env['res.country'].search(['|', ('name', '=', queue_obj.sender_address_country),
        #                                                           ('code', '=', queue_obj.sender_address_country)],
        #                                                          limit=1)
        #         if queue_obj.sender_contact_name:
        #             child_dic = {'type': 'contact', 'name': queue_obj.sender_contact_name,
        #                          'email': queue_obj.sender_contact_email, 'phone': queue_obj.sender_contact_phone}
        #         partner = self.env['res.partner'].create({
        #             'company_type': 'company',
        #             'name': queue_obj.sender_party_name,
        #             'street': queue_obj.sender_address_line1,
        #             'street2': queue_obj.sender_address_line2,
        #             'city': queue_obj.sender_address_city,
        #             'zip': queue_obj.sender_address_zip,
        #             'country_id': country_obj and country_obj.id or False,
        #             'peppol_identifier': queue_obj.extracted_senderid.split(":")[1],
        #             'peppol_scheme': '0195',
        #             'child_ids': child_dic and [(0, 0, child_dic)] or False
        #         })
        #         res['partner_id'] = partner.id
        #
        #     delivery_contact_dic = {}
        #     if queue_obj.delivery_party_name:
        #         delivery_contact_dic = {'type': 'delivery'}
        #         if queue_obj.delivery_party_contact_name:
        #             delivery_contact_dic['name'] = queue_obj.delivery_party_contact_name
        #         else:
        #             delivery_contact_dic['name'] = queue_obj.delivery_party_name
        #
        #         country_obj = False
        #         if queue_obj.delivery_party_country:
        #             country_obj = self.env['res.country'].search(['|', ('name', '=', queue_obj.delivery_party_country),
        #                                                           ('code', '=', queue_obj.delivery_party_country)],
        #                                                          limit=1)
        #
        #         delivery_contact_dic.update({
        #             'street': queue_obj.delivery_party_street1,
        #             'street2': queue_obj.delivery_party_street2,
        #             'city': queue_obj.delivery_party_city,
        #             'zip': queue_obj.delivery_party_zip,
        #             'country_id': country_obj and country_obj.id or False,
        #             'email': queue_obj.delivery_party_contact_email,
        #             'phone': queue_obj.delivery_party_contact_phone,
        #             'parent_id': partner.id
        #         })
        #
        #     if delivery_contact_dic:
        #         delivery_contact_present = False
        #         for child in partner.sudo().child_ids.filtered(lambda x: x.type == 'delivery'):
        #             if child.name == delivery_contact_dic['name']:
        #                 delivery_contact_present = child
        #                 break;
        #         if not delivery_contact_present:
        #             delivery_contact_present = self.env['res.partner'].create(delivery_contact_dic)
        #         res['partner_shipping_id'] = delivery_contact_present.id
        #
        #     if queue_obj.validity_date:
        #         res['validity_date'] = queue_obj.validity_date
        #     payment_term = self.env['account.payment.term'].search([('name', '=', queue_obj.payment_terms)])
        #     if payment_term:
        #         res['payment_term_id'] = payment_term.id
        #     if queue_obj.note:
        #         res['note'] = queue_obj.note
        #     order_lines = []
        #     for line in queue_obj.order_line_ids:
        #         default_codes, barcodes = [], []
        #         if line.buyers_item_identification:
        #             product = self.env['product.product'].search([('company_id', '=', queue_obj.company_id.id), '|',
        #                                                           ('default_code', '=',
        #                                                            line.buyers_item_identification),
        #                                                           ('barcode', '=', line.buyers_item_identification)],
        #                                                          limit=1)
        #         elif line.sellers_item_identification:
        #             product = self.env['product.product'].search([('company_id', '=', queue_obj.company_id.id), '|',
        #                                                           ('default_code', '=',
        #                                                            line.sellers_item_identification),
        #                                                           ('barcode', '=', line.sellers_item_identification)],
        #                                                          limit=1)
        #         elif line.manufacturers_item_identification:
        #             product = self.env['product.product'].search([('company_id', '=', queue_obj.company_id.id), '|',
        #                                                           ('default_code', '=',
        #                                                            line.manufacturers_item_identification),
        #                                                           ('barcode', '=',
        #                                                            line.manufacturers_item_identification)], limit=1)
        #         elif line.standard_item_identification:
        #             product = self.env['product.product'].search([('company_id', '=', queue_obj.company_id.id), '|',
        #                                                           ('default_code', '=',
        #                                                            line.standard_item_identification),
        #                                                           ('barcode', '=', line.standard_item_identification)],
        #                                                          limit=1)
        #         elif line.item_classification_identifier:
        #             product = self.env['product.product'].search([('company_id', '=', queue_obj.company_id.id), '|',
        #                                                           ('default_code', '=',
        #                                                            line.item_classification_identifier),
        #                                                           ('barcode', '=',
        #                                                            line.item_classification_identifier)], limit=1)
        #         else:
        #             product = self.env['product.product'].search(
        #                 [('company_id', '=', queue_obj.company_id.id), '|', ('name', '=', line.name),
        #                  ('name', 'ilike', line.name)], limit=1)
        #
        #         order_line_values = {
        #             'product_id': product.id if product else False,
        #             'name': line.description or line.name,
        #             'product_uom_qty': line.quantity,
        #             'price_unit': line.price_amount,
        #             # 'date_planned': line.create_date,
        #             # 'price_subtotal': line.amount_excluding_tax,
        #             # 'product_uom': product.uom_id.id if product and product.uom_id else False,
        #             'incoming_order_line_id': line.id,
        #             'tax_id': False
        #         }
        #         print('\n\n\n\norder_line_values', order_line_values)
        #         if line.unit_code:
        #             uom_obj = self.env['uom.uom'].sudo().search([('unece_code', '=', line.unit_code)], limit=1)
        #             if uom_obj:
        #                 order_line_values.update({'product_uom': uom_obj.id})
        #             else:
        #                 raise ValidationError(
        #                     "Please configure '" + str(line.unit_code) + "' in Units of Measure master list.")
        #
        #         discount = (line.quantity * line.price_amount) - line.amount_excluding_tax
        #         if discount > 0.0:
        #             discount_percentage = (discount / (line.quantity * line.price_amount)) * 100
        #             order_line_values.update({'discount': discount_percentage})
        #         order_lines.append((0, 0, order_line_values))
        #
        #     res['order_line'] = order_lines
        #     print('\n\nres', res)
        #     so_id = self.env['sale.order'].create(res)
        #     for orderline in so_id.order_line:
        #         if orderline.incoming_order_line_id.tax_category_code:
        #                 tax_obj = self.env['account.tax'].sudo().search([('company_id','=',so_id.company_id.id), ('type_tax_use','=','sale'), ('amount','=',orderline.incoming_order_line_id.tax_percentage)], limit=1)
        #                 print("tax_obj ==",tax_obj)
        #                 if tax_obj and tax_obj.unece_categ_id:
        #                     orderline.tax_id = [(6,0,[tax_obj.id])]
        #                 else:
        #                     raise ValidationError("The Tax Category Code are not configured with the Taxes %s." % (tax_obj.name))
        #         else:
        #             orderline.write({'tax_id': False})
        #             print("orderline.tax_id ==",orderline.tax_id)
        #         if not so_id.partner_id.peppol_identifier:
        #             raise ValidationError("Peppol Identifier for Customer %s is not defined." % (so_id.partner_id.name))
        #         sender_peppol_id = queue_obj.extracted_senderid.split(":")[1]
        #         if so_id.partner_id.peppol_identifier.lower() != sender_peppol_id.lower():
        #             raise ValidationError("Customer's Peppol identifier does not match. Mapping cannot be allowed.")
        #         mapped_orderlines = []
        #         print('\n\n\nqueue_obj', queue_obj)
        #         for line in queue_obj.order_line_ids:
        #             for orderline in so_id.order_line:
        #                 if line.quantity == orderline.product_uom_qty and line.price_amount == orderline.price_unit and line.id not in mapped_orderlines:
        #                     mapped_orderlines.append(orderline.id)
        #         if len(mapped_orderlines) != len(queue_obj.order_line_ids.ids):
        #             raise ValidationError("The Order lines does not match. Mapping cannot be allowed.")
        #         print("obj.amount_untaxed ==",so_id.amount_untaxed)
        #         print("obj.amount_total ==",so_id.amount_total)
        #         print("queue_obj.amt_untaxed ==",queue_obj.amt_untaxed)
        #         if so_id.amount_untaxed != queue_obj.amt_untaxed and self.document_type == 'order':
        #             raise ValidationError("The Total Untaxed Amount does not match. Mapping cannot be allowed.")
        #         # if so_id.amount_total != queue_obj.amt_including_tax and self.document_type == 'order':
        #         #     raise ValidationError("The Total Amount does not match. Mapping cannot be allowed.")
        #         queue_obj.write({
        #             'so_id': so_id.id,
        #             'message': "Sale Order mapped successfully!",
        #             'state': 'success'})
        #
        #         if queue_obj.payment_terms and not so_id.payment_term_id:
        #             pobjs = self.env['account.payment.term'].sudo().search([('name', 'ilike', queue_obj.payment_terms)], limit=1)
        #             print("pobjs ==",pobjs)
        #             if pobjs:
        #                 so_id.write({'payment_term_id': pobjs.id})
        #             else:
        #                 so_id.payment_term_id = self.env['account.payment.term'].sudo().create({'name': queue_obj.payment_terms}).id
        #         if queue_obj.note:
        #             so_id.note = so_id.note +'\n'+ queue_obj.note
        #     print('\n\nso_id', so_id)
        #     return {
        #         'name': _('Sale Order'),
        #         'type': 'ir.actions.act_window',
        #         'res_model': 'sale.order',
        #         'view_mode': 'form',
        #         'view_type': 'form',
        #         'res_id': so_id.id,
        #         'target': 'current',  # or 'new' to open in popup
        #     }

            # res_model = 'order.queue.out'
            # view_id = 'metro_einvoice_datapost.order_queue_out_action'
        # if self.document_type == 'balance':
        #     res_model = 'order.balance.queue.out'
        #     view_id = 'metro_einvoice_datapost.order_balance_queue_out_action'
        # if self.document_type == 'variation':
        #     res_model = 'order.change.queue.out'
        #     view_id = 'metro_einvoice_datapost.order_change_queue_out_action'
        # if self.document_type == 'cancel':
        #     res_model = 'order.cancel.queue.out'
        #     view_id = 'metro_einvoice_datapost.order_cancel_queue_out_action'

        # PRINT FOR DEBUG
        active_model = ctx.get('active_model')
        active_id = ctx.get('active_id')
        if self.document_type in ['initial', 'balance', 'variation', 'cancel'] and active_model == 'purchase.order':
            Queue = self.env['order.queue.out']
            po_id = self.env['purchase.order'].browse(active_id)
            queue_ref = Queue._add_to_queue(po_id, self.document_type)
            po_id.write({'order_note': self.note, 'outgoing_order_doc_ref': queue_ref.id})
            # if res_model == 'order.change.queue.out':
            #     po_id.write({'outgoing_order_change_doc_ref': queue_ref.id})
            # if res_model == 'order.balance.queue.out':
            #     po_id.write({'outgoing_order_balance_doc_ref': queue_ref.id})
            # if res_model == 'order.cancel.queue.out':
            #     po_id.write({'outgoing_order_cancel_doc_ref': queue_ref.id})
            return {
                'name': self.sudo().env.ref('metro_einvoice_datapost.order_queue_out_action').name,
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'order.queue.out',
                'domain': [('id', '=', queue_ref.id)]
            }
