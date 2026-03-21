from odoo import fields, models, api, _
import requests
from requests import ConnectionError
import json
import traceback
import logging

_logger = logging.getLogger(__name__)

SELECTION_PEPPOL_LOG_SG_STATE = [
    ('success', 'Mapped'),
    ('sent_to_process', 'Unmapped'),
    ('error', 'Failed'),
    ('cancelled', 'Cancelled')
]


class PeppolLogSG(models.Model):
    _name = "peppol.log.sg"
    _description = "Document Incoming"
    _rec_name = "invoice_no"
    _order = "create_date desc"
    _inherit = ['mail.thread']

    invoice_no = fields.Char(string="Invoice Ref", readonly=True, tracking=True)
    message = fields.Text(string="Message", readonly=True, tracking=True)
    subtype = fields.Selection(SELECTION_PEPPOL_LOG_SG_STATE, string="Status", readonly=True, tracking=True)
    guid = fields.Char('GUID', readonly=True, help="Globally Unique Identifier", tracking=True)
    error_type = fields.Selection([('partner', 'Partner'), ('product', 'Product'), ('tax', 'Tax')])
    po_id = fields.Many2one('purchase.order', string="Purchase Order", readonly=True)

    sender_party_name = fields.Char("Vendor")
    sender_address_line1 = fields.Char("Vendor Address Line 1")
    sender_address_line2 = fields.Char("Vendor Address Line 2")
    sender_address_city = fields.Char("Vendor City")
    sender_address_county = fields.Char("Vendor County")
    sender_address_zip = fields.Char("Vendor Zip")
    sender_address_country = fields.Char("Vendor Country")
    sender_peppol_identifiers = fields.Text("Vendor Peppol Identifer")

    invoice_number = fields.Char("Invoice Number")
    legal_entity_id = fields.Char("Legal Entity ID", help="The id of the LegalEntity the invoice was received for")
    issue_date = fields.Date("Issue Date")
    tax_point_date = fields.Date("Tax Point Date")
    due_date = fields.Date("Due Date")
    document_currency_code = fields.Char("Currency Code", help="The ISO 4217 currency for the invoice.")
    source = fields.Char("Source")

    invoice_type = fields.Char("Invoice Type")
    period_start = fields.Date("Period Start", help="The start date of the period this invoice relates to")
    period_end = fields.Date("Period End", help="The end date of the period this invoice relates to")
    buyer_reference = fields.Char("Buyer Reference", help="Reference provided by the buyer. Used for routing")
    billing_reference = fields.Char("Billing Reference",
                                    help="Reference to the previous invoice this invoice relates to.")
    order_reference = fields.Char("Order Reference",
                                  help="Reference to the order. Used for matching the invoice to an order")

    payment_means_account = fields.Char("Payment Means Account", help="The account number to which to transfer")
    payment_means_branch_code = fields.Char("Payment Means Branch Code")
    payment_means_holder = fields.Char("Payment Means Holder", help="The account holder name to which to transfer")
    payment_means_mandate = fields.Char("Payment Means Mandate",
                                        help="The mandate, used only for type DirectDebitPaymentMean")
    payment_means_network = fields.Char("Payment Means Network",
                                        help="The payment network. Used only for type CardPaymentType")
    payment_means_payment_id = fields.Char("Payment Means Payment ID",
                                           help="The payment id to use when making the payment. The invoice sender will use this to match the received funds to the invoice")
    payment_means_type = fields.Char("Payment Means Type", help="The type of payment means.")

    note = fields.Text("Note")

    json_data = fields.Text("JSON Data")
    invoice_line_ids = fields.One2many("incoming.invoice.lines", "parent_id", "Invoice Lines")

    company_id = fields.Many2one("res.company", string="Company")
    currency_id = fields.Many2one("res.currency", string="Currency")
    amt_including_tax = fields.Float("Total(Inc. tax)")

    document_ids = fields.Many2many(
        'ir.attachment', 'unmapped_inv_docs_docs_rel', 'peppol_log_id', 'attachment_id',
        string='Received Documents')
    error_exception = fields.Text("Technical Error")
    billing_first_name = fields.Char(string="Billing Contact")
    billing_last_name = fields.Char(string="Billing Last Name")
    email = fields.Char(string="Email")

    @api.model
    def create(self, vals):
        """It sends either Email or Notification to the particular users at the time of creating Incoming Invoice."""
        obj = super(PeppolLogSG, self).create(vals)
        if obj.subtype in ['sent_to_process', 'error']:
            groups = self.env['ir.config_parameter'].sudo().get_param('peppol_notification_grp_ids', default=False)
            domain = [('groups_id', 'in', eval(groups))]
            if obj.company_id:
                domain += [('company_ids', 'in', [obj.company_id.id])]
            for user in self.env['res.users'].sudo().search(domain):
                if user.notification_type == 'email':
                    template_obj = self.env.ref('account_peppol_sg.incoming_invoice_document_notification')
                    action_id = self.env.ref('account_peppol_sg.action_pepppol_log_sg_view').id
                    template_obj.with_context(
                        {'email_to': user.email, 'document_id': obj.id, 'action_id': action_id}).send_mail(obj.id,
                                                                                                           force_send=False)
                elif user.notification_type == 'inbox':
                    body = _('Hi<br/>New e-Invoice <b>%s</b> received with status ') % (obj.invoice_no)
                    if obj.subtype == 'success':
                        body += _('<b>Mapped.</b>')
                    elif obj.subtype == 'sent_to_process':
                        body += _('<b>Unmapped.</b>')
                    elif obj.subtype == 'error':
                        body += _('<b>Failed.</b>')
                    if obj.po_id:
                        body += _('<br/><p>Invoice Mapped to the PO <b>%s</b>.</p>') % (obj.po_id.name)
                    obj.message_post(body=body,
                                     message_type="notification",
                                     subtype_xmlid="mail.mt_comment",
                                     notify_by_email=False,
                                     partner_ids=[user.partner_id.id])
        return obj

    def action_view_orders(self):
        """ List all the Purchase Orders and displays the 'Map' button."""
        return {
            'name': _('Purchase Orders'),
            'view_mode': 'tree,form',
            'views': [(self.env.ref('account_peppol_sg.purchase_order_peppol_mapping_list').id, 'tree'),
                      (self.env.ref('purchase.purchase_order_form').id, 'form')],
            'search_view_id': self.env.ref('purchase.view_purchase_order_filter').id,
            'res_model': 'purchase.order',
            'context': {'invoice_map_id': self.id},
            'type': 'ir.actions.act_window',
        }

    def action_suggestion(self):
        return False

    def get_endpoint(self):
        params = self.env['ir.config_parameter'].sudo()
        endpoint = params.get_param('endpoint', default=False)
        token = params.get_param('apikey', default=False)
        if not endpoint or not token:
            return
        return requests.get("{}purchase_invoices/{}".format(endpoint, self.guid),
                            headers={'Content-type': 'application/json;charset=UTF-8',
                                     'Authorization': 'Bearer {}'.format(token)})

    def action_create_record(self):
        response = self.get_endpoint()
        if response.status_code == 200:
            data = response.json()
            for rec in self:
                if rec.error_type == 'partner':
                    sender_dict = list(data.get('sender').values())[9]
                    res_partner_id = self.env['res.partner'].search(
                        [('peppol_identifier', '=', list(sender_dict.values())[2])], limit=1)
                    if not res_partner_id:
                        return {
                            'name': _('Partner'),
                            'view_mode': 'form',
                            'view_id': self.env.ref('base.view_partner_form').id,
                            'res_model': 'res.partner',
                            'context': {'default_name': list(data.get('sender').values())[0],
                                        'default_peppol_identifier': list(sender_dict.values())[2],
                                        'default_peppol_scheme': list(sender_dict.values())[1]},
                            'type': 'ir.actions.act_window',
                            'target': 'self',
                        }
                elif rec.error_type == 'product':
                    for product in data.get('invoice_lines'):
                        product_id = self.env['product.product'].search([('name', '=', product.get('name'))])
                        if not product_id:
                            return {
                                'name': _('Product'),
                                'view_mode': 'form',
                                'view_id': self.env.ref('product.product_template_only_form_view').id,
                                'res_model': 'product.product',
                                'context': {'default_name': product.get('name')},
                                'type': 'ir.actions.act_window',
                                'target': 'self',
                            }
                elif rec.error_type == 'tax':
                    for product in data.get('invoice_lines'):
                        invoice_tax = self.env['account.tax'].search(
                            [('unece_categ_id.code', '=', list(product.get('tax').values())[4])])
                        type_obj = self.env['unece.code.list'].search(
                            [('code', '=', list(product.get('tax').values())[5])])
                        categ_obj = self.env['unece.code.list'].search(
                            [('code', '=', list(product.get('tax').values())[4])])
                        if not invoice_tax:
                            return {
                                'name': _('Tax'),
                                'view_mode': 'form',
                                'view_id': self.env.ref('account.view_tax_form').id,
                                'res_model': 'account.tax',
                                'context': {'default_name': "GST 7%", 'default_unece_type_id': type_obj.id,
                                            'default_unece_categ_id': categ_obj.id},
                                'type': 'ir.actions.act_window',
                                'target': 'self',
                            }

    def action_verify_list(self):
        for rec in self:
            if rec.error_type == 'partner':
                return {
                    'name': _('Partner'),
                    'view_mode': 'tree',
                    'view_id': self.env.ref('base.view_partner_tree').id,
                    'res_model': 'res.partner',
                    'type': 'ir.actions.act_window',
                    'target': 'self',
                }
            elif rec.error_type == 'product':
                return {
                    'name': _('Product'),
                    'view_mode': 'tree',
                    'view_id': self.env.ref('product.product_product_tree_view').id,
                    'res_model': 'product.product',
                    'type': 'ir.actions.act_window',
                    'target': 'self',
                }
            elif rec.error_type == 'tax':
                return {
                    'name': _('Tax'),
                    'view_mode': 'tree',
                    'view_id': self.env.ref('account.view_tax_tree').id,
                    'res_model': 'account.tax',
                    'type': 'ir.actions.act_window',
                    'target': 'self',
                }

    def action_retry(self):
        """This method is used to retry and get record in peppol_log master."""
        error_codes = {
            401: '401 Unauthorized',
            403: '403 Forbidden',
            404: '404 Not Found'
        }
        try:
            if self.guid:
                response = self.get_endpoint()
                if response.status_code == 200:
                    data = response.json()
                    account_invoice = self.peppol_parsing_invoice(data)
                    if account_invoice:
                        self.update(account_invoice)
                        if account_invoice.get('po_id', False):
                            # Email Notification to Purchase Order Representative
                            template_obj = self.env.ref('account_peppol_sg.incoming_invoice_mapped_notification')
                            action_id = self.env.ref('account_peppol_sg.action_pepppol_log_sg_view').id
                            template_obj.with_context({'document_id': self.id, 'action_id': action_id}).send_mail(
                                account_invoice['po_id'], force_send=False)
                elif response.status_code in error_codes.keys():
                    self.update({
                        'subtype': 'error',
                        'message': error_codes[response.status_code],
                    })
                else:
                    self.update({
                        'subtype': 'error',
                        'message': "Unknown Error",
                    })
        except Exception as e:
            self.update({
                'subtype': 'error',
                'message': 'Critical Error.\nFor more details read the Technical tab.',
                'error_exception': repr(e) + "\nTraceback::" + traceback.format_exc(),
            })

    def action_cancel(self):
        """ This method will set the subtype as cancelled. """
        self.write({'subtype': 'cancelled'})

    def _delete_webhookinstance(self, guid, endpoint, token):
        headers = {
            'Content-type': 'application/json;charset=UTF-8',
            'Authorization': 'Bearer {}'.format(token)
        }
        url = "{}webhook_instances/{}".format(endpoint, guid)
        response = requests.delete(url, headers=headers)
        return response.status_code

    def create_unmapped_invoice_doc(self, data):
        currency_obj = self.env['res.currency'].sudo().search([('name', '=', data.get('document_currency_code'))],
                                                              limit=1)
        unmapped_vals = {
            'invoice_no': data.get('invoice_number'),
            'invoice_type': data.get('invoice_type'),
            'issue_date': data.get('issue_date'),
            'due_date': data.get('due_date'),
            'tax_point_date': data.get('tax_point_date', False),
            'document_currency_code': data.get('document_currency_code'),
            'currency_id': currency_obj.id,
            'period_start': data.get('period_start'),
            'period_end': data.get('period_end'),
            'buyer_reference': data.get('buyer_reference'),
            'billing_reference': data.get('billing_reference'),
            'order_reference': data.get('order_reference'),
            'source': data.get('source'),
            'amt_including_tax': data.get('amount_including_tax'),
            'json_data': str(data),
            'guid': data.get('guid'),
            'legal_entity_id': data.get('legal_entity_id')
        }

        if data.get('sender'):
            unmapped_vals.update({
                'sender_party_name': data['sender'].get('party_name'),
                'sender_address_line1': data['sender'].get('line1'),
                'sender_address_line2': data['sender'].get('line2'),
                'sender_address_city': data['sender'].get('city'),
                'sender_address_county': data['sender'].get('county'),
                'sender_address_zip': data['sender'].get('zip'),
                'sender_address_country': data['sender'].get('country'),
                'billing_first_name': data['sender'].get('billing_contact') and data['sender']['billing_contact'].get(
                    'first_name') or '',
                'billing_last_name': data['sender'].get('billing_contact') and data['sender']['billing_contact'].get(
                    'last_name') or '',
                'email': data['sender'].get('billing_contact') and data['sender']['billing_contact'].get('email') or '',
            })
            sender_peppol_lis, sender_peppol_details = [], ""
            for identifier in data['sender']['identifiers']:
                sender_peppol_lis.append({
                    'superscheme': identifier['superscheme'],
                    'scheme': identifier['scheme'],
                    'identifier': identifier['identifier']
                })
                sender_peppol_details += '||'.join(sender_peppol_lis[-1].values()) + '\n'
            unmapped_vals.update({
                'sender_peppol_identifiers': sender_peppol_details,
            })

        if data.get('payment_means_array') and data['payment_means_array'][0]:
            unmapped_vals.update({
                'payment_means_account': data['payment_means_array'][0].get('account'),
                'payment_means_type': data['payment_means_array'][0].get('type'),
                'payment_means_branch_code': data['payment_means_array'][0].get('branche_code'),
                'payment_means_holder': data['payment_means_array'][0].get('holder'),
                'payment_means_payment_id': data['payment_means_array'][0].get('payment_id')
            })

        lines_lis = []
        for product in data.get('invoice_lines'):
            lines_lis.append((0, 0, {'name': product.get('name'),
                                     'description': product.get('description'),
                                     'quantity': product.get('quantity'),
                                     'price_amount': product.get('price_amount'),
                                     'allowance_charges': product.get('allowance_charges') and
                                                          product.get('allowance_charges')[0],
                                     'amount_excluding_tax': product.get('amount_excluding_tax'),
                                     'tax_type': product.get('tax') and product['tax'].get('type'),
                                     'tax_category': product.get('tax') and product['tax'].get('category'),
                                     'tax_category_code': product.get('tax') and product['tax'].get('category_code'),
                                     'tax_percentage': product.get('tax') and product['tax'].get('percentage'),
                                     'tax_amount': product.get('tax') and product['tax'].get('amount'),
                                     'tax_country': product.get('tax_country')}))
        lines_lis and unmapped_vals.update({'invoice_line_ids': lines_lis})

        # if data.get('legal_entity_id'):
        #     company_obj = self.env['res.company'].search([('legal_entity_identifier', '=', data['legal_entity_id'])], limit=1)
        #     unmapped_vals.update({
        #         'company_id': company_obj and company_obj.id or False,
        #         'legal_entity_id': data['legal_entity_id']
        #     })

        attachment_ids = []
        for attachment in data.get('attachments', []):
            if attachment.get('document'):
                attachment_ids.append(self.env['ir.attachment'].create({
                    'type': 'binary',
                    'name': 'Received Bill/' + fields.Date.today().strftime('%d/%m/%Y'),
                    'datas': attachment['document'],
                    'mimetype': data.get('content_type'),
                }).id)
        attachment_ids and unmapped_vals.update({'document_ids': [(6, 0, attachment_ids)]})

        return unmapped_vals

    def peppol_parsing_invoice(self, data):
        """This method is used to create invoice and peppol log master"""
        purchase_ord_ref = self.env['purchase.order'].sudo().search([('name', '=', data.get('order_reference'))])
        unmapped_vals = self.create_unmapped_invoice_doc(data)

        if purchase_ord_ref:
            unmapped_vals.update({
                'po_id': purchase_ord_ref.id,
                'message': "Invoice mapped Successfully !!!",
                'subtype': 'success',
            })
        else:
            sender_peppol_lis, sender_peppol_details = [], ""
            for identifier in data['sender']['identifiers']:
                sender_peppol_lis.append({
                    'superscheme': identifier['superscheme'],
                    'scheme': identifier['scheme'],
                    'identifier': identifier['identifier']
                })
                sender_peppol_details += '||'.join(sender_peppol_lis[-1].values()) + '\n'

            unmapped_vals.update({
                'message': "Purchase Order is not found in the database. \nInvoice tracked and stored. \n\nSender Party Name: %s\nSender Identifier Details:\n%s"
                           % (data['sender']['party_name'], sender_peppol_details),
                'subtype': 'sent_to_process'
            })
        return unmapped_vals

    def _cron_webhook_event_listener(self):
        for access_point in self.env['peppol.access.point.sg'].sudo().search([]):
            endpoint = access_point.endpoint
            token = access_point.authorization_key
            headers = {'Content-type': 'application/json;charset=UTF-8',
                       'Authorization': 'Bearer {}'.format(access_point.authorization_key)}
            call_webhook = True
            while call_webhook:
                try:
                    web_response = requests.get("{}webhook_instances/".format(endpoint), headers=headers)
                    if web_response.status_code == 200:
                        response = web_response.json()
                        body_data = json.loads(response['body'])
                        log_msg = "Status Code: {}, event_type: {}, ".format(body_data.get('guid', 'None'),
                                                                               body_data.get('event_type', 'None'))
                        if body_data.get('event_type') == 'document_submission':
                            queue_obj = self.env['peppol.queue.out'].sudo().search(
                                [('guid', '=', body_data.get('guid'))], limit=1)
                            log_msg += "peppol.queue.out: {}, ".format(queue_obj.id)
                            if queue_obj:
                                queue_obj.write({'event': body_data.get('event')})
                        elif body_data.get('event_type') == 'received_invoice':
                            self._create_incoming_invoice(body_data.get('guid'), access_point,
                                                          body_data.get('tenant_id'))

                        if self._delete_webhookinstance(response['guid'], endpoint, token) == 204:
                            _logger.info(log_msg)
                            continue
                        else:
                            _logger.exception("Failed in deleting the Webhook.\nResponse::%s" % str(response))
                    else:
                        call_webhook = False

                except ConnectionError as e:
                    call_webhook = False
                    _logger.exception(
                        "ConnectionError arised while performing the GET webhook_instances/ requests:\n %s" % repr(e))

                except Exception as e:
                    call_webhook = False
                    _logger.exception(
                        "Exception arised while performing the GET webhook_instances/ requests:\n %s" % repr(e))

    def _create_incoming_invoice(self, webhook_guid, access_point, tenant_id):
        """This method is used for parsing invoice from purchase_invoice's endpoint."""
        error_codes = {
            401: '401 Unauthorized',
            403: '403 Forbidden',
            404: '404 Not Found'
        }

        endpoint = access_point.endpoint
        token = access_point.authorization_key
        headers = {'Content-type': 'application/json;charset=UTF-8',
                   'Authorization': 'Bearer {}'.format(access_point.authorization_key)}

        try:
            inv_data = {}
            response = requests.get("{}purchase_invoices/{}/json".format(endpoint, webhook_guid), headers=headers)
            if response.status_code == 200:
                inv_data = response.json()
                account_invoice = self.peppol_parsing_invoice(inv_data)
                log_obj = self.env['peppol.log.sg'].create(account_invoice)
                company_obj = self.env['res.company'].sudo().search([('tenant_id', '=', tenant_id)], limit=1)
                if company_obj:
                    log_obj.write({'company_id': company_obj.id})
                if account_invoice.get('po_id', False):
                    # Email Notification to Purchase Order Representative
                    purchase_order = self.env['purchase.order'].sudo().search([('id', '=', account_invoice['po_id'])])
                    if purchase_order.user_id.notification_type == 'email':
                        template_obj = self.env.ref('account_peppol_sg.incoming_invoice_mapped_notification')
                        action_id = self.env.ref('account_peppol_sg.action_pepppol_log_sg_view').id
                        template_obj.with_context({'document_id': log_obj.id, 'action_id': action_id}).send_mail(
                            account_invoice['po_id'], force_send=False)
                    elif purchase_order.user_id.notification_type == 'inbox':
                        body = _(
                            'Hi<br/>A new Invoice has been received from the Peppol network and mapped against the Purchase Order <b>%s</b>.') % (
                                   purchase_order.name)
                        purchase_order.message_post(body=body,
                                                    message_type="notification",
                                                    subtype_xmlid="mail.mt_comment",
                                                    notify_by_email=False,
                                                    partner_ids=[purchase_order.user_id.id])

            elif response.status_code in error_codes.keys():
                self.env['peppol.log.sg'].create({
                    'subtype': 'error',
                    'guid': webhook_guid,
                    'message': error_codes[response.status_code],
                })
            else:
                self.env['peppol.log.sg'].create({
                    'subtype': 'error',
                    'guid': webhook_guid,
                    'message': "Unknown Error",
                })
        except ConnectionError as e:
            _logger.exception("ConnectionError arised while performing the GET requests:\n %s" % repr(e))
        except Exception as e:
            self.env['peppol.log.sg'].create({
                'invoice_no': inv_data.get('invoice_number'),
                'guid': webhook_guid,
                'subtype': 'error',
                'message': 'Critical Error.\nFor more details read the Technical tab.',
                'error_exception': repr(e) + "\nTraceback::" + traceback.format_exc(),
            })

    def _cron_parsing_invoice(self):
        """This method is used for parsing invoice from purchase_invoice's endpoint."""
        error_codes = {
            401: '401 Unauthorized',
            403: '403 Forbidden',
            404: '404 Not Found'
        }

        for access_point in self.env['peppol.access.point.sg'].sudo().search([]):
            endpoint = access_point.endpoint
            token = access_point.authorization_key
            headers = {'Content-type': 'application/json;charset=UTF-8',
                       'Authorization': 'Bearer {}'.format(access_point.authorization_key)}
            call_webhook = True

            while call_webhook:
                try:
                    webhook_guid, inv_data = False, {}
                    web_response = requests.get("{}webhook_instances/".format(endpoint), headers=headers)
                    if web_response.status_code == 200:
                        response = web_response.json()
                        body_data = json.loads(response['body'])
                        webhook_guid = body_data['guid']
                        # Delete the GUID immediately
                        if (self._delete_webhookinstance(response['guid'], endpoint,
                                                         token)) != 204:  # If already deleted then return
                            break
                    else:
                        call_webhook = False
                        continue

                    response = requests.get("{}purchase_invoices/{}/json".format(endpoint, webhook_guid),
                                            headers=headers)
                    if response.status_code == 200:
                        inv_data = response.json()
                        account_invoice = self.peppol_parsing_invoice(inv_data)
                        log_obj = self.env['peppol.log.sg'].create(account_invoice)
                        if account_invoice.get('po_id', False):
                            # Email Notification to Purchase Order Representative
                            purchase_order = self.env['purchase.order'].search([('id', '=', account_invoice['po_id'])])
                            if purchase_order.user_id.notification_type == 'email':
                                template_obj = self.env.ref('account_peppol_sg.incoming_invoice_mapped_notification')
                                action_id = self.env.ref('account_peppol_sg.action_pepppol_log_sg_view').id
                                template_obj.with_context(
                                    {'document_id': log_obj.id, 'action_id': action_id}).send_mail(
                                    account_invoice['po_id'], force_send=False)
                            elif purchase_order.user_id.notification_type == 'inbox':
                                body = _(
                                    'Hi<br/>A new Invoice has been received from the Peppol network and mapped against the Purchase Order <b>%s</b>.') % (
                                           purchase_order.name)
                                purchase_order.message_post(body=body,
                                                            message_type="notification",
                                                            subtype_xmlid="mail.mt_comment",
                                                            notify_by_email=False,
                                                            partner_ids=[purchase_order.user_id.id])

                    elif response.status_code in error_codes.keys():
                        self.env['peppol.log.sg'].create({
                            'subtype': 'error',
                            'guid': webhook_guid,
                            'message': error_codes[response.status_code],
                        })
                    else:
                        self.env['peppol.log.sg'].create({
                            'subtype': 'error',
                            'guid': webhook_guid,
                            'message': "Unknown Error",
                        })
                except ConnectionError as e:
                    _logger.exception("ConnectionError arised while performing the GET requests:\n %s" % repr(e))
                    call_webhook = False
                except Exception as e:
                    call_webhook = False
                    self.env['peppol.log.sg'].create({
                        'invoice_no': inv_data.get('invoice_number'),
                        'guid': webhook_guid,
                        'subtype': 'error',
                        'message': 'Critical Error.\nFor more details read the Technical tab.',
                        'error_exception': repr(e) + "\nTraceback::" + traceback.format_exc(),
                    })


class IncomingInvoiceLines(models.Model):
    _name = "incoming.invoice.lines"
    _description = "Incoming Invoice Lines"

    parent_id = fields.Many2one('peppol.log.sg', 'Parent')
    name = fields.Char("Name")
    description = fields.Char("Description")
    quantity = fields.Float("Quantity")
    price_amount = fields.Float("Price Amount")
    allowance_charges = fields.Float("Allowance Charges")
    amount_excluding_tax = fields.Float("Amount Excluding Tax")
    tax_type = fields.Char("Tax Type")
    tax_category = fields.Char("Tax Category")
    tax_category_code = fields.Char("Tax Category Code")
    tax_percentage = fields.Float("Tax %")
    tax_amount = fields.Float("Tax Amount")
    tax_country = fields.Char("Tax Country")
