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

class OrderCancelResponsesQueueIn(models.Model):
    _name = "order.cancel.responses.queue.in"
    _description = "Incoming Order Responses Queue"
    _rec_name = "order_no" 
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    message = fields.Text(string="Message", readonly=True, tracking=True)
    state = fields.Selection(SELECTION_PEPPOL_QUEUE_IN_STATE, string="Status", readonly=True, tracking=True,
                             default='received')
    name = fields.Char(string="Name", store=True, readonly=True)    
    order_no = fields.Char('Order No', readonly=True)
    order_queue_out_id = fields.Many2one("order.cancel.queue.out", string="Related Document", readonly=True)
   
    order_id = fields.Many2one("purchase.order", related='order_queue_out_id.order_id', string="Order")
    partner_id = fields.Many2one('res.partner', related='order_queue_out_id.order_id.partner_id', string='Vendor')
    company_id = fields.Many2one('res.company', string="Company")
    received = fields.Boolean('Received', help="Used for Technical purpose", readonly=True)
    
    issue_datetime = fields.Datetime(string="Issued On", readonly=True)
    issue_date = fields.Date('Issued On', readonly=True)
    issue_time = fields.Char('Issue Time', readonly=True)
    note = fields.Text(string="Note", readonly=True)
    response_code = fields.Selection([('AB', 'Message acknowledgement'), ('AP', 'Accepted'),('RE', 'Rejected'),
                                ('CA', 'Conditionally accepted')], string="Response", readonly=True)
    effective_date = fields.Date('Effective Date', readonly=True)
    sender_party_id = fields.Char('Sender ID', readonly=True)
    sender_party_name = fields.Char('Sender Party Name', readonly=True)
    sender_party_contact_name = fields.Char('Contact Name', readonly=True)
    sender_party_contact_telephone = fields.Char('Contact Telephone', readonly=True)
    sender_party_contact_email = fields.Char('Contact Email', readonly=True)

    receiver_party_id = fields.Char('Receiver ID', readonly=True)
    receiver_party_name = fields.Char('Receiver Party Name', readonly=True)

    access_point_id = fields.Many2one('peppol.access.point.sg', readonly=True)
    error_exception = fields.Text("Technical Error", readonly=True)
    xml_data = fields.Text("XML Invoice Data", help="For Technical Use only", readonly=True)
    upload_time = fields.Char('Document uploaded/received time', readonly=True)

    extracted_senderid = fields.Char('Sender Peppol ID', help="Sender id extracted from the uploaded xml", tracking=1, readonly=True)
    extracted_receiverid = fields.Char('Receiver Peppol ID', help="Receiver id extracted from the uploaded xml", tracking=1, readonly=True)
    extracted_totamount = fields.Char('Total Amount', help="Document total amount extracted from the uploaded xml",
                                      tracking=1, readonly=True)
    extracted_docno = fields.Char('Document No', help="Document number extracted from the uploaded xml", tracking=1, readonly=True)
    invalidated = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Invalidated Document",
                                   help="true denotes an Invalidated document. Documents become invalidated when a new document with the same Document number received again.",
                                   tracking=1, readonly=True)
    instance_id = fields.Char('Instance ID',
                              help="Generated unique id for the document when sending to the peppol network.", readonly=True)

    status_message = fields.Text('Status Message', default='', tracking=1, help="Detailed description for the status.", readonly=True)
    document_currency_code = fields.Char("Currency Code", help="The ISO 4217 currency for the invoice.") #DocumentCurrencyCode
    currency_id = fields.Many2one("res.currency", string="Currency")



    def _parse_xml_order_response_data(self, xml_str):
        print("_parse_xml_inv_response_data >>>>>>")
        cbc = "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}"
        cac = "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}"
        vals = {'xml_data': xml_str,
                'state': 'sent_to_process'}
        myroot = ET.fromstring(xml_str)
        try:
            order_no = ''
            for x in myroot[1]:
                print("x.tag ==",x.tag)
                if x.tag == cbc + 'ID':  # <cbc:ID>
                    vals.update({'name': x.text})
                if x.tag == cbc + 'IssueDate':  # <cbc:IssueDate>
                    vals.update({'issue_date': x.text})
                if x.tag == cbc + 'IssueTime':  # <cbc:IssueDate>
                    vals.update({'issue_time': x.text})
                if x.tag == cbc + 'OrderResponseCode':  # <cbc:Note>
                    vals.update({'response_code': x.text})
                if x.tag == cbc + 'Note':  # <cbc:Note>
                    vals.update({'note': x.text})
                if x.tag == cbc + 'DocumentCurrencyCode':  # <cbc:DocumentCurrencyCode>
                    currency_obj = self.env['res.currency'].sudo().search([('name', '=', x.text.strip())], limit=1)
                    vals.update({'document_currency_code': x.text,
                                 'currency_id': currency_obj and currency_obj.id or False})

                if x.tag == cac + 'OrderReference':  # <cac:OrderReference>
                    for child in x:
                        if child.tag == cbc + 'ID':
                            order_no = child.text
                            print('\n\n\n\norder_no', order_no)
                            queue_obj = self.env['order.cancel.queue.out'].search([('order_id.name', '=', child.text)],
                                                                            limit=1)
                            if queue_obj:
                                vals.update({'order_queue_out_id': queue_obj.id})


            print("vals ===",vals)
            if 'order_queue_out_id' in vals:
                vals.update({
                    'message': 'This Document mapped successfully!',
                    'state': 'success',
                })
                queue_obj.write({'response_status_code': vals['response_code']})
            else:
                vals.update({
                    'message': "The Document Reference '%s' is not found in the database." % (
                        order_no),
                    'state': 'sent_to_process'
                })
            self.write(vals)

        except Exception as e:
            self.write({
                'state': 'error',
                'message': 'Critical Error.\nPlease read the traceback of the error to identify the issue.',
                'error_exception': repr(e) + "\nTraceback::" + traceback.format_exc(),
            })
            self.message_post(body=_(repr(e) + "<br/>Traceback::" + traceback.format_exc()))

    def _create_incoming_order_response(self, resp_dic, api_dic, company_id, access_point_id):
        if self.search([('extracted_docno', '=', resp_dic.get('documentNo', '').strip())]):
            return
        company_obj = False
        if resp_dic.get('receiver'):
            receiver_peppol_id = resp_dic.get('receiver').strip().split(":")[1]
            company_obj = self.env['res.company'].sudo().search(['|',('peppol_identifier','=',receiver_peppol_id), ('peppol_identifier','ilike',receiver_peppol_id)], limit=1)
        print("company_obj ===", company_obj)
        obj = self.create({
            'status_message': resp_dic.get('statusMessage'),
            'invalidated': 'yes' if resp_dic.get('invalidated') == True else 'no',
            'extracted_senderid': resp_dic.get('sender').strip(),
            'extracted_receiverid': resp_dic.get('receiver').strip(),
            'extracted_totamount': resp_dic.get('amount'),
            'extracted_docno': resp_dic.get('documentNo').strip(),
            'instance_id': resp_dic.get('instanceId'),
            'order_no': resp_dic.get('documentNo').strip(),
            'received': True,
            'company_id': company_obj and company_obj.id or False,
            'access_point_id': access_point_id,            
        })

        try:
            response = requests.get('%s/api/business/%s/order-response-advanced/%s' % (api_dic['base_url'],
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
                obj._parse_xml_order_response_data(response_data)
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
                'message': 'Critical Error.\nPlease read the traceback of the error to identify the issue.',
                'error_exception': repr(e) + "\nTraceback::" + traceback.format_exc(),
            })
            obj.message_post(body=_(repr(e) + "<br/>Traceback::" + traceback.format_exc()))

    def query_cancel_order_res_receive_documents(self):
        for access_point in self.env['peppol.access.point.sg'].sudo().search([('company_id', '=', self.env.company.id)]):
            base_url = access_point.endpoint
            api_version = access_point.api_version
            receiver_peppol_id = access_point.company_id.peppol_scheme + ':' + access_point.company_id.peppol_identifier
            timeout = self.env['ir.config_parameter'].sudo().get_param('api_timeout', default='20')
            receiver_peppol_id = '0195:SGTST201904063K'
            # headers = {
            #     "Accept": "*/*",
            #     "Authorization": "Basic {}".format(access_point.get_basic_auth_token()),
            #     # TODO: Don't calculate but instead calculate and store as one time.
            # }
            headers = {
                # "Accept": "*/*",
                "Authorization": f"Bearer {access_point.access_token}",
                # TODO: Don't calculate but instead calculate and store as one time.
            }
            try:
                status_code, response_data = 'None', ''
                response = requests.get(
                    '%s/api/business/%s/order-response-advanced?receiver=%s' % (base_url, api_version, receiver_peppol_id),
                    headers=headers,
                    timeout=int(timeout))
                status_code = response.status_code
                try:
                    response_data = json.loads(response.text)
                except:
                    response_data = response.text
                print("status_code ==",status_code)
                if status_code == 200 and isinstance(response_data, dict):
                    for resp_dic in response_data['info']:
                        self._create_incoming_order_response(resp_dic, {'base_url': base_url, 'api_version': api_version,
                                                                'headers': headers, 'timeout': timeout},
                                                     company_id=access_point.company_id.id,
                                                     access_point_id=access_point.id)
                else:
                    self.env['incoming.failed.logs'].create({
                        'status_code': status_code,
                        'response_body': response_data,
                    })

            except ConnectionError as e:
                _logger.exception(
                    "ConnectionError arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e))
                self.env['incoming.failed.logs'].create({
                    'status_code': status_code,
                    'response_body': response_data,
                    'error_body': "ConnectionError arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e),
                    'traceback_body': traceback.format_exc(),
                })
            except Exception as e:
                _logger.exception(
                    "An Exception arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e))
                self.env['incoming.failed.logs'].create({
                    'status_code': status_code,
                    'response_body': response_data,
                    'error_body': "An Exception arised while performing the 'Query Documents to Receive API' GET requests:\n %s" % repr(e),
                    'traceback_body': traceback.format_exc(),
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
                response = requests.get('%s/business/%s/order-responses/%s.xml' % (base_url, api_version, urllib.parse.quote(obj.extracted_docno, safe="")),
                                        headers=headers,
                                        timeout=int(timeout))
                status_code = response.status_code
                try:
                    response_data = json.loads(response.text)
                except:
                    response_data = response.text
                print("status_code ==",status_code)
                if status_code == 200:
                    self._parse_xml_inv_response_data(response_data)
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

    def action_cancel(self):
        """ This method will set the state as cancelled. """
        self.write({'state': 'cancelled'})
