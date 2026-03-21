from odoo import fields, models, api, _
import requests
from requests import ConnectionError
import json
import traceback
import logging
import xml.etree.ElementTree as ET
from odoo.exceptions import ValidationError
import urllib.parse

_logger = logging.getLogger(__name__)

SELECTION_PEPPOL_QUEUE_IN_STATE = [
    ('received', 'Received'),
    ('success', 'Mapped'),
    ('sent_to_process', 'Unmapped'),
    ('error', 'Failed'),
    ('cancelled', 'Cancelled')
]

ERROR_RESPONSES_DIC = {
    400: 'Bad Request',
    401: 'Unauthorized',
    404: 'Not Found',
    403: 'Forbidden',
    405: 'Method not allowed'
}


class PeppolLogSG(models.Model):
    _name = "order.queue.in"
    _description = "Incoming Orders Queue"
    _rec_name = "order_no"
    _order = "create_date desc"
    _inherit = ['mail.thread']

    message = fields.Text(string="Message", readonly=True, tracking=True)
    state = fields.Selection(SELECTION_PEPPOL_QUEUE_IN_STATE, string="Status", readonly=True, tracking=True,
                             default='received')
    error_type = fields.Selection([('partner', 'Partner'), ('product', 'Product'), ('tax', 'Tax')])
    so_id = fields.Many2one('sale.order', string="Sale Order", readonly=True)
    company_id = fields.Many2one("res.company", string="Company")
    currency_id = fields.Many2one("res.currency", string="Currency")
    received = fields.Boolean('Received', help="Used for Technical purpose")
    document_ids = fields.Many2many(
        'ir.attachment', 'unmapped_order_docs_docs_rel', 'order_queue_id', 'attachment_id',
        string='Received Documents')
    access_point_id = fields.Many2one('peppol.access.point.sg')
    error_exception = fields.Text("Technical Error")
    xml_data = fields.Text("XML Invoice Data", help="For Technical Use only")

    upload_time = fields.Char('Document uploaded/received time')
    extracted_senderid = fields.Char('Sender Peppol ID', help="Sender id extracted from the uploaded xml", tracking=1)
    extracted_receiverid = fields.Char('Receiver Peppol ID', help="Receiver id extracted from the uploaded xml", tracking=1)
    extracted_totamount = fields.Char('Total Amount', help="Document total amount extracted from the uploaded xml",
                                      tracking=1)
    extracted_docno = fields.Char('Document No', help="Document number extracted from the uploaded xml", tracking=1)
    invalidated = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Invalidated Document",
                                   help="true denotes an Invalidated document. Documents become invalidated when a new document with the same Document number received again.",
                                   tracking=1)
    instance_id = fields.Char('Instance ID',
                              help="Generated unique id for the document when sending to the peppol network.")

    status_message = fields.Text('Status Message', default='', tracking=1, help="Detailed description for the status.")

    sender_party_name = fields.Char("Customer")
    sender_address_line1 = fields.Char("Customer Address Line 1")
    sender_address_line2 = fields.Char("Customer Address Line 2")
    sender_address_city = fields.Char("Customer City")
    sender_address_county = fields.Char("Customer County")
    sender_address_zip = fields.Char("Customer Zip")
    sender_address_country = fields.Char("Customer Country")

    sender_contact_name = fields.Char(string="Customer Contact Name")
    sender_contact_phone = fields.Char(string="Customer Contact Phone")
    sender_contact_email = fields.Char(string="Customer Contact Email")

    sender_party_tax_scheme_companyid = fields.Char("Customer Tax Scheme Company Id",
                                                    help="Seller GST identifier, Seller tax registration identifier")
    sender_party_tax_scheme_id = fields.Char("Customer Tax Scheme Id", help="Seller tax registration identifier")

    note = fields.Text("Note") #Note
    issue_date = fields.Date("Issue Date")
    validity_date = fields.Date("Validity Date") #ValidityPeriod
    document_currency_code = fields.Char("Currency Code", help="The ISO 4217 currency for the invoice.") #DocumentCurrencyCode

    order_no = fields.Char(string="Order Ref", readonly=True, tracking=True) #ID
    order_type_code = fields.Char("Order Type Code") #OrderTypeCode

    sale_order_ref = fields.Char("Sales Order ID", help="An identifier of a referenced sales order, issued by the Seller") #SalesOrderID
    buyer_reference = fields.Char("Customer Reference", help="Reference provided by the buyer. Used for routing") #CustomerReference

    order_reference = fields.Char("Original Order",
                                  help="Reference to the order.") #Order document reference

    payment_terms = fields.Text('Payment Terms') #PaymentTerms
    payment_means = fields.Text('Payment Means')

    order_line_ids = fields.One2many("incoming.order.lines", "parent_id", "Order Lines")

    amt_including_tax = fields.Float("Total") 
    amt_untaxed = fields.Float("Untaxed Amount")
    taxed_amt = fields.Float("Tax")
    discount_amt = fields.Float("Discount Amount")

    purchase_ord_ref = fields.Many2one('purchase.order')

    delivery_location_name = fields.Char('Delivery Location Name')
    delivery_location_id = fields.Char('Delivery Location ID')
    delivery_location_street1 = fields.Char('Delivery Location Address Line 1')
    delivery_location_street2 = fields.Char('Delivery Location Address Line 2')
    delivery_location_city = fields.Char('Delivery Location City')
    delivery_location_zip = fields.Char('Delivery Location Zip')
    delivery_location_country = fields.Char('Delivery Location Country')

    requested_delivery_startdate = fields.Char('Requested Delivery Start Date')
    requested_delivery_enddate = fields.Char('Requested Delivery End Date')

    delivery_party_name = fields.Char('Delivery Party Name')
    delivery_party_id = fields.Char('Delivery Party ID')
    delivery_party_street1 = fields.Char('Delivery Party Address Line 1')
    delivery_party_street2 = fields.Char('Delivery Party Address Line 2')
    delivery_party_city = fields.Char('Delivery Party City')
    delivery_party_zip = fields.Char('Delivery Party Zip')
    delivery_party_country = fields.Char('Delivery Party Country')

    delivery_party_contact_name = fields.Char(string="Delivery Party Contact Name")
    delivery_party_contact_phone = fields.Char(string="Delivery Party Contact Phone")
    delivery_party_contact_email =  fields.Char(string="Delivery Party Contact Email")

    order_response_out_ids = fields.Many2many('order.responses.queue.out', string="Responses") # 'ord_queue_in_resp_rel', 'queue_in', 'response_out_id'
    sent_order_responses_count = fields.Integer(string="Sent Order Responses Count",compute="_compute_order_response_count")
    client_ref = fields.Char('Client Ref')
    map_sale_order_count = fields.Integer(string="Sent Order Responses Count",compute="_compute_map_sale_order_count")
    document_type = fields.Selection([
        ('initial', 'Initial'),
        ('balance', 'Balance'),
        ('variation', 'Variation'),
        ('cancel', 'Cancel')], string="Document Type")
    order_line_note = fields.Text("Note")
    incoming_orders_count = fields.Integer(string="Incoming Orders Count",compute="_compute_incoming_order_count")
    incoming_balance_orders_count = fields.Integer(string="Incoming Orders Count",compute="_compute_incoming_balance_order_count")
    variation_number = fields.Char("Variation Number")  #  Variation Number

    def _compute_order_response_count(self):
        for rec in self:
            order_responses_count = self.env['order.responses.queue.out'].search_count(
                [('source_doc_id', '=', rec.id)])
            rec.sent_order_responses_count = order_responses_count

    def action_view_order_response_queue_out(self):
        name = 'Outgoing Order Responses'
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'order.responses.queue.out',
            'domain': [('source_doc_id', '=', self.ids)],
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def _compute_map_sale_order_count(self):
        for rec in self:
            map_sale_order_count = self.env['sale.order'].search_count(
                [('origin', '=', self.order_no)])
            rec.map_sale_order_count = map_sale_order_count

    def action_view_map_sale_orders(self):
        sale_order = self.env['sale.order']
        orders = sale_order.search([('origin', '=', self.order_no)])
        name = 'Sales Orders'
        if len(orders) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': name,
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': orders.id,
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': name,
                'res_model': 'sale.order',
                'domain': [('origin', '=', self.order_no)],
                'view_mode': 'tree,form',
                'target': 'current',
            }

    def action_view_incoming_orders(self):
        name = 'Incoming Orders'
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'order.queue.in',
            'domain': [('order_reference', '=', self.order_reference), ('id', '!=', self.id), ('order_reference', '!=', False)],
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def _compute_incoming_order_count(self):
        for rec in self:
            incoming_orders_count = self.search_count(
                [('order_reference', '=', self.order_reference), ('id', '!=', rec.id), ('order_reference', '!=', False)])
            rec.incoming_orders_count = incoming_orders_count

    def action_view_incoming_balance_orders(self):
        name = 'Incoming Orders'
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'order.queue.in',
            'domain': [('order_reference', '=', self.order_no), ('order_reference', '!=', False)],
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def _compute_incoming_balance_order_count(self):
        for rec in self:
            incoming_balance_orders_count = self.search_count(
                [('order_reference', '=', self.order_no), ('order_reference', '!=', False)])
            print('\n\n\n\nincoming_balance_orders_count', incoming_balance_orders_count)
            rec.incoming_balance_orders_count = incoming_balance_orders_count

    # change order incoming oreder query code
    def query_receive_documents(self):
        for access_point in self.env['peppol.access.point.sg'].sudo().search([('company_id', '=', self.env.company.id)]):
            base_url = access_point.endpoint
            api_version = access_point.api_version
            receiver_peppol_id = access_point.company_id.peppol_scheme + ':' + access_point.company_id.peppol_identifier
            print('\n\n\nreceiver_peppol_id', receiver_peppol_id)
            timeout = self.env['ir.config_parameter'].sudo().get_param('api_timeout', default='20')
            headers = {
                # "Accept": "*/*",
                "Authorization": f"Bearer {access_point.access_token}",
                # TODO: Don't calculate but instead calculate and store as one time.
            }
            try:
                status_code, response_data = 'None', ''
                response = requests.get(
                    '%s/api/business/%s/orders?receiver=%s' % (base_url, api_version, receiver_peppol_id),
                    headers=headers,
                    timeout=int(timeout))
                print('%s/business/%s/orders.json?type=2&receiver=%s' % (base_url, api_version, receiver_peppol_id))
                status_code = response.status_code
                print('\n\n\nstatus_code', status_code)
                try:
                    response_data = json.loads(response.text)
                except:
                    response_data = response.text
                print("orders = response_data ===",response_data)
                print("isinstance(response_data, dict) ==",isinstance(response_data, dict))
                print("status_code ==",status_code)
                if status_code == 200 and isinstance(response_data, dict):
                    for resp_dic in response_data['info']:
                        self._create_incoming_order_record(resp_dic, {'base_url': base_url, 'api_version': api_version,
                                                                'headers': headers, 'timeout': timeout},
                                                     company_id=access_point.company_id.id,
                                                     access_point_id=access_point.id)
                else:
                    vals = {
                        'status_code': status_code,
                        'response_body': response_data,
                        'doc_type': 'orders'
                    }
                    self.env['incoming.failed.logs'].create(vals)

            except ConnectionError as e:
                _logger.exception(
                    "ConnectionError arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e))
                vals = {
                    'status_code': status_code,
                    'response_body': response_data,
                    'error_body': "ConnectionError arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e),
                    'traceback_body': traceback.format_exc(),
                    'doc_type': 'orders'
                }
                self.env['incoming.failed.logs'].create(vals)
            except Exception as e:
                _logger.exception(
                    "An Exception arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e))
                vals = {
                    'status_code': status_code,
                    'response_body': response_data,
                    'error_body': "An Exception arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e),
                    'traceback_body': traceback.format_exc(),
                    'doc_type': 'orders'
                }
                self.env['incoming.failed.logs'].create(vals)

    def _create_incoming_order_record(self, resp_dic, api_dic, company_id, access_point_id):
        if self.search([('order_no', '=', resp_dic.get('documentNo', '').strip())]):
            return
        company_obj = False
        if resp_dic.get('receiver'):
            receiver_peppol_id = resp_dic.get('receiver').strip().split(":")[1]
            company_obj = self.env['res.company'].sudo().search(['|',('peppol_identifier','=',receiver_peppol_id), ('peppol_identifier','ilike',receiver_peppol_id)], limit=1)
        obj = self.create({
            'status_message': resp_dic.get('statusMessage'),
            'invalidated': 'yes' if resp_dic.get('invalidated') == True else 'no',
            'extracted_senderid': resp_dic.get('sender').strip(),
            'extracted_receiverid': resp_dic.get('receiver').strip(),
            'extracted_totamount': resp_dic.get('amount'),
            'extracted_docno': resp_dic.get('documentNo').strip(),
            'instance_id': resp_dic.get('instanceId'),
            'client_ref': resp_dic.get('clientRef'),
            'order_no': resp_dic.get('documentNo').strip(),
            'received': True,
            'company_id': company_obj and company_obj.id or False,
            'access_point_id': access_point_id,
            'document_type': 'initial',
        })

        try:
            response = requests.get('%s/api/business/%s/orders/%s' % (api_dic['base_url'],
                                                                        api_dic['api_version'],
                                                                        urllib.parse.quote(resp_dic.get('clientRef'), safe="")
                                                                        ),
                                    headers=api_dic['headers'],
                                    timeout=int(api_dic['timeout']))
            status_code = response.status_code
            try:
                response_data = json.loads(response.text)
            except:
                response_data = response.text
            if status_code == 200:
                obj._parse_xml_order_data(response_data)
            else:
                extra_msg = ''
                if isinstance(response_data, dict) and response_data.get('message'):
                    extra_msg = response_data.get('message')
                obj.write({'state': 'error',
                           'message': "{} {}\n{}".format(status_code, ERROR_RESPONSES_DIC.get(status_code, ''),
                                                         extra_msg)})
                obj.message_post(body=_("<b>Download Document API responded as {} {}</b><br/>{}".format(status_code,
                                                                                                        ERROR_RESPONSES_DIC.get(
                                                                                                            status_code,
                                                                                                            ''),
                                                                                                        response_data)))
        except ConnectionError as e:
            _logger.exception(
                "ConnectionError arised while performing the 'Download Incoming Doc API' GET requests:\n %s" % repr(e))
        except Exception as e:
            _logger.exception(
                "An Exception arised while performing the 'Download Incoming Doc API' GET requests:\n %s" % repr(e))
            obj.write({
                'state': 'error',
                'message': 'Critical Error.\nFind more details under the Technical tab.',
                'error_exception': repr(e) + "\nTraceback::" + traceback.format_exc(),
            })

    def _parse_xml_order_data(self, xml_str):
        print("\n\n >>>>>  _parse_xml_order_data() >>>>>>")
        cbc = "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}"
        cac = "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}"
        vals = {'xml_data': xml_str,
                'state': 'sent_to_process'}
        myroot = ET.fromstring(xml_str)
        try:
            payment_str = ''
            order_lines = []
            for x in myroot[1]:
                print("x.tag ==",x.tag)
                if x.tag == cbc + 'ID':  # <cbc:ID>
                    vals.update({'order_no': x.text})
                if x.tag == cbc + 'IssueDate':  # <cbc:IssueDate>
                    vals.update({'issue_date': x.text})
                if x.tag == cbc + 'DueDate':  # <cbc:DueDate>
                    vals.update({'due_date': x.text})
                if x.tag == cbc + 'OrderTypeCode':  # <cbc:InvoiceTypeCode>
                    vals.update({'order_type_code': x.text})
                if x.tag == cbc + 'Note':  # <cbc:Note>
                    vals.update({'note': x.text})
                if x.tag == cbc + 'DocumentCurrencyCode':  # <cbc:DocumentCurrencyCode>
                    currency_obj = self.env['res.currency'].sudo().search([('name', '=', x.text.strip())], limit=1)
                    vals.update({'document_currency_code': x.text,
                                 'currency_id': currency_obj and currency_obj.id or False})
                if x.tag == cac + 'ValidityPeriod':
                    for child in x:
                        if child.tag == cbc + 'EndDate':
                            vals.update({'validity_date': child.text})
                if x.tag == cbc + 'SalesOrderID':  # <cbc:SalesOrderID>
                    vals.update({'sale_order_ref': x.text})
                if x.tag == cbc + 'CustomerReference':  # <cbc:BuyerReference>
                    vals.update({'buyer_reference': x.text})
                if x.tag == cac + 'OrderDocumentReference':  # <cac:OrderReference>
                    for child in x:
                        if child.tag == cbc + 'ID':
                            vals.update({'order_reference': child.text})
                if x.tag == cac + 'AdditionalDocumentReference': # <cac:AdditionalDocumentReference>
                    for child in x:
                        if child.tag == cac + 'Attachment':
                            for subchild in child:
                                if subchild.tag == cbc + 'EmbeddedDocumentBinaryObject':
                                    attr_dic = subchild.attrib
                                    vals.update({'document_ids': [(0, 0, {
                                       'type': 'binary',
                                       'name': attr_dic.get('filename'),
                                       'datas': subchild.text,
                                       'mimetype': attr_dic.get('mimeCode')
                                   })]})
                if x.tag == cac + 'BuyerCustomerParty':  # <cac:AccountingSupplierParty>
                    for child in x:
                        if child.tag == cac + 'Party':  # <cac:Party>
                            for subchild in child:
                                if subchild.tag == cac + 'PartyName':  # <cac:PartyName>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'Name':  # <cbc:Name>
                                            vals.update({'sender_party_name': subchild_1.text})
                                if subchild.tag == cac + 'PostalAddress':  # <cac:PostalAddress>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'StreetName':
                                            vals.update({'sender_address_line1': subchild_1.text})
                                        if subchild_1.tag == cbc + 'AdditionalStreetName':
                                            vals.update({'sender_address_line2': subchild_1.text})
                                        if subchild_1.tag == cbc + 'CityName':
                                            vals.update({'sender_address_city': subchild_1.text})
                                        if subchild_1.tag == cbc + 'PostalZone':
                                            vals.update({'sender_address_zip': subchild_1.text})
                                        if subchild_1.tag == cac + 'Country':
                                            for subchild_1_1 in subchild_1:
                                                if subchild_1_1.tag == cbc + 'IdentificationCode':
                                                    vals.update({'sender_address_country': subchild_1_1.text})
                                if subchild.tag == cac + 'PartyTaxScheme':  # <cac:PartyTaxScheme>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'CompanyID':
                                            vals.update({'sender_party_tax_scheme_companyid': subchild_1.text})
                                        if subchild_1.tag == cac + 'TaxScheme':
                                            for subchild_1_1 in subchild_1:
                                                if subchild_1_1.tag == cbc + 'ID':
                                                    vals.update({'sender_party_tax_scheme_id': subchild_1_1.text})
                                # TODO: Party Legal Entity
                                if subchild.tag == cac + 'Contact':  # <cac:Contact>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'Name':
                                            vals.update({'sender_contact_name': subchild_1.text})
                                        if subchild_1.tag == cbc + 'ElectronicMail':
                                            vals.update({'sender_contact_email': subchild_1.text})
                                        if subchild_1.tag == cbc + 'Telephone':
                                            vals.update({'sender_contact_phone': subchild_1.text})

                if x.tag == cac + 'Delivery':  # <cac:Delivery>
                    for child in x:
                        if child.tag == cac + 'DeliveryLocation':  # <cac:DeliveryLocation>
                            for subchild in child:                            
                                if subchild.tag == cbc + 'ID':  # <cbc:ID>
                                    vals.update({'delivery_location_id': subchild.text})
                                if subchild.tag == cbc + 'Name':  # <cbc:Name>
                                    vals.update({'delivery_location_name': subchild.text})
                                if subchild.tag == cac + 'Address':  # <cac:Address>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'StreetName':
                                            vals.update({'delivery_location_street1': subchild_1.text})
                                        if subchild_1.tag == cbc + 'AdditionalStreetName':
                                            vals.update({'delivery_location_street2': subchild_1.text})
                                        if subchild_1.tag == cbc + 'CityName':
                                            vals.update({'delivery_location_city': subchild_1.text})
                                        if subchild_1.tag == cbc + 'PostalZone':
                                            vals.update({'delivery_location_zip': subchild_1.text})
                                        if subchild_1.tag == cac + 'Country':
                                            for subchild_1_1 in subchild_1:
                                                if subchild_1_1.tag == cbc + 'IdentificationCode':
                                                    vals.update({'delivery_location_country': subchild_1_1.text})

                        if child.tag == cac + 'RequestedDeliveryPeriod':  # <cac:RequestedDeliveryPeriod>
                            for subchild in child:
                                if subchild.tag == cbc + 'StartDate':
                                    vals.update({'requested_delivery_startdate': subchild.text})
                                if subchild.tag == cbc + 'EndDate':
                                    vals.update({'requested_delivery_enddate': subchild.text})
                            for subchild in child:
                                if subchild.tag == cbc + 'StartTime':
                                    vals['requested_delivery_startdate'] = vals['requested_delivery_startdate'] + ' ' + subchild.text
                                if subchild.tag == cbc + 'EndTime':
                                    vals['requested_delivery_enddate'] = vals['requested_delivery_enddate'] + ' ' + subchild.text

                        if child.tag == cac + 'DeliveryParty':  # <cac:DeliveryParty>
                            for subchild in child:
                                if subchild.tag == cac + 'PartyIdentification':  # <cbc:PartyIdentification>
                                    for subchild_1 in subchild:                                        
                                        if subchild_1.tag == cbc + 'ID':  # <cbc:ID>
                                            vals.update({'delivery_party_id': subchild_1.text})
                                if subchild.tag == cac + 'PartyName':  # <cac:PartyName>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'Name':  # <cbc:Name>
                                            vals.update({'delivery_party_name': subchild_1.text})
                                if subchild.tag == cac + 'PostalAddress':  # <cac:PostalAddress>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'StreetName':
                                            vals.update({'delivery_party_street1': subchild_1.text})
                                        if subchild_1.tag == cbc + 'AdditionalStreetName':
                                            vals.update({'delivery_party_street2': subchild_1.text})
                                        if subchild_1.tag == cbc + 'CityName':
                                            vals.update({'delivery_party_city': subchild_1.text})
                                        if subchild_1.tag == cbc + 'PostalZone':
                                            vals.update({'delivery_party_zip': subchild_1.text})
                                        if subchild_1.tag == cac + 'Country':
                                            for subchild_1_1 in subchild_1:
                                                if subchild_1_1.tag == cbc + 'IdentificationCode':
                                                    vals.update({'delivery_party_country': subchild_1_1.text})
                                # TODO: Party Legal Entity
                                if subchild.tag == cac + 'Contact':  # <cac:Contact>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'Name':
                                            vals.update({'delivery_party_contact_name': subchild_1.text})
                                        if subchild_1.tag == cbc + 'ElectronicMail':
                                            vals.update({'delivery_party_contact_email': subchild_1.text})
                                        if subchild_1.tag == cbc + 'Telephone':
                                            vals.update({'delivery_party_contact_phone': subchild_1.text})
                                


                if x.tag == cac + 'PaymentTerms':  # <cac:PaymentTerms>
                    for child in x:
                        if child.tag == cbc + 'Note':
                            vals.update({'payment_terms': child.text})

                if x.tag == cac + 'TaxTotal':  # <cac:TaxTotal>
                    for child in x:
                        if child.tag == cbc + 'TaxAmount':
                            vals.update({'taxed_amt': child.text})
                            break

                if x.tag == cac + 'AnticipatedMonetaryTotal':  # <cac:AnticipatedMonetaryTotal>
                    for child in x:
                        if child.tag == cbc + 'TaxExclusiveAmount':
                            vals.update({'amt_untaxed': child.text})
                        if child.tag == cbc + 'AllowanceTotalAmount':
                            vals.update({'discount_amt': child.text})
                        if child.tag == cbc + 'PayableAmount':
                            vals.update({'amt_including_tax': child.text})
                
                if x.tag == cac + 'OrderLine':  # <cac:OrderLine>
                    lines_dic = {}
                    for ch in x:
                        if ch.tag == cbc + 'Note':
                            lines_dic.update({'note': ch.text})
                        if ch.tag == cac + 'LineItem':
                            print("ch.tag ==",ch.tag)
                            for child in ch:
                                if child.tag == cbc + 'ID':
                                    lines_dic.update({'line_item_id': child.text})
                                if child.tag == cbc + 'Quantity':
                                    attr_dic = child.attrib
                                    print("\nattr_dic ====",attr_dic)
                                    lines_dic.update({'quantity': child.text, 'unit_code': attr_dic.get('unitCode', '')})
                                if child.tag == cbc + 'LineExtensionAmount':
                                    lines_dic.update({'amount_excluding_tax': child.text})
                                if child.tag == cbc + 'Delivery':
                                    for child_d in child:
                                        if child_d.tag == cac + 'RequestedDeliveryPeriod':  # <cac:RequestedDeliveryPeriod>
                                            for subchild in child_d:
                                                if subchild.tag == cbc + 'StartDate':
                                                    vals.update({'issue_date': subchild.text})
                                if child.tag == cac + 'AllowanceCharge':
                                	print("child.tag ==",child.tag)
                                	for child_1 in child:
                                		print("child_1.tag == cbc + 'ChargeIndicator'", child_1.tag == cbc + 'ChargeIndicator')
                                		print("child_1.text == True", child_1.text == True)
                                		if child_1.tag == cbc + 'ChargeIndicator' and child_1.text == True: # IF it is a charge, then avoid.
                                			break
                                		if child_1.tag == cbc + 'Amount':
                                			lines_dic.update({'allowance_charges': child_1.text})
                                if child.tag == cac + 'Price':
                                    price_amount, base_qty = 0.0, 1
                                    for child_1 in child:
                                        if child_1.tag == cbc + 'PriceAmount':
                                            price_amount = float(child_1.text)
                                        if child_1.tag == cbc + 'BaseQuantity':
                                            base_qty = int(child_1.text)

                                    if price_amount > 0.0:
                                        lines_dic.update({'price_amount': price_amount / base_qty})
                                if child.tag == cac + 'Item':
                                    for child_1 in child:
                                        if child_1.tag == cbc + 'Name':
                                            lines_dic.update({'name': child_1.text})
                                        if child_1.tag == cbc + 'Description':
                                            lines_dic.update({'description': child_1.text})
                                        if child_1.tag == cac + 'BuyersItemIdentification':
                                            for child_1_1 in child_1:
                                                if child_1_1.tag == cbc + 'ID':
                                                    lines_dic.update({'buyers_item_identification': child_1_1.text})
                                        if child_1.tag == cac + 'SellersItemIdentification':
                                            for child_1_1 in child_1:
                                                if child_1_1.tag == cbc + 'ID':
                                                    lines_dic.update({'sellers_item_identification': child_1_1.text})
                                        if child_1.tag == cbc + 'ManufacturersItemIdentification':
                                            for child_1_1 in child_1:
                                                if child_1_1.tag == cbc + 'ID':
                                                    lines_dic.update({'manufacturers_item_identification': child_1_1.text})
                                        if child_1.tag == cbc + 'StandardItemIdentification':
                                            for child_1_1 in child_1:
                                                if child_1_1.tag == cbc + 'ID':
                                                    lines_dic.update({'standard_item_identification': child_1_1.text})
                                        if child_1.tag == cbc + 'CommodityClassification':
                                            for child_1_1 in child_1:
                                                if child_1_1.tag == cbc + 'ItemClassificationCode':
                                                    lines_dic.update({'item_classification_identifier': child_1_1.text})
                                        if child_1.tag == cac + 'ClassifiedTaxCategory':
                                            for child_1_1 in child_1:
                                                if child_1_1.tag == cbc + 'Percent':
                                                    lines_dic.update({'tax_percentage': child_1_1.text})
                                                if child_1_1.tag == cbc + 'ID':
                                                    lines_dic.update({'tax_category_code': child_1_1.text})
                                                if child_1_1.tag == cac + 'TaxScheme':
                                                    for child_1_1_1 in child_1_1:
                                                        if child_1_1_1.tag == cbc + 'ID':
                                                            lines_dic.update({'tax_type': child_1_1_1.text})
                    if lines_dic:
                        order_lines.append((0, 0, lines_dic))

            order_lines and vals.update({'order_line_ids': order_lines})
            if 'sale_order_ref' in vals:
                sale_obj = self.env['sale.order'].sudo().search(
                    [('name', '=', vals.get('sale_order_ref'))])
                if sale_obj:
                    vals.update({
                        'so_id': sale_obj.id,
                        'message': "The Buyer issued Sale Order is mapped successfully!",
                        'state': 'success',
                    })
                else:
                    vals.update({
                        'message': "The Buyer issued Sale Order '%s' is not found in the database. Please either map or create the new Order." % (
                            vals.get('sale_order_ref', '')),
                        'state': 'sent_to_process'
                    })

            vals.update({
                'state': 'sent_to_process'
            })
            self.write(vals)

        except Exception as e:
            self.write({
                'state': 'error',
                'message': 'Critical Error.\nFind more details under the Technical tab.',
                'error_exception': repr(e) + "\nTraceback::" + traceback.format_exc(),
            })


    def action_retry(self):
        print("action_retry====")
        for obj in self:
            access_point = obj.access_point_id
            base_url = access_point.endpoint
            api_version = access_point.api_version
            timeout = self.env['ir.config_parameter'].sudo().get_param('api_timeout', default='20')
            headers = {
                "Accept": "*/*",
                "Authorization": "Basic {}".format(access_point.get_basic_auth_token()),
                # TODO: Dont calculate but instead calculate and store as one time.
            }
            try:
                response = requests.get('%s/business/%s/orders/%s.xml' % (base_url, api_version, urllib.parse.quote(obj.extracted_docno, safe="")),
                                        headers=headers,
                                        timeout=int(timeout))
                status_code = response.status_code
                try:
                    response_data = json.loads(response.text)
                except:
                    response_data = response.text
                print("status_code ==",status_code)
                if status_code == 200:
                    self._parse_xml_order_data(response_data)
                else:
                    extra_msg = ''
                    if isinstance(response_data, dict) and response_data.get('message'):
                        extra_msg = response_data.get('message')
                    self.write({'state': 'error',
                                'message': "{} {}\n{}".format(status_code, ERROR_RESPONSES_DIC.get(status_code, ''),
                                                              extra_msg)})
                    self.message_post(
                        body=_("<b>Download Document API responded as {} {}</b><br/>{}".format(status_code,
                                                                                               ERROR_RESPONSES_DIC.get(
                                                                                                   status_code, ''),
                                                                                               response_data)))
            except ConnectionError as e:
                _logger.exception(
                    "ConnectionError arised while retying the 'Download Incoming Doc API' GET requests:\n %s" % repr(e))
            except Exception as e:
                _logger.exception(
                    "An Exception arised while retying the 'Download Incoming Doc API' GET requests:\n %s" % repr(e))

    def unlink(self):
        for line in self:
            if line.state not in ('received', 'cancelled'):
                raise ValidationError(_("You cannot delete the records in the state other than 'Received' or 'Cancelled'."))
        return super(PeppolLogSG, self).unlink()

    def action_cancel(self):
        """ This method will set the state as cancelled. """
        self.write({'state': 'cancelled'})

    def action_view_orders(self):
        """ List all the Sale Orders and displays the 'Map' button."""
        self.ensure_one()
        ctx = self._context
        res = {}
        if self._name == 'order.queue.in':
            # queue_obj = self.env[active_model].browse(active_id)
            res['origin'] = self.order_no
            res['company_id'] = self.company_id.id
            res['incoming_order_id'] = self.id
            if self.document_type:
                res['document_type'] = self.document_type
            if self.buyer_reference:
                res['client_order_ref'] = self.buyer_reference
            if self.requested_delivery_enddate:
                if not self.requested_delivery_enddate.split(" "):
                    requested_delivery_enddate = self.requested_delivery_enddate + " 00:00:00"
                else:
                    requested_delivery_enddate = self.requested_delivery_enddate
                res['commitment_date'] = requested_delivery_enddate

            if self.payment_terms:
                pobjs = self.env['account.payment.term'].sudo().search([('name', 'ilike', self.payment_terms), ('company_id', '=', self.company_id.id)],
                                                                       limit=1)
                print("pobjs ==", pobjs)
                if pobjs:
                    res['payment_term_id'] = pobjs.id
                else:
                    res['payment_term_id'] = self.env['account.payment.term'].sudo().create(
                        {'name': self.payment_terms}).id

            partner = self.env['res.partner'].search([('company_id', '=', self.company_id.id), '|',
                                                      ('peppol_identifier', '=',
                                                       self.extracted_senderid.split(":")[1]),
                                                      ('peppol_identifier', 'ilike',
                                                       self.extracted_senderid.split(":")[1])], limit=1)
            if partner:
                res['partner_id'] = partner.id
            else:
                country_obj, child_dic = False, {}
                if self.sender_address_country:
                    country_obj = self.env['res.country'].search(['|', ('name', '=', self.sender_address_country),
                                                                  ('code', '=', self.sender_address_country)],
                                                                 limit=1)
                if self.sender_contact_name:
                    child_dic = {'type': 'contact', 'name': self.sender_contact_name,
                                 'email': self.sender_contact_email, 'phone': self.sender_contact_phone}
                partner = self.env['res.partner'].create({
                    'company_type': 'company',
                    'name': self.sender_party_name,
                    'street': self.sender_address_line1,
                    'street2': self.sender_address_line2,
                    'city': self.sender_address_city,
                    'zip': self.sender_address_zip,
                    'country_id': country_obj and country_obj.id or False,
                    'peppol_identifier': self.extracted_senderid.split(":")[1],
                    'peppol_scheme': '0195',
                    'child_ids': child_dic and [(0, 0, child_dic)] or False
                })
                res['partner_id'] = partner.id

            delivery_contact_dic = {}
            if self.delivery_party_name:
                delivery_contact_dic = {'type': 'delivery'}
                if self.delivery_party_contact_name:
                    delivery_contact_dic['name'] = self.delivery_party_contact_name
                else:
                    delivery_contact_dic['name'] = self.delivery_party_name

                country_obj = False
                if self.delivery_party_country:
                    country_obj = self.env['res.country'].search(['|', ('name', '=', self.delivery_party_country),
                                                                  ('code', '=', self.delivery_party_country)],
                                                                 limit=1)

                delivery_contact_dic.update({
                    'street': self.delivery_party_street1,
                    'street2': self.delivery_party_street2,
                    'city': self.delivery_party_city,
                    'zip': self.delivery_party_zip,
                    'country_id': country_obj and country_obj.id or False,
                    'email': self.delivery_party_contact_email,
                    'phone': self.delivery_party_contact_phone,
                    'parent_id': partner.id
                })

            if delivery_contact_dic:
                delivery_contact_present = False
                for child in partner.sudo().child_ids.filtered(lambda x: x.type == 'delivery'):
                    if child.name == delivery_contact_dic['name']:
                        delivery_contact_present = child
                        break;
                if not delivery_contact_present:
                    delivery_contact_present = self.env['res.partner'].create(delivery_contact_dic)
                res['partner_shipping_id'] = delivery_contact_present.id

            if self.validity_date:
                res['validity_date'] = self.validity_date
            # payment_term = self.env['account.payment.term'].search([('name', '=', self.payment_terms)])
            # if payment_term:
            #     res['payment_term_id'] = payment_term.id
            if self.note:
                res['note'] = self.note
            order_lines = []
            for line in self.order_line_ids:
                default_codes, barcodes = [], []
                if line.buyers_item_identification:
                    product = self.env['product.product'].search([('company_id', '=', self.company_id.id), '|',
                                                                  ('default_code', '=',
                                                                   line.buyers_item_identification),
                                                                  ('barcode', '=', line.buyers_item_identification)],
                                                                 limit=1)
                elif line.sellers_item_identification:
                    product = self.env['product.product'].search([('company_id', '=', self.company_id.id), '|',
                                                                  ('default_code', '=',
                                                                   line.sellers_item_identification),
                                                                  ('barcode', '=', line.sellers_item_identification)],
                                                                 limit=1)
                elif line.manufacturers_item_identification:
                    product = self.env['product.product'].search([('company_id', '=', self.company_id.id), '|',
                                                                  ('default_code', '=',
                                                                   line.manufacturers_item_identification),
                                                                  ('barcode', '=',
                                                                   line.manufacturers_item_identification)], limit=1)
                elif line.standard_item_identification:
                    product = self.env['product.product'].search([('company_id', '=', self.company_id.id), '|',
                                                                  ('default_code', '=',
                                                                   line.standard_item_identification),
                                                                  ('barcode', '=', line.standard_item_identification)],
                                                                 limit=1)
                elif line.item_classification_identifier:
                    product = self.env['product.product'].search([('company_id', '=', self.company_id.id), '|',
                                                                  ('default_code', '=',
                                                                   line.item_classification_identifier),
                                                                  ('barcode', '=',
                                                                   line.item_classification_identifier)], limit=1)
                else:
                    product = self.env['product.product'].search(
                        [('company_id', '=', self.company_id.id), '|', ('name', '=', line.name),
                         ('name', 'ilike', line.name)], limit=1)

                order_line_values = {
                    'product_id': product.id if product else False,
                    'name': line.description or line.name,
                    'product_uom_qty': line.quantity,
                    'price_unit': line.price_amount,
                    # 'date_planned': line.create_date,
                    # 'price_subtotal': line.amount_excluding_tax,
                    'product_uom': product.uom_id.id if product and product.uom_id else False,
                    'incoming_order_line_id': line.id,
                    'tax_id': False
                }
                print('\n\n\n\norder_line_values', order_line_values)
                if line.unit_code:
                    uom_obj = self.env['uom.uom'].sudo().search([('unece_code', '=', line.unit_code)], limit=1)
                    if uom_obj:
                        order_line_values.update({'product_uom': uom_obj.id})
                    else:
                        raise ValidationError(
                            "Please configure '" + str(line.unit_code) + "' in Units of Measure master list.")

                discount = (line.quantity * line.price_amount) - line.amount_excluding_tax
                if discount > 0.0:
                    discount_percentage = (discount / (line.quantity * line.price_amount)) * 100
                    order_line_values.update({'discount': discount_percentage})
                order_lines.append((0, 0, order_line_values))

            res['order_line'] = order_lines
            res['document_type'] = self.document_type
            print('\n\nres', res)
            _logger.info(res)
            so_id = self.env['sale.order'].create(res)
            for orderline in so_id.order_line:
                if orderline.incoming_order_line_id.tax_category_code:
                        tax_obj = self.env['account.tax'].sudo().search([('company_id','=',so_id.company_id.id), ('type_tax_use','=','sale'), ('amount','=',orderline.incoming_order_line_id.tax_percentage)], limit=1)
                        print("tax_obj ==",tax_obj)
                        if tax_obj and tax_obj.unece_categ_id:
                            orderline.tax_id = [(6,0,[tax_obj.id])]
                        else:
                            raise ValidationError("The Tax Category Code are not configured with the Taxes %s." % (tax_obj.name))
                else:
                    orderline.write({'tax_id': False})
                    print("orderline.tax_id ==",orderline.tax_id)
                if not so_id.partner_id.peppol_identifier:
                    raise ValidationError("Peppol Identifier for Customer %s is not defined." % (so_id.partner_id.name))
                sender_peppol_id = self.extracted_senderid.split(":")[1]
                if so_id.partner_id.peppol_identifier.lower() != sender_peppol_id.lower():
                    raise ValidationError("Customer's Peppol identifier does not match. Mapping cannot be allowed.")
                mapped_orderlines = []
                print('\n\n\nqueue_obj', self)
                for line in self.order_line_ids:
                    for orderline in so_id.order_line:
                        if line.quantity == orderline.product_uom_qty and line.price_amount == orderline.price_unit and line.id not in mapped_orderlines:
                            mapped_orderlines.append(orderline.id)
                if len(mapped_orderlines) != len(self.order_line_ids.ids):
                    raise ValidationError("The Order lines does not match. Mapping cannot be allowed.")
                print("obj.amount_untaxed ==",so_id.amount_untaxed)
                print("obj.amount_total ==",so_id.amount_total)
                print("queue_obj.amt_untaxed ==",self.amt_untaxed)
                if so_id.amount_untaxed != self.amt_untaxed and self.document_type == 'initial':
                    raise ValidationError("The Total Untaxed Amount does not match. Mapping cannot be allowed.")
                # if so_id.amount_total != queue_obj.amt_including_tax and self.document_type == 'order':
                #     raise ValidationError("The Total Amount does not match. Mapping cannot be allowed.")
                self.write({
                    'so_id': so_id.id,
                    'message': "Sale Order mapped successfully!",
                    'state': 'success'})

                if self.payment_terms and not so_id.payment_term_id:
                    pobjs = self.env['account.payment.term'].sudo().search([('name', 'ilike', self.payment_terms)], limit=1)
                    print("pobjs ==",pobjs)
                    if pobjs:
                        so_id.write({'payment_term_id': pobjs.id})
                    else:
                        so_id.payment_term_id = self.env['account.payment.term'].sudo().create({'name': self.payment_terms}).id
                if self.note:
                    so_id.note = so_id.note +'\n'+ self.note
            print('\n\nso_id', so_id)
            return {
                'name': _('Sale Order'),
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': so_id.id,
                'target': 'current',  # or 'new' to open in popup
            }
        # return {
        #     'name': _('Order Note'),
        #     'type': 'ir.actions.act_window',
        #     'res_model': 'order.reason.note.wizard',
        #     'view_mode': 'form',
        #     'target': 'new',
        #     'context': {
        #         'active_id': self.id,
        #         'active_model': self._name,  # = "peppol.queue.in"
        #     }
        # }

        # extracted_senderid = self.extracted_senderid.split(":")[1]
        # partner_ids = self.env['res.partner'].search([('peppol_identifier', 'ilike', extracted_senderid)])
        # sale_order_ids = self.env['sale.order'].search([('partner_id', 'in', partner_ids.ids)])
        #
        # return {
        #     'name': _('Sale Orders'),
        #     'view_mode': 'tree,form',
        #     'views': [(self.env.ref('metro_einvoice_datapost.sale_order_peppol_mapping_list').id, 'tree'),
        #               (self.env.ref('sale.view_order_form').id, 'form')],
        #     'search_view_id': self.env.ref('sale.view_sales_order_filter').id,
        #     'res_model': 'sale.order',
        #     'domain': [('id', 'in', sale_order_ids.ids)],
        #     'type': 'ir.actions.act_window',
        # }

    # order reponse out
    def action_order_response_out(self):
        maped_so = self.env['sale.order'].search([('incoming_order_id', '=', self.id)])
        #if self.state not in  ['cancelled'] and not maped_so:
        #    raise ValidationError(_("Before Send Response first match with the order."))
        return {
            'name': _('Order Response'),
            'res_model': 'order.response.prefill.status',
            'view_mode': 'form',
            'context': {
                'active_model': 'order.queue.in',
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    # balance order incoming oreder query code
    def query_balance_order_receive_documents(self):
        for access_point in self.env['peppol.access.point.sg'].sudo().search([('company_id', '=', self.env.company.id)]):
            print('\n\n\n\naccess_point', access_point)
            base_url = access_point.endpoint
            api_version = access_point.api_version
            receiver_peppol_id = access_point.company_id.peppol_scheme + ':' + access_point.company_id.peppol_identifier
            # receiver_peppol_id = '0195:SGTST202039751G'
            timeout = self.env['ir.config_parameter'].sudo().get_param('api_timeout', default='20')
            headers = {
                # "Accept": "*/*",
                "Authorization": f"Bearer {access_point.access_token}",
                # TODO: Don't calculate but instead calculate and store as one time.
            }
            print('\n\n\n\nreceiver_peppol_id', receiver_peppol_id)
            try:
                status_code, response_data = 'None', ''
                response = requests.get(
                    '%s/api/business/%s/order-balance?receiver=%s' % (base_url, api_version, receiver_peppol_id),
                    headers=headers)
                status_code = response.status_code
                try:
                    response_data = json.loads(response.text)
                except:
                    response_data = response.text
                print("orders = response_data ===",response_data)
                print("isinstance(response_data, dict) ==",isinstance(response_data, dict))
                print("status_code ==",status_code)
                if status_code == 200 and isinstance(response_data, dict):
                    for resp_dic in response_data['info']:
                        self._create_incoming_order_balance_record(resp_dic, {'base_url': base_url, 'api_version': api_version,
                                                                'headers': headers, 'timeout': timeout},
                                                     company_id=access_point.company_id.id,
                                                     access_point_id=access_point.id)
                else:
                    vals = {
                        'status_code': status_code,
                        'response_body': response_data,
                        'doc_type': 'orders'
                    }
                    self.env['incoming.failed.logs'].create(vals)

            except ConnectionError as e:
                _logger.exception(
                    "ConnectionError arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e))
                vals = {
                    'status_code': status_code,
                    'response_body': response_data,
                    'error_body': "ConnectionError arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e),
                    'traceback_body': traceback.format_exc(),
                    'doc_type': 'orders'
                }
                self.env['incoming.failed.logs'].create(vals)
            except Exception as e:
                _logger.exception(
                    "An Exception arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e))
                vals = {
                    'status_code': status_code,
                    'response_body': response_data,
                    'error_body': "An Exception arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e),
                    'traceback_body': traceback.format_exc(),
                    'doc_type': 'orders'
                }
                self.env['incoming.failed.logs'].create(vals)

    def _create_incoming_order_balance_record(self, resp_dic, api_dic, company_id, access_point_id):
        # if self.search([('order_no', '=', resp_dic.get('documentNo', '').strip())]):
        #     return
        company_obj = False
        if resp_dic.get('receiver'):
            receiver_peppol_id = resp_dic.get('receiver').strip().split(":")[1]
            company_obj = self.env['res.company'].sudo().search(['|',('peppol_identifier','=',receiver_peppol_id), ('peppol_identifier','ilike',receiver_peppol_id)], limit=1)
        obj = self.create({
            'status_message': resp_dic.get('statusMessage'),
            'invalidated': 'yes' if resp_dic.get('invalidated') == True else 'no',
            'extracted_senderid': resp_dic.get('sender').strip(),
            'extracted_receiverid': resp_dic.get('receiver').strip(),
            'extracted_totamount': resp_dic.get('amount'),
            'extracted_docno': resp_dic.get('documentNo').strip(),
            'instance_id': resp_dic.get('instanceId'),
            'client_ref': resp_dic.get('clientRef'),
            'order_no': resp_dic.get('documentNo').strip(),
            'received': True,
            'company_id': company_obj and company_obj.id or False,
            'access_point_id': access_point_id,
            'document_type': 'balance',
        })

        try:
            response = requests.get('%s/api/business/%s/order-balance/%s' % (api_dic['base_url'],
                                                                        api_dic['api_version'],
                                                                        urllib.parse.quote(resp_dic.get('clientRef'), safe="")
                                                                        ),
                                    headers=api_dic['headers'],
                                    timeout=int(api_dic['timeout']))
            status_code = response.status_code
            try:
                response_data = json.loads(response.text)
            except:
                response_data = response.text
            if status_code == 200:
                obj._parse_xml_order_balance_data(response_data)
            else:
                extra_msg = ''
                if isinstance(response_data, dict) and response_data.get('message'):
                    extra_msg = response_data.get('message')
                obj.write({'state': 'error',
                           'message': "{} {}\n{}".format(status_code, ERROR_RESPONSES_DIC.get(status_code, ''),
                                                         extra_msg)})
                obj.message_post(body=_("<b>Download Document API responded as {} {}</b><br/>{}".format(status_code,
                                                                                                        ERROR_RESPONSES_DIC.get(
                                                                                                            status_code,
                                                                                                            ''),
                                                                                                        response_data)))
        except ConnectionError as e:
            _logger.exception(
                "ConnectionError arised while performing the 'Download Incoming Doc API' GET requests:\n %s" % repr(e))
        except Exception as e:
            _logger.exception(
                "An Exception arised while performing the 'Download Incoming Doc API' GET requests:\n %s" % repr(e))
            obj.write({
                'state': 'error',
                'message': 'Critical Error.\nFind more details under the Technical tab.',
                'error_exception': repr(e) + "\nTraceback::" + traceback.format_exc(),
            })

    def _parse_xml_order_balance_data(self, xml_str):
        print("\n\n >>>>>  _parse_xml_order_data() >>>>>>")
        cbc = "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}"
        cac = "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}"
        vals = {'xml_data': xml_str,
                'state': 'sent_to_process'}
        myroot = ET.fromstring(xml_str)
        try:
            payment_str = ''
            order_lines = []
            for x in myroot[1]:
                print("x.tag ==", x.tag)
                if x.tag == cbc + 'ID':  # <cbc:ID>
                    vals.update({'order_no': x.text})
                    print('\n\n\n\nvals', vals)
                if x.tag == cbc + 'IssueDate':  # <cbc:IssueDate>
                    vals.update({'issue_date': x.text})
                # if x.tag == cbc + 'DueDate':  # <cbc:DueDate>
                #     vals.update({'due_date': x.text})
                if x.tag == cbc + 'OrderTypeCode':  # <cbc:InvoiceTypeCode>
                    vals.update({'order_type_code': x.text})
                if x.tag == cbc + 'Note':  # <cbc:Note>
                    vals.update({'note': x.text})
                if x.tag == cbc + 'DocumentCurrencyCode':  # <cbc:DocumentCurrencyCode>
                    currency_obj = self.env['res.currency'].sudo().search([('name', '=', x.text.strip())], limit=1)
                    vals.update({'document_currency_code': x.text,
                                 'currency_id': currency_obj and currency_obj.id or False})
                # if x.tag == cac + 'ValidityPeriod':
                #     for child in x:
                #         if child.tag == cbc + 'EndDate':
                #             vals.update({'validity_date': child.text})
                # if x.tag == cbc + 'SalesOrderID':  # <cbc:SalesOrderID>
                #     vals.update({'sale_order_ref': x.text})
                if x.tag == cbc + 'CustomerReference':  # <cbc:BuyerReference>
                    vals.update({'buyer_reference': x.text})
                if x.tag == cac + 'OrderDocumentReference':  # <cac:OrderReference>
                    for child in x:
                        if child.tag == cbc + 'ID':
                            vals.update({'order_reference': child.text})
                if x.tag == cac + 'BuyerCustomerParty':  # <cac:AccountingSupplierParty>
                    for child in x:
                        if child.tag == cac + 'Party':  # <cac:Party>
                            for subchild in child:
                                if subchild.tag == cac + 'PartyLegalEntity':  # <cac:PartyName>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'RegistrationName':  # <cbc:Name>
                                            vals.update({'sender_party_name': subchild_1.text})
                                # TODO: Party Legal Entity
                                if subchild.tag == cac + 'Contact':  # <cac:Contact>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'Name':
                                            vals.update({'sender_contact_name': subchild_1.text})
                                        if subchild_1.tag == cbc + 'ElectronicMail':
                                            vals.update({'sender_contact_email': subchild_1.text})
                                        if subchild_1.tag == cbc + 'Telephone':
                                            vals.update({'sender_contact_phone': subchild_1.text})

                if x.tag == cac + 'AnticipatedMonetaryTotal':  # <cac:AnticipatedMonetaryTotal>
                    for child in x:
                        if child.tag == cbc + 'LineExtensionAmount':
                            vals.update({'amt_untaxed': child.text})
                        if child.tag == cbc + 'PayableAmount':
                            vals.update({'amt_including_tax': child.text})
                if x.tag == cac + 'PaymentTerms':  # <cac:PaymentTerms>
                    for child in x:
                        if child.tag == cbc + 'Note':
                            vals.update({'payment_terms': child.text})
                if x.tag == cac + 'OrderLine':  # <cac:OrderLine>
                    lines_dic = {}
                    for ch in x:
                        if ch.tag == cbc + 'Note':
                            lines_dic.update({'note': ch.text})
                        if ch.tag == cac + 'LineItem':
                            print("ch.tag ==", ch.tag)
                            for child in ch:
                                if child.tag == cbc + 'ID':
                                    lines_dic.update({'line_item_id': child.text})
                                if child.tag == cbc + 'Quantity':
                                    attr_dic = child.attrib
                                    print("\nattr_dic ====", attr_dic)
                                    lines_dic.update(
                                        {'quantity': child.text, 'unit_code': attr_dic.get('unitCode', '')})
                                if child.tag == cbc + 'LineExtensionAmount':
                                    lines_dic.update({'amount_excluding_tax': child.text})
                                # if child.tag == cac + 'AllowanceCharge':
                                #     print("child.tag ==", child.tag)
                                #     for child_1 in child:
                                #         print("child_1.tag == cbc + 'ChargeIndicator'",
                                #               child_1.tag == cbc + 'ChargeIndicator')
                                #         print("child_1.text == True", child_1.text == True)
                                #         if child_1.tag == cbc + 'ChargeIndicator' and child_1.text == True:  # IF it is a charge, then avoid.
                                #             break
                                #         if child_1.tag == cbc + 'Amount':
                                #             lines_dic.update({'allowance_charges': child_1.text})
                                if child.tag == cac + 'Price':
                                    price_amount, base_qty = 0.0, 1
                                    for child_1 in child:
                                        if child_1.tag == cbc + 'PriceAmount':
                                            price_amount = float(child_1.text)
                                        # if child_1.tag == cbc + 'BaseQuantity':
                                        #     base_qty = int(child_1.text)

                                    if price_amount > 0.0:
                                        lines_dic.update({'price_amount': price_amount})
                                if child.tag == cac + 'Item':
                                    for child_1 in child:
                                        if child_1.tag == cbc + 'Name':
                                            lines_dic.update({'name': child_1.text})
                                        # if child_1.tag == cbc + 'Description':
                                        #     lines_dic.update({'description': child_1.text})
                                        # if child_1.tag == cac + 'BuyersItemIdentification':
                                        #     for child_1_1 in child_1:
                                        #         if child_1_1.tag == cbc + 'ID':
                                        #             lines_dic.update({'buyers_item_identification': child_1_1.text})
                                        # if child_1.tag == cac + 'SellersItemIdentification':
                                        #     for child_1_1 in child_1:
                                        #         if child_1_1.tag == cbc + 'ID':
                                        #             lines_dic.update({'sellers_item_identification': child_1_1.text})
                                        # if child_1.tag == cbc + 'ManufacturersItemIdentification':
                                        #     for child_1_1 in child_1:
                                        #         if child_1_1.tag == cbc + 'ID':
                                        #             lines_dic.update(
                                        #                 {'manufacturers_item_identification': child_1_1.text})
                                        # if child_1.tag == cbc + 'StandardItemIdentification':
                                        #     for child_1_1 in child_1:
                                        #         if child_1_1.tag == cbc + 'ID':
                                        #             lines_dic.update({'standard_item_identification': child_1_1.text})
                                        # if child_1.tag == cbc + 'CommodityClassification':
                                        #     for child_1_1 in child_1:
                                        #         if child_1_1.tag == cbc + 'ItemClassificationCode':
                                        #             lines_dic.update({'item_classification_identifier': child_1_1.text})
                                        # if child_1.tag == cac + 'ClassifiedTaxCategory':
                                        #     for child_1_1 in child_1:
                                        #         if child_1_1.tag == cbc + 'Percent':
                                        #             lines_dic.update({'tax_percentage': child_1_1.text})
                                        #         if child_1_1.tag == cbc + 'ID':
                                        #             lines_dic.update({'tax_category_code': child_1_1.text})
                                        #         if child_1_1.tag == cac + 'TaxScheme':
                                        #             for child_1_1_1 in child_1_1:
                                        #                 if child_1_1_1.tag == cbc + 'ID':
                                        #                     lines_dic.update({'tax_type': child_1_1_1.text})
                    if lines_dic:
                        order_lines.append((0, 0, lines_dic))

            order_lines and vals.update({'order_line_ids': order_lines})
            if 'sale_order_ref' in vals:
                sale_obj = self.env['sale.order'].sudo().search(
                    [('name', '=', vals.get('sale_order_ref'))])
                if sale_obj:
                    vals.update({
                        'so_id': sale_obj.id,
                        'message': "The Buyer issued Sale Order is mapped successfully!",
                        'state': 'success',
                    })
                else:
                    vals.update({
                        'message': "The Buyer issued Sale Order '%s' is not found in the database. Please either map or create the new Order." % (
                            vals.get('sale_order_ref', '')),
                        'state': 'sent_to_process'
                    })

            vals.update({
                'state': 'sent_to_process'
            })
            self.write(vals)

        except Exception as e:
            self.write({
                'state': 'error',
                'message': 'Critical Error.\nFind more details under the Technical tab.',
                'error_exception': repr(e) + "\nTraceback::" + traceback.format_exc(),
            })

    # change order incoming oreder query code
    def query_change_order_receive_documents(self):
        for access_point in self.env['peppol.access.point.sg'].sudo().search([('company_id', '=', self.env.company.id)]):
            print('\n\n\n\naccess_point', access_point)
            base_url = access_point.endpoint
            api_version = access_point.api_version
            receiver_peppol_id = access_point.company_id.peppol_scheme + ':' + access_point.company_id.peppol_identifier
            # invoice_no = "P00196"
            timeout = self.env['ir.config_parameter'].sudo().get_param('api_timeout', default='20')
            headers = {
                # "Accept": "*/*",
                "Authorization": f"Bearer {access_point.access_token}",
                # TODO: Don't calculate but instead calculate and store as one time.
            }
            try:
                status_code, response_data = 'None', ''
                response = requests.get(
                    '%s/api/business/%s/order-change?receiver=%s' % (base_url, api_version, receiver_peppol_id),
                    headers=headers)
                status_code = response.status_code
                try:
                    response_data = json.loads(response.text)
                except:
                    response_data = response.text
                print("orders chanage = response_data ===", response_data)
                print("isinstance(response_data, dict) ==",isinstance(response_data, dict))
                print("status_code chnage ord ==", status_code)
                if status_code == 200 and isinstance(response_data, dict):
                    for resp_dic in response_data['info']:
                        self._create_incoming_order_change_record(resp_dic, {'base_url': base_url, 'api_version': api_version,
                                                                'headers': headers, 'timeout': timeout},
                                                     company_id=access_point.company_id.id,
                                                     access_point_id=access_point.id)
                else:
                    vals = {
                        'status_code': status_code,
                        'response_body': response_data,
                        'doc_type': 'orders'
                    }
                    self.env['incoming.failed.logs'].create(vals)

            except ConnectionError as e:
                _logger.exception(
                    "ConnectionError arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e))
                vals = {
                    'status_code': status_code,
                    'response_body': response_data,
                    'error_body': "ConnectionError arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e),
                    'traceback_body': traceback.format_exc(),
                    'doc_type': 'orders'
                }
                self.env['incoming.failed.logs'].create(vals)
            except Exception as e:
                _logger.exception(
                    "An Exception arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e))
                vals = {
                    'status_code': status_code,
                    'response_body': response_data,
                    'error_body': "An Exception arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e),
                    'traceback_body': traceback.format_exc(),
                    'doc_type': 'orders'
                }
                self.env['incoming.failed.logs'].create(vals)

    def _create_incoming_order_change_record(self, resp_dic, api_dic, company_id, access_point_id):
        if self.search([('order_no', '=', resp_dic.get('documentNo', '').strip())]):
            return
        company_obj = False
        if resp_dic.get('receiver'):
            receiver_peppol_id = resp_dic.get('receiver').strip().split(":")[1]
            company_obj = self.env['res.company'].sudo().search(['|',('peppol_identifier','=',receiver_peppol_id), ('peppol_identifier','ilike',receiver_peppol_id)], limit=1)
        obj = self.create({
            'status_message': resp_dic.get('statusMessage'),
            'invalidated': 'yes' if resp_dic.get('invalidated') == True else 'no',
            'extracted_senderid': resp_dic.get('sender').strip(),
            'extracted_receiverid': resp_dic.get('receiver').strip(),
            'extracted_totamount': resp_dic.get('amount'),
            'extracted_docno': resp_dic.get('documentNo').strip(),
            'instance_id': resp_dic.get('instanceId'),
            'client_ref': resp_dic.get('clientRef'),
            'order_no': resp_dic.get('documentNo').strip(),
            'received': True,
            'company_id': company_obj and company_obj.id or False,
            'access_point_id': access_point_id,
            'document_type': 'variation',
        })

        try:
            response = requests.get('%s/api/business/%s/order-change/%s' % (api_dic['base_url'],
                                                                        api_dic['api_version'],
                                                                        urllib.parse.quote(resp_dic.get('clientRef'), safe="")
                                                                        ),
                                    headers=api_dic['headers'],
                                    timeout=int(api_dic['timeout']))
            status_code = response.status_code
            try:
                response_data = json.loads(response.text)
            except:
                response_data = response.text
            if status_code == 200:
                obj._parse_xml_order_change_data(response_data)
            else:
                extra_msg = ''
                if isinstance(response_data, dict) and response_data.get('message'):
                    extra_msg = response_data.get('message')
                obj.write({'state': 'error',
                           'message': "{} {}\n{}".format(status_code, ERROR_RESPONSES_DIC.get(status_code, ''),
                                                         extra_msg)})
                obj.message_post(body=_("<b>Download Document API responded as {} {}</b><br/>{}".format(status_code,
                                                                                                        ERROR_RESPONSES_DIC.get(
                                                                                                            status_code,
                                                                                                            ''),
                                                                                                        response_data)))
        except ConnectionError as e:
            _logger.exception(
                "ConnectionError arised while performing the 'Download Incoming Doc API' GET requests:\n %s" % repr(e))
        except Exception as e:
            _logger.exception(
                "An Exception arised while performing the 'Download Incoming Doc API' GET requests:\n %s" % repr(e))
            obj.write({
                'state': 'error',
                'message': 'Critical Error.\nFind more details under the Technical tab.',
                'error_exception': repr(e) + "\nTraceback::" + traceback.format_exc(),
            })

    def _parse_xml_order_change_data(self, xml_str):
        print("\n\n >>>>>  _parse_xml_order_data() >>>>>>", xml_str)
        cbc = "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}"
        cac = "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}"
        vals = {'xml_data': xml_str,
                'state': 'sent_to_process'}
        myroot = ET.fromstring(xml_str)
        print('\n\n\n>>>>????my_rootttttttttt', myroot)
        try:
            payment_str = ''
            order_lines = []
            for x in myroot[1]:
                print("x.tag ==", x.tag)
                if x.tag == cbc + 'ID':  # <cbc:ID>
                    vals.update({'order_no': x.text})
                if x.tag == cbc + 'IssueDate':  # <cbc:IssueDate>
                    vals.update({'issue_date': x.text})
                if x.tag == cbc + 'SequenceNumberID':  # <cbc:IssueDate>
                    vals.update({'variation_number': x.text})
                if x.tag == cbc + 'Note':  # <cbc:Note>
                    vals.update({'note': x.text})
                if x.tag == cbc + 'DocumentCurrencyCode':  # <cbc:DocumentCurrencyCode>
                    currency_obj = self.env['res.currency'].sudo().search([('name', '=', x.text.strip())], limit=1)
                    vals.update({'document_currency_code': x.text,
                                 'currency_id': currency_obj and currency_obj.id or False})
                if x.tag == cbc + 'CustomerReference':  # <cbc:BuyerReference>
                    vals.update({'buyer_reference': x.text})
                if x.tag == cac + 'ValidityPeriod':
                    for child in x:
                        if child.tag == cbc + 'EndDate':
                            vals.update({'validity_date': child.text})
                if x.tag == cac + 'OrderReference':  # <cac:OrderReference>
                    for child in x:
                        if child.tag == cbc + 'ID':
                            vals.update({'order_reference': child.text})
                # if x.tag == cac + 'AdditionalDocumentReference': # <cac:AdditionalDocumentReference>
                #     for child in x:
                #         if child.tag == cac + 'Attachment':
                #             for subchild in child:
                #                 if subchild.tag == cbc + 'EmbeddedDocumentBinaryObject':
                #                     attr_dic = subchild.attrib
                #                     vals.update({'document_ids': [(0, 0, {
                #                        'type': 'binary',
                #                        'name': attr_dic.get('filename'),
                #                        'datas': subchild.text,
                #                        'mimetype': attr_dic.get('mimeCode')
                #                    })]})
                if x.tag == cac + 'BuyerCustomerParty':  # <cac:AccountingSupplierParty>
                    for child in x:
                        if child.tag == cac + 'Party':  # <cac:Party>
                            for subchild in child:
                                if subchild.tag == cac + 'PartyName':  # <cac:PartyName>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'Name':  # <cbc:Name>
                                            vals.update({'sender_party_name': subchild_1.text})
                                if subchild.tag == cac + 'PartyLegalEntity':  # <cac:PartyLegalEntity>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cac + 'RegistrationAddress':
                                            for subchild_1_1 in subchild_1:
                                                if subchild_1_1.tag == cbc + 'CityName':
                                                    vals.update({'sender_address_city': subchild_1_1.text})
                                                if subchild_1_1.tag == cac + 'Country':
                                                    for subchild_1_1_1 in subchild_1_1:
                                                        if subchild_1_1_1.tag == cbc + 'IdentificationCode':
                                                            vals.update({'sender_address_country': subchild_1_1_1.text})
                                # TODO: Party Legal Entity
                                if subchild.tag == cac + 'Contact':  # <cac:Contact>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'Name':
                                            vals.update({'sender_contact_name': subchild_1.text})
                                        if subchild_1.tag == cbc + 'ElectronicMail':
                                            vals.update({'sender_contact_email': subchild_1.text})
                                        if subchild_1.tag == cbc + 'Telephone':
                                            vals.update({'sender_contact_phone': subchild_1.text})

                if x.tag == cac + 'Delivery':  # <cac:Delivery>
                    for child in x:
                        if child.tag == cac + 'DeliveryLocation':  # <cac:DeliveryLocation>
                            for subchild in child:
                                if subchild.tag == cac + 'Address':  # <cac:Address>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'StreetName':
                                            vals.update({'delivery_location_street1': subchild_1.text})
                                        if subchild_1.tag == cbc + 'AdditionalStreetName':
                                            vals.update({'delivery_location_street2': subchild_1.text})
                                        if subchild_1.tag == cbc + 'CityName':
                                            vals.update({'delivery_location_city': subchild_1.text})
                                        if subchild_1.tag == cbc + 'PostalZone':
                                            vals.update({'delivery_location_zip': subchild_1.text})
                                        if subchild_1.tag == cac + 'Country':
                                            for subchild_1_1 in subchild_1:
                                                if subchild_1_1.tag == cbc + 'IdentificationCode':
                                                    vals.update({'delivery_location_country': subchild_1_1.text})

                        if child.tag == cac + 'RequestedDeliveryPeriod':  # <cac:RequestedDeliveryPeriod>
                            for subchild in child:
                                if subchild.tag == cbc + 'StartDate':
                                    vals.update({'requested_delivery_startdate': subchild.text})
                                if subchild.tag == cbc + 'EndDate':
                                    vals.update({'requested_delivery_enddate': subchild.text})
                            # for subchild in child:
                            #     if subchild.tag == cbc + 'StartTime':
                            #         vals['requested_delivery_startdate'] = vals['requested_delivery_startdate'] + ' ' + subchild.text
                            #     if subchild.tag == cbc + 'EndTime':
                            #         vals['requested_delivery_enddate'] = vals['requested_delivery_enddate'] + ' ' + subchild.text

                        if child.tag == cac + 'DeliveryParty':  # <cac:DeliveryParty>
                            for subchild in child:
                                # if subchild.tag == cac + 'PartyIdentification':  # <cbc:PartyIdentification>
                                #     for subchild_1 in subchild:
                                #         if subchild_1.tag == cbc + 'ID':  # <cbc:ID>
                                #             vals.update({'delivery_party_id': subchild_1.text})
                                if subchild.tag == cac + 'PartyName':  # <cac:PartyName>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'Name':  # <cbc:Name>
                                            vals.update({'delivery_party_name': subchild_1.text})
                                # TODO: Party Legal Entity
                                if subchild.tag == cac + 'Contact':  # <cac:Contact>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'Name':
                                            vals.update({'delivery_party_contact_name': subchild_1.text})
                                        if subchild_1.tag == cbc + 'ElectronicMail':
                                            vals.update({'delivery_party_contact_email': subchild_1.text})
                                        if subchild_1.tag == cbc + 'Telephone':
                                            vals.update({'delivery_party_contact_phone': subchild_1.text})
                if x.tag == cac + 'PaymentTerms':  # <cac:PaymentTerms>
                    for child in x:
                        if child.tag == cbc + 'Note':
                            vals.update({'payment_terms': child.text})
                if x.tag == cac + 'TaxTotal':  # <cac:TaxTotal>
                    for child in x:
                        if child.tag == cbc + 'TaxAmount':
                            vals.update({'taxed_amt': child.text})
                            break

                if x.tag == cac + 'AnticipatedMonetaryTotal':  # <cac:AnticipatedMonetaryTotal>
                    for child in x:
                        if child.tag == cbc + 'TaxExclusiveAmount':
                            vals.update({'amt_untaxed': child.text})
                        if child.tag == cbc + 'PayableAmount':
                            vals.update({'amt_including_tax': child.text})

                if x.tag == cac + 'OrderLine':  # <cac:OrderLine>
                    lines_dic = {}
                    for ch in x:
                        if ch.tag == cac + 'LineItem':
                            print("ch.tag ==", ch.tag)
                            for child in ch:
                                if child.tag == cbc + 'ID':
                                    lines_dic.update({'line_item_id': child.text})
                                if child.tag == cbc + 'Quantity':
                                    attr_dic = child.attrib
                                    print("\nattr_dic ====", attr_dic)
                                    lines_dic.update(
                                        {'quantity': child.text, 'unit_code': attr_dic.get('unitCode', '')})
                                if child.tag == cbc + 'LineExtensionAmount':
                                    lines_dic.update({'amount_excluding_tax': child.text})
                                # if child.tag == cac + 'AllowanceCharge':
                                # 	print("child.tag ==",child.tag)
                                # 	for child_1 in child:
                                # 		print("child_1.tag == cbc + 'ChargeIndicator'", child_1.tag == cbc + 'ChargeIndicator')
                                # 		print("child_1.text == True", child_1.text == True)
                                # 		if child_1.tag == cbc + 'ChargeIndicator' and child_1.text == True: # IF it is a charge, then avoid.
                                # 			break
                                # 		if child_1.tag == cbc + 'Amount':
                                # 			lines_dic.update({'allowance_charges': child_1.text})
                                if child.tag == cac + 'Price':
                                    price_amount, base_qty = 0.0, 1
                                    for child_1 in child:
                                        if child_1.tag == cbc + 'PriceAmount':
                                            price_amount = float(child_1.text)
                                        # if child_1.tag == cbc + 'BaseQuantity':
                                        #     base_qty = int(child_1.text)

                                    if price_amount > 0.0:
                                        lines_dic.update({'price_amount': price_amount})
                                if child.tag == cac + 'Item':
                                    for child_1 in child:
                                        if child_1.tag == cbc + 'Name':
                                            lines_dic.update({'name': child_1.text})
                                        if child_1.tag == cbc + 'Description':
                                            lines_dic.update({'description': child_1.text})
                                        if child_1.tag == cac + 'ClassifiedTaxCategory':
                                            for child_1_1 in child_1:
                                                if child_1_1.tag == cbc + 'Percent':
                                                    lines_dic.update({'tax_percentage': child_1_1.text})
                                                if child_1_1.tag == cbc + 'ID':
                                                    lines_dic.update({'tax_category_code': child_1_1.text})
                                                if child_1_1.tag == cac + 'TaxScheme':
                                                    for child_1_1_1 in child_1_1:
                                                        if child_1_1_1.tag == cbc + 'ID':
                                                            lines_dic.update({'tax_type': child_1_1_1.text})
                    if lines_dic:
                        order_lines.append((0, 0, lines_dic))

            order_lines and vals.update({'order_line_ids': order_lines})
            if 'sale_order_ref' in vals:
                sale_obj = self.env['sale.order'].sudo().search(
                    [('name', '=', vals.get('sale_order_ref'))])
                if sale_obj:
                    vals.update({
                        'so_id': sale_obj.id,
                        'message': "The Buyer issued Sale Order is mapped successfully!",
                        'state': 'success',
                    })
                else:
                    vals.update({
                        'message': "The Buyer issued Sale Order '%s' is not found in the database. Please either map or create the new Order." % (
                            vals.get('sale_order_ref', '')),
                        'state': 'sent_to_process'
                    })

            vals.update({
                'state': 'sent_to_process'
            })
            self.write(vals)

        except Exception as e:
            self.write({
                'state': 'error',
                'message': 'Critical Error.\nFind more details under the Technical tab.',
                'error_exception': repr(e) + "\nTraceback::" + traceback.format_exc(),
            })

    # cancel order incoming oreder query code
    def query_cancel_order_receive_documents(self):
        for access_point in self.env['peppol.access.point.sg'].sudo().search([('company_id', '=', self.env.company.id)]):
            base_url = access_point.endpoint
            api_version = access_point.api_version
            receiver_peppol_id = access_point.company_id.peppol_scheme + ':' + access_point.company_id.peppol_identifier
            # invoice_no = "P00194"
            timeout = self.env['ir.config_parameter'].sudo().get_param('api_timeout', default='20')
            headers = {
                # "Accept": "*/*",
                "Authorization": f"Bearer {access_point.access_token}",
                # TODO: Don't calculate but instead calculate and store as one time.
            }
            try:
                status_code, response_data = 'None', ''
                response = requests.get(
                    '%s/api/business/%s/order-cancellation?receiver=%s' % (base_url, api_version, receiver_peppol_id),
                    headers=headers)
                status_code = response.status_code
                try:
                    response_data = json.loads(response.text)
                except:
                    response_data = response.text
                print("orders = response_data ===",response_data)
                print("isinstance(response_data, dict) ==",isinstance(response_data, dict))
                print("status_code ==",status_code)
                if status_code == 200 and isinstance(response_data, dict):
                    for resp_dic in response_data['info']:
                        self._create_incoming_order_cancel_record(resp_dic, {'base_url': base_url, 'api_version': api_version,
                                                                'headers': headers, 'timeout': timeout},
                                                     company_id=access_point.company_id.id,
                                                     access_point_id=access_point.id)
                else:
                    vals = {
                        'status_code': status_code,
                        'response_body': response_data,
                        'doc_type': 'orders'
                    }
                    self.env['incoming.failed.logs'].create(vals)

            except ConnectionError as e:
                _logger.exception(
                    "ConnectionError arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e))
                vals = {
                    'status_code': status_code,
                    'response_body': response_data,
                    'error_body': "ConnectionError arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e),
                    'traceback_body': traceback.format_exc(),
                    'doc_type': 'orders'
                }
                self.env['incoming.failed.logs'].create(vals)
            except Exception as e:
                _logger.exception(
                    "An Exception arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e))
                vals = {
                    'status_code': status_code,
                    'response_body': response_data,
                    'error_body': "An Exception arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e),
                    'traceback_body': traceback.format_exc(),
                    'doc_type': 'orders'
                }
                self.env['incoming.failed.logs'].create(vals)

    def _create_incoming_order_cancel_record(self, resp_dic, api_dic, company_id, access_point_id):
        if self.search([('order_no', '=', resp_dic.get('documentNo', '').strip())]):
            return
        company_obj = False
        if resp_dic.get('receiver'):
            receiver_peppol_id = resp_dic.get('receiver').strip().split(":")[1]
            company_obj = self.env['res.company'].sudo().search(['|',('peppol_identifier','=',receiver_peppol_id), ('peppol_identifier','ilike',receiver_peppol_id)], limit=1)
        obj = self.create({
            'status_message': resp_dic.get('statusMessage'),
            'invalidated': 'yes' if resp_dic.get('invalidated') == True else 'no',
            'extracted_senderid': resp_dic.get('sender').strip(),
            'extracted_receiverid': resp_dic.get('receiver').strip(),
            'extracted_totamount': resp_dic.get('amount'),
            'extracted_docno': resp_dic.get('documentNo').strip(),
            'instance_id': resp_dic.get('instanceId'),
            'client_ref': resp_dic.get('clientRef'),
            'order_no': resp_dic.get('documentNo').strip(),
            'received': True,
            'company_id': company_obj and company_obj.id or False,
            'access_point_id': access_point_id,
            'document_type': 'cancel',
            'state': 'cancelled',
        })

        try:
            response = requests.get('%s/api/business/%s/order-cancellation/%s' % (api_dic['base_url'],
                                                                        api_dic['api_version'],
                                                                        urllib.parse.quote(resp_dic.get('clientRef'), safe="")
                                                                        ),
                                    headers=api_dic['headers'],
                                    timeout=int(api_dic['timeout']))
            status_code = response.status_code
            try:
                response_data = json.loads(response.text)
            except:
                response_data = response.text
            if status_code == 200:
                obj._parse_xml_order_cancel_data(response_data)
            else:
                extra_msg = ''
                if isinstance(response_data, dict) and response_data.get('message'):
                    extra_msg = response_data.get('message')
                obj.write({'state': 'error',
                           'message': "{} {}\n{}".format(status_code, ERROR_RESPONSES_DIC.get(status_code, ''),
                                                         extra_msg)})
                obj.message_post(body=_("<b>Download Document API responded as {} {}</b><br/>{}".format(status_code,
                                                                                                        ERROR_RESPONSES_DIC.get(
                                                                                                            status_code,
                                                                                                            ''),
                                                                                                        response_data)))
        except ConnectionError as e:
            _logger.exception(
                "ConnectionError arised while performing the 'Download Incoming Doc API' GET requests:\n %s" % repr(e))
        except Exception as e:
            _logger.exception(
                "An Exception arised while performing the 'Download Incoming Doc API' GET requests:\n %s" % repr(e))
            obj.write({
                'state': 'error',
                'message': 'Critical Error.\nFind more details under the Technical tab.',
                'error_exception': repr(e) + "\nTraceback::" + traceback.format_exc(),
            })

    def _parse_xml_order_cancel_data(self, xml_str):
        print("\n\n >>>>>  _parse_xml_order_data() >>>>>>")
        cbc = "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}"
        cac = "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}"
        vals = {'xml_data': xml_str,
                'state': 'sent_to_process'}
        myroot = ET.fromstring(xml_str)
        # order_cancel_node = None
        # for node in myroot:
        #     if "OrderCancellation" in node.tag:
        #         order_cancel_node = node
        #         break
        #
        # if not order_cancel_node:
        #     print("❌ No OrderCancellation node found!")
        #     return vals
        try:
            payment_str = ''
            order_lines = []
            for x in myroot[1]:
                print("x.tag ==",x.tag)
                if x.tag == cbc + 'ID':  # <cbc:ID>
                    vals.update({'order_no': x.text})
                if x.tag == cbc + 'IssueDate':  # <cbc:IssueDate>
                    vals.update({'issue_date': x.text})
                if x.tag == cbc + 'CancellationNote':  # <cbc:Note>
                    vals.update({'note': x.text})
                if x.tag == cac + 'OrderReference':  # <cac:OrderReference>
                    for child in x:
                        if child.tag == cbc + 'ID':
                            vals.update({'order_reference': child.text})

                if x.tag == cac + 'BuyerCustomerParty':  # <cac:AccountingSupplierParty>
                    for child in x:
                        if child.tag == cac + 'Party':  # <cac:Party>
                            for subchild in child:
                                if subchild.tag == cac + 'PartyLegalEntity':  # <cac:PartyName>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'RegistrationName':  # <cbc:Name>
                                            vals.update({'sender_party_name': subchild_1.text})
            vals.update({
                'state': 'sent_to_process'
            })
            self.write(vals)

        except Exception as e:
            self.write({
                'state': 'error',
                'message': 'Critical Error.\nFind more details under the Technical tab.',
                'error_exception': repr(e) + "\nTraceback::" + traceback.format_exc(),
            })

class IncomingOrderLines(models.Model):
    _name = "incoming.order.lines"
    _description = "Incoming Order Lines"

    parent_id = fields.Many2one('order.queue.in', 'Parent')
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
    note = fields.Text('Note')
    buyers_item_identification = fields.Char('Buyers Item Identifier')
    sellers_item_identification = fields.Char('Sellers Item Identifier')
    manufacturers_item_identification = fields.Char('Manufacturers Item Identifier')
    standard_item_identification = fields.Char('Standard Item Identifier')
    item_classification_identifier = fields.Char('Item Classification Identifier')
    discount_rate = fields.Char('Discount %')
    unit_code = fields.Char('Unit Code')
    line_item_id = fields.Char("Line item ID")
    issue_date = fields.Date("Issue Date")
