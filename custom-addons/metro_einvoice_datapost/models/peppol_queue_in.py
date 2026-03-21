from odoo import fields, models, api, _
import requests
from requests import ConnectionError
import json
import traceback
import logging
import xml.etree.ElementTree as ET
from odoo.exceptions import ValidationError,UserError
import urllib.parse
import re


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


class PeppolQueueIn(models.Model):
    _name = "peppol.queue.in"
    _description = "Incoming Invoices/Credit Notes Queue"
    _rec_name = "invoice_no"
    _order = "create_date desc"
    _inherit = ['mail.thread']

    message = fields.Text(string="Message", readonly=True, tracking=True)
    state = fields.Selection(SELECTION_PEPPOL_QUEUE_IN_STATE, string="Status", readonly=True, tracking=True,
                             default='received')
    move_id = fields.Many2one('account.move', readonly=True, tracking=True)
    error_type = fields.Selection([('partner', 'Partner'), ('product', 'Product'), ('tax', 'Tax')])
    po_id = fields.Many2one('purchase.order', string="Purchase Order", readonly=True)
    company_id = fields.Many2one("res.company", string="Company")
    currency_id = fields.Many2one("res.currency", string="Currency")
    received = fields.Boolean('Received', help="Used for Technical purpose")
    document_ids = fields.Many2many(
        'ir.attachment', 'unmapped_inv_docs_docs_rel', 'peppol_log_id', 'attachment_id',
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
    non_peppol = fields.Char('Non peppol document')
    iras_status = fields.Char("IRAS Status", help="IRAS submission status of the document.")
    iras_statusinfo = fields.Text('IRAS Status Info', help="Additional information relevant to IRAS status.")
    status_message = fields.Text('Status Message', default='', tracking=1, help="Detailed description for the status.")

    sender_party_name = fields.Char("Vendor")
    sender_address_line1 = fields.Char("Vendor Address Line 1")
    sender_address_line2 = fields.Char("Vendor Address Line 2")
    sender_address_city = fields.Char("Vendor City")
    sender_address_county = fields.Char("Vendor County")
    sender_address_zip = fields.Char("Vendor Zip")
    sender_address_country = fields.Char("Vendor Country")

    sender_contact_name = fields.Char(string="Vendor Contact Name")
    sender_contact_phone = fields.Char(string="Vendor Contact Phone")
    sender_contact_email = fields.Char(string="Vendor Contact Email")

    sender_party_tax_scheme_companyid = fields.Char("Vendor Tax Scheme Company Id",
                                                    help="Seller GST identifier, Seller tax registration identifier")
    sender_party_tax_scheme_id = fields.Char("Vendor Tax Scheme Id", help="Seller tax registration identifier")

    note = fields.Text("Note")
    issue_date = fields.Date("Issue Date")
    due_date = fields.Date("Due Date")
    tax_point_date = fields.Date("Tax Point Date")
    document_currency_code = fields.Char("Currency Code", help="The ISO 4217 currency for the invoice.")

    invoice_no = fields.Char(string="Invoice Ref", readonly=True, tracking=True)
    invoice_type_code = fields.Char("Invoice Type Code")
    period_start = fields.Date("Period Start", help="The start date of the period this invoice relates to")
    period_end = fields.Date("Period End", help="The end date of the period this invoice relates to")
    buyer_reference = fields.Char("Buyer Reference", help="Reference provided by the buyer. Used for routing")

    order_reference = fields.Char("Order Reference",
                                  help="Reference to the order. Used for matching the invoice to an order")

    payment_terms = fields.Text('Payment Terms')
    payment_means = fields.Text('Payment Means')

    invoice_line_ids = fields.One2many("incoming.invoice.lines", "parent_id", "Invoice Lines")

    amt_including_tax = fields.Float("Total")
    amt_untaxed = fields.Float("Untaxed Amount")
    taxed_amt = fields.Float("Tax")
    discount_amt = fields.Float("Discount Amount")
    doc_type = fields.Selection([('invoices', 'Invoices'),('credit-notes', 'Credit Notes')], string='Doc Type')
    doc_type_code = fields.Char(compute='_compute_doc_type_code', string='Doc Type Code')

    invoice_response_out_ids = fields.Many2many('invoice.responses.queue.out', string="Responses") # 'inv_queue_in_resp_rel', 'queue_in', 'response_out_id'
    sent_inv_responses_count = fields.Integer(string="Sent Invoice Responses Count",compute="_compute_invoice_response_count")
    convert_to_purchase_invoice_bill = fields.Selection(
        [('PO', 'PO'), ('Direct', 'Direct')],
        string='Convert to Purchase Invoice/Bill',
        related="company_id.convert_to_purchase_invoice_bill")
    uen_no = fields.Char(string="UEN No")
    is_gst_register = fields.Boolean(string="Is GST Register")
    registered_name = fields.Char(string="Registered Name")
    registration_id = fields.Char(string="Registration ID")
    registered_from = fields.Date(string="Registered From")
    registration_status = fields.Selection([
        ('registered', 'Registered'),
        ('unregistered', 'Unregistered')
    ], string="GST Registration Status")
    remark = fields.Text(string="Remarks")
    return_code = fields.Char(string="Return Code")
    client_ref = fields.Char('Client Ref')
    gst_no = fields.Char(string="GST No")

    
    def _compute_invoice_response_count(self):
        for rec in self:
            invoice_response_count = self.env['invoice.responses.queue.out'].search_count(
                [('source_doc_id', '=', rec.id)])
            rec.sent_inv_responses_count = invoice_response_count

    def action_view_invoice_response_queue_out(self):
        if self.doc_type == 'invoices':
            name = 'Outgoing Invoice Responses'
        else:
            name = 'Outgoing Credit Notes Responses'
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'invoice.responses.queue.out',
            'domain': [('source_doc_id', '=', self.ids)],
            'view_mode': 'tree,form',
            'target': 'current',
        }

    @api.depends('doc_type')
    def _compute_doc_type_code(self):
        for obj in self:
            obj.doc_type_code = {'invoices': '380', 'credit-notes': '381'}.get(obj.doc_type, False)
            
    def _parse_xml_invoice_data(self, xml_str):
        cbc = "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}"
        cac = "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}"
        vals = {'xml_data': xml_str,
                'state': 'sent_to_process'}
        myroot = ET.fromstring(xml_str)
        try:
            payment_str = ''
            inv_lines = []
            for x in myroot[1]:
                if x.tag == cbc + 'ID':  # <cbc:ID>
                    vals.update({'invoice_no': x.text})
                if x.tag == cbc + 'IssueDate':  # <cbc:IssueDate>
                    vals.update({'issue_date': x.text})
                if x.tag == cbc + 'DueDate':  # <cbc:DueDate>
                    vals.update({'due_date': x.text})
                if x.tag == cbc + 'TaxPointDate':  # <cbc:TaxPointDate>
                    vals.update({'tax_point_date': x.text})
                if x.tag == cbc + 'InvoiceTypeCode':  # <cbc:InvoiceTypeCode>
                    vals.update({'invoice_type_code': x.text})
                if x.tag == cbc + 'Note':  # <cbc:Note>
                    vals.update({'note': x.text})
                if x.tag == cbc + 'DocumentCurrencyCode':  # <cbc:DocumentCurrencyCode>
                    currency_obj = self.env['res.currency'].sudo().search([('name', '=', x.text.strip())], limit=1)
                    vals.update({'document_currency_code': x.text,
                                 'currency_id': currency_obj and currency_obj.id or False})
                if x.tag == cac + 'InvoicePeriod':
                    for child in x:
                        if child.tag == cbc + 'StartDate':
                            vals.update({'period_start': child.text})
                        if child.tag == cbc + 'EndDate':
                            vals.update({'period_end': child.text})
                if x.tag == cbc + 'BuyerReference':  # <cbc:BuyerReference>
                    vals.update({'buyer_reference': x.text})
                if x.tag == cac + 'OrderReference':  # <cac:OrderReference>
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
                if x.tag == cac + 'AccountingSupplierParty':  # <cac:AccountingSupplierParty>
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
                                        if subchild_1.tag == cbc + 'PostalZone':
                                            vals.update({'sender_address_zip': subchild_1.text})
                                        if subchild_1.tag == cac + 'Country':
                                            for subchild_1_1 in subchild_1:
                                                if subchild_1_1.tag == cbc + 'IdentificationCode':
                                                    vals.update({'sender_address_country': subchild_1_1.text})
                                if subchild.tag == cac + 'PartyLegalEntity':  # <cac:PartyLegalEntity>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'CompanyID':  
                                            vals.update({'uen_no': subchild_1.text}) 


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
                if x.tag == cac + 'PaymentTerms':  # <cac:PaymentTerms>
                    for child in x:
                        if child.tag == cbc + 'Note':
                            vals.update({'payment_terms': child.text})

                # TODO: Payment Means
                if x.tag == cac + 'PaymentMeans':  # <cac:PaymentMeans>
                    if payment_str:
                        payment_str += '\n'
                    for child in x:
                        if child.tag == cbc + 'PaymentMeansCode':
                            attr_dic = child.attrib
                            payment_str += '\nName: ' + attr_dic.get('name', '')
                        if child.tag == cbc + 'PaymentID':
                            payment_str += '\nPayment ID: ' + child.text
                        if child.tag == cac + 'PayeeFinancialAccount':
                            payment_str += '\nPayee Account Details:: '
                            for child_1 in child:
                                if child_1.tag == cbc + 'ID':
                                    payment_str += '\n\t Account No: ' + child_1.text
                                if child_1.tag == cbc + 'Name':
                                    payment_str += '\n\t Account Name: ' + child_1.text
                                if child_1.tag == cac + 'FinancialInstitutionBranch':
                                    payment_str += '\n\t Financial Inst. Branch: '
                                    for child_1_1 in child_1:
                                        if child_1_1.tag == cbc + 'ID':
                                            payment_str += child_1_1.text
                        if child.tag == cac + 'CardAccount':
                            payment_str += '\nCard Account::'
                            for child_1 in child:
                                if child_1.tag == cbc + 'PrimaryAccountNumberID':
                                    payment_str += '\nAccount No: ' + child_1.text
                                if child_1.tag == cbc + 'NetworkID':
                                    payment_str += '\nCard Network: ' + child_1.text
                                if child_1.tag == cbc + 'HolderName':
                                    payment_str += '\nCard Holder Name: ' + child_1.text

                if x.tag == cac + 'TaxTotal':  # <cac:TaxTotal>
                    for child in x:
                        if child.tag == cbc + 'TaxAmount':
                            vals.update({'taxed_amt': child.text})
                            break

                if x.tag == cac + 'LegalMonetaryTotal':  # <cac:LegalMonetaryTotal>
                    for child in x:
                        if child.tag == cbc + 'TaxExclusiveAmount':
                            vals.update({'amt_untaxed': child.text})
                        if child.tag == cbc + 'AllowanceTotalAmount':
                            vals.update({'discount_amt': child.text})
                        if child.tag == cbc + 'TaxInclusiveAmount':
                            vals.update({'amt_including_tax': child.text})

                if x.tag == cac + 'InvoiceLine':  # <cac:InvoiceLine>
                    lines_dic = {}
                    for child in x:
                        if child.tag == cbc + 'InvoicedQuantity':
                            lines_dic.update({'quantity': child.text})
                        if child.tag == cbc + 'LineExtensionAmount':
                            lines_dic.update({'amount_excluding_tax': child.text})
                        if child.tag == cac + 'Price':
                            price_amount, base_qty = 0.0, 1
                            for child_1 in child:
                                if child_1.tag == cbc + 'PriceAmount':
                                    price_amount = float(child_1.text)
                                if child_1.tag == cbc + 'BaseQuantity':
                                    base_qty = float(child_1.text)
                                if child_1.tag == cac + 'AllowanceCharge':
                                    for child_1_1 in child_1:
                                        if child_1_1.tag == cbc + 'Amount':
                                            lines_dic.update({'allowance_charges': child_1_1.text})
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
                        inv_lines.append((0, 0, lines_dic))
            if payment_str:
                payment_str = payment_str[1:]
                vals.update({'payment_means': payment_str})
            inv_lines and vals.update({'invoice_line_ids': inv_lines})
            # Check whether the required PO ref exists in Odoo
            if 'order_reference' in vals:
                purchase_ord_ref = self.env['purchase.order'].sudo().search(
                    [('name', '=', vals.get('order_reference'))])
                if purchase_ord_ref:
                    vals.update({
                        'po_id': purchase_ord_ref.id,
                        'message': "Purchase Order mapped Successfully !!!",
                        'state': 'success',
                    })
                else:
                    vals.update({
                        'message': "Purchase Order '%s' is not found in the database." % (
                            vals.get('order_reference', '')),
                        'state': 'sent_to_process'
                    })
            self.write(vals)
        except Exception as e:
            self.write({
                'state': 'error',
                'message': 'Critical Error.\nFind more details under the Technical tab.',
                'error_exception': repr(e) + "\nTraceback::" + traceback.format_exc(),
            })

    def _parse_xml_creditnotes_data(self, xml_str):
        cbc = "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}"
        cac = "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}"
        vals = {'xml_data': xml_str,
                'state': 'sent_to_process'}
        myroot = ET.fromstring(xml_str)
        try:
            payment_str = ''
            inv_lines = []
            for x in myroot[1]:
                if x.tag == cbc + 'ID':  # <cbc:ID>
                    vals.update({'invoice_no': x.text})
                if x.tag == cbc + 'IssueDate':  # <cbc:IssueDate>
                    vals.update({'issue_date': x.text})
                if x.tag == cbc + 'DueDate':  # <cbc:DueDate>
                    vals.update({'due_date': x.text})
                if x.tag == cbc + 'TaxPointDate':  # <cbc:TaxPointDate>
                    vals.update({'tax_point_date': x.text})
                if x.tag == cbc + 'InvoiceTypeCode':  # <cbc:InvoiceTypeCode>
                    vals.update({'invoice_type_code': x.text})
                if x.tag == cbc + 'Note':  # <cbc:Note>
                    vals.update({'note': x.text})
                if x.tag == cbc + 'DocumentCurrencyCode':  # <cbc:DocumentCurrencyCode>
                    currency_obj = self.env['res.currency'].sudo().search([('name', '=', x.text.strip())], limit=1)
                    vals.update({'document_currency_code': x.text,
                                 'currency_id': currency_obj and currency_obj.id or False})
                if x.tag == cac + 'InvoicePeriod':
                    for child in x:
                        if child.tag == cbc + 'StartDate':
                            vals.update({'period_start': child.text})
                        if child.tag == cbc + 'EndDate':
                            vals.update({'period_end': child.text})
                if x.tag == cbc + 'BuyerReference':  # <cbc:BuyerReference>
                    vals.update({'buyer_reference': x.text})
                if x.tag == cac + 'OrderReference':  # <cac:OrderReference>
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
                if x.tag == cac + 'AccountingSupplierParty':  # <cac:AccountingSupplierParty>
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
                                        if subchild_1.tag == cbc + 'PostalZone':
                                            vals.update({'sender_address_zip': subchild_1.text})
                                        if subchild_1.tag == cac + 'Country':
                                            for subchild_1_1 in subchild_1:
                                                if subchild_1_1.tag == cbc + 'IdentificationCode':
                                                    vals.update({'sender_address_country': subchild_1_1.text})
                                if subchild.tag == cac + 'PartyLegalEntity':  # <cac:PartyLegalEntity>
                                    for subchild_1 in subchild:
                                        if subchild_1.tag == cbc + 'CompanyID':  # <cbc:CompanyID>
                                            vals.update({'uen_no': subchild_1.text})  # Store UEN number

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
                if x.tag == cac + 'PaymentTerms':  # <cac:PaymentTerms>
                    for child in x:
                        if child.tag == cbc + 'Note':
                            vals.update({'payment_terms': child.text})

                # TODO: Payment Means
                if x.tag == cac + 'PaymentMeans':  # <cac:PaymentMeans>
                    if payment_str:
                        payment_str += '\n'
                    for child in x:
                        if child.tag == cbc + 'PaymentMeansCode':
                            attr_dic = child.attrib
                            payment_str += '\nName: ' + attr_dic.get('name', '')
                        if child.tag == cbc + 'PaymentID':
                            payment_str += '\nPayment ID: ' + child.text
                        if child.tag == cac + 'PayeeFinancialAccount':
                            payment_str += '\nPayee Account Details:: '
                            for child_1 in child:
                                if child_1.tag == cbc + 'ID':
                                    payment_str += '\n\t Account No: ' + child_1.text
                                if child_1.tag == cbc + 'Name':
                                    payment_str += '\n\t Account Name: ' + child_1.text
                                if child_1.tag == cac + 'FinancialInstitutionBranch':
                                    payment_str += '\n\t Financial Inst. Branch: '
                                    for child_1_1 in child_1:
                                        if child_1_1.tag == cbc + 'ID':
                                            payment_str += child_1_1.text
                        if child.tag == cac + 'CardAccount':
                            payment_str += '\nCard Account::'
                            for child_1 in child:
                                if child_1.tag == cbc + 'PrimaryAccountNumberID':
                                    payment_str += '\nAccount No: ' + child_1.text
                                if child_1.tag == cbc + 'NetworkID':
                                    payment_str += '\nCard Network: ' + child_1.text
                                if child_1.tag == cbc + 'HolderName':
                                    payment_str += '\nCard Holder Name: ' + child_1.text

                if x.tag == cac + 'TaxTotal':  # <cac:TaxTotal>
                    for child in x:
                        if child.tag == cbc + 'TaxAmount':
                            vals.update({'taxed_amt': child.text})
                            break

                if x.tag == cac + 'LegalMonetaryTotal':  # <cac:LegalMonetaryTotal>
                    for child in x:
                        if child.tag == cbc + 'TaxExclusiveAmount':
                            vals.update({'amt_untaxed': child.text})
                        if child.tag == cbc + 'AllowanceTotalAmount':
                            vals.update({'discount_amt': child.text})
                        if child.tag == cbc + 'TaxInclusiveAmount':
                            vals.update({'amt_including_tax': child.text})

                if x.tag == cac + 'CreditNoteLine':  # <cac:CreditNoteLine>
                    lines_dic = {}
                    for child in x:
                        if child.tag == cbc + 'CreditedQuantity':
                            lines_dic.update({'quantity': child.text})
                        if child.tag == cbc + 'LineExtensionAmount':
                            lines_dic.update({'amount_excluding_tax': child.text})
                        if child.tag == cac + 'Price':
                            price_amount, base_qty = 0.0, 1
                            for child_1 in child:
                                if child_1.tag == cbc + 'PriceAmount':
                                    price_amount = float(child_1.text)
                                if child_1.tag == cbc + 'BaseQuantity':
                                    base_qty = int(child_1.text)
                                if child_1.tag == cac + 'AllowanceCharge':
                                    for child_1_1 in child_1:
                                        if child_1_1.tag == cbc + 'Amount':
                                            lines_dic.update({'allowance_charges': child_1_1.text})
                            if price_amount > 0.0:
                                lines_dic.update({'price_amount': price_amount / base_qty})

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
                        inv_lines.append((0, 0, lines_dic))
            if payment_str:
                payment_str = payment_str[1:]
                vals.update({'payment_means': payment_str})
            inv_lines and vals.update({'invoice_line_ids': inv_lines})
            # Check whether the required PO ref exists in Odoo
            if 'order_reference' in vals:
                purchase_ord_ref = self.env['purchase.order'].sudo().search(
                    [('name', '=', vals.get('order_reference'))])
                if purchase_ord_ref:
                    vals.update({
                        'po_id': purchase_ord_ref.id,
                        'message': "Purchase Order mapped Successfully !!!",
                        'state': 'success',
                    })
                else:
                    vals.update({
                        'message': "Purchase Order '%s' is not found in the database." % (
                            vals.get('order_reference', '')),
                        'state': 'sent_to_process'
                    })
            self.write(vals)
        except Exception as e:
            self.write({
                'state': 'error',
                'message': 'Critical Error.\nFind more details under the Technical tab.',
                'error_exception': repr(e) + "\nTraceback::" + traceback.format_exc(),
            })

    def _create_incoming_invoice_record(self, resp_dic, api_dic, company_id, access_point_id):
        if self.search([('invoice_no', '=', resp_dic.get('documentNo', '').strip()), ('company_id','=',company_id)]):
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
            'iras_status': resp_dic.get('irasStatus'),
            'iras_statusinfo': resp_dic.get('irasStatusInfo'),
            'invoice_no': resp_dic.get('documentNo').strip(),
            'received': True,
            'company_id': company_obj and company_obj.id or False,
            'access_point_id': access_point_id,            
            'doc_type': 'invoices'
        })

        try:
            # response = requests.get('%s/business/%s/invoices/%s.xml' % (api_dic['base_url'],
            #                                                             api_dic['api_version'],
            #                                                             urllib.parse.quote(resp_dic.get('documentNo'), safe="")
            #                                                             ),
            #                         headers=api_dic['headers'],
            #                         timeout=int(api_dic['timeout']))
            response = requests.get('%s/api/business/%s/invoices/%s' % (api_dic['base_url'],
                                                                        api_dic['api_version'],
                                                                        urllib.parse.quote(resp_dic.get('clientRef'),
                                                                                           safe="")
                                                                        ),
                                    headers=api_dic['headers'],
                                    timeout=int(api_dic['timeout']))
            status_code = response.status_code
            try:
                response_data = json.loads(response.text)
            except:
                response_data = response.text
            if status_code == 200:
                obj._parse_xml_invoice_data(response_data)
                print('\nobj.sender_party_name', obj.sender_party_name)
                if obj.sender_party_name:
                    res_partner_id = self.env['res.partner'].search(
                        [('name', '=', obj.sender_party_name), ('vat', '!=', False)], limit=1)
                    if res_partner_id:
                        res_partner_id.check_gst_register(res_partner_id)
                        print('\nres_partner_id', res_partner_id)
                        if obj.doc_type == 'invoices' and res_partner_id.registration_status == 'unregistered' and obj.taxed_amt > 0:
                            obj.write({'gst_no': res_partner_id.vat})
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

    def _create_incoming_credit_record(self, resp_dic, api_dic, company_id, access_point_id):
        print("\n_create_incoming_credit_record ====")
        if self.search([('invoice_no', '=', resp_dic.get('documentNo', '').strip()), ('company_id', '=', company_id)]):
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
            'iras_status': resp_dic.get('irasStatus'),
            'iras_statusinfo': resp_dic.get('irasStatusInfo'),
            'invoice_no': resp_dic.get('documentNo').strip(),
            'received': True,
            'company_id': company_obj and company_obj.id or False,
            'access_point_id': access_point_id,            
            'doc_type': 'credit-notes'
        })

        try:
            # response = requests.get('%s/business/%s/credit-notes/%s.xml' % (api_dic['base_url'],
            #                                                             api_dic['api_version'],
            #                                                             urllib.parse.quote(resp_dic.get('documentNo'), safe="")),
            #                         headers=api_dic['headers'],
            #                         timeout=int(api_dic['timeout']))
            response = requests.get('%s/api/business/%s/credit-notes/%s' % (api_dic['base_url'],
                                                                            api_dic['api_version'],
                                                                            urllib.parse.quote(resp_dic.get('clientRef'), safe="")),
                                    headers=api_dic['headers'],
                                    timeout=int(api_dic['timeout']))
            status_code = response.status_code
            try:
                response_data = json.loads(response.text)
            except:
                response_data = response.text
            if status_code == 200:
                obj._parse_xml_creditnotes_data(response_data)
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

    def query_receive_documents(self):
        for access_point in self.env['peppol.access.point.sg'].sudo().search([('company_id', '=', self.env.company.id)]):
            print('\n>access_point>', access_point)
            _logger.info("\naccess_point............")
            _logger.info(access_point)
            base_url = access_point.endpoint
            api_version = access_point.api_version
            receiver_id = access_point.company_id.peppol_scheme + ':' + access_point.company_id.peppol_identifier
            timeout = self.env['ir.config_parameter'].sudo().get_param('api_timeout', default='20')
            headers = {
                # "Accept": "*/*",
                "Authorization": f"Bearer {access_point.access_token}",
                # TODO: Don't calculate but instead calculate and store as one time.
            }
            try:
                status_code, response_data = 'None', ''
                print('\nreiruri', '%s/api/business/%s/invoices?receiver=%s' % (base_url, api_version, receiver_id))
                response = requests.get(
                    '%s/api/business/%s/invoices?receiver=%s' % (base_url, api_version, receiver_id),
                    headers=headers,
                    timeout=int(timeout))
                _logger.info('%s/api/business/%s/invoices?receiver=%s' % (base_url, api_version, receiver_id))
                status_code = response.status_code
                try:
                    response_data = json.loads(response.text)
                except:
                    response_data = response.text
                print("invoices = response_data ===",response_data)
                _logger.info("\nresponse_data..................")
                _logger.info(response_data)
                _logger.info(status_code)

                if status_code == 200 and isinstance(response_data, dict):
                    total_records = response_data['total']
                    for resp_dic in response_data['info']:
                        _logger.info("Creatingggggggggggggggggggggggggggggggggggggggggg")
                        self._create_incoming_invoice_record(resp_dic, {'base_url': base_url, 'api_version': api_version,
                                                                'headers': headers, 'timeout': timeout},
                                                     company_id=access_point.company_id.id,
                                                     access_point_id=access_point.id)
                else:
                    vals = {
                        'status_code': status_code,
                        'response_body': response_data,
                        'doc_type': 'invoices'
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
                    'doc_type': 'invoices'
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
                    'doc_type': 'invoices'
                }
                self.env['incoming.failed.logs'].create(vals)

            try:
                print("credit-notes ====")
                status_code, response_data = 'None', ''
                # response = requests.get(
                #     '%s/business/%s/credit-notes.json?type=2' % (base_url, api_version),
                #     headers=headers,
                #     timeout=int(timeout))

                response = requests.get(
                    '%s/api/business/%s/credit-notes?receiver=%s' % (base_url, api_version, receiver_id),
                    headers=headers,
                    timeout=int(timeout))
                _logger.error('%s/api/business/%s/credit-notes?receiver=%s' % (base_url, api_version, receiver_id))
                status_code = response.status_code
                try:
                    response_data = json.loads(response.text)
                except:
                    response_data = response.text
                print("credit-notes = response_data ===",response_data)
                if status_code == 200 and isinstance(response_data, dict):
                    total_records = response_data['total']
                    for resp_dic in response_data['info']:
                        self._create_incoming_credit_record(resp_dic, {'base_url': base_url, 'api_version': api_version,
                                                                'headers': headers, 'timeout': timeout},
                                                     company_id=access_point.company_id.id,
                                                     access_point_id=access_point.id)
                else:
                    vals = {
                        'status_code': status_code,
                        'response_body': response_data,
                        'doc_type': 'credit-notes'
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
                    'doc_type': 'credit-notes'
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
                    'doc_type': 'credit-notes'
                }
                self.env['incoming.failed.logs'].create(vals)

    def action_retry(self):
        for obj in self:
            access_point = obj.access_point_id
            base_url = access_point.endpoint
            api_version = access_point.api_version
            timeout = self.env['ir.config_parameter'].sudo().get_param('api_timeout', default='20')
            headers = {
                # "Accept": "*/*",
                "Authorization": f"Bearer {access_point.access_token}",
                # TODO: Don't calculate but instead calculate and store as one time.
            }
            if obj.doc_type == 'invoices':
                try:
                    # response = requests.get('%s/business/%s/invoices/%s.xml' % (base_url, api_version, urllib.parse.quote(obj.extracted_docno, safe="")),
                    #                         headers=headers,
                    #                         timeout=int(timeout))
                    response = requests.get('%s/api/business/%s/invoices/%s' % (base_url, api_version, urllib.parse.quote(obj.client_ref, safe="")),
                                            headers=headers,
                                            timeout=int(timeout))
                    status_code = response.status_code
                    try:
                        response_data = json.loads(response.text)
                    except:
                        response_data = response.text
                    if status_code == 200:
                        self._parse_xml_invoice_data(response_data)
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
            else:
                try:
                    response = requests.get('%s/api/business/%s/credit-notes/%s' % (base_url, api_version, urllib.parse.quote(obj.client_ref, safe="")),
                                            headers=headers,
                                            timeout=int(timeout))
                    status_code = response.status_code
                    try:
                        response_data = json.loads(response.text)
                    except:
                        response_data = response.text
                    if status_code == 200:
                        self._parse_xml_creditnotes_data(response_data)
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
                raise ValidationError(_("You cannot delete the records other than 'Received' or 'Cancelled' states."))
        return super(PeppolQueueIn, self).unlink()

    def action_cancel(self):
        """ This method will set the state as cancelled. """
        self.write({'state': 'cancelled'})

    @api.model
    def create1(self, vals):
        """It sends either Email or Notification to the particular users at the time of creating Incoming Invoice."""
        obj = super(PeppolQueueIn, self).create(vals)
        if obj.state in ['received', 'error']:
            groups = self.env['ir.config_parameter'].sudo().get_param('incoming_doc_email_grp_name_ids', default=False)
            domain = [('groups_id', 'in', eval(groups))]
            if obj.company_id:
                domain += [('company_ids', 'in', [obj.company_id.id])]
            for user in self.env['res.users'].sudo().search(domain):
                if user.notification_type == 'email':
                    template_obj = self.env.ref('metro_einvoice_datapost.incoming_invoice_document_notification')
                    action_id = self.env.ref('metro_einvoice_datapost.action_pepppol_log_sg_view').id
                    template_obj.with_context(
                        {'email_to': user.email, 'document_id': obj.id, 'action_id': action_id}).send_mail(obj.id,
                                                                                                           force_send=False)
                elif user.notification_type == 'inbox':
                    body = _('Hi<br/>New %s <b>%s</b> received with status ') % (obj.doc_type == 'invoices' and 'Invoice' or 'Credit Note', obj.invoice_no)
                    if obj.state == 'success':
                        body += _('<b>Mapped.</b>')
                    elif obj.state == 'sent_to_process':
                        body += _('<b>Unmapped.</b>')
                    elif obj.state == 'error':
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
            'views': [(self.env.ref('metro_einvoice_datapost.purchase_order_peppol_mapping_list').id, 'tree'),
                      (self.env.ref('purchase.purchase_order_form').id, 'form')],
            'search_view_id': self.env.ref('purchase.view_purchase_order_filter').id,
            'res_model': 'purchase.order',
            'context': {'invoice_map_id': self.id},
            'type': 'ir.actions.act_window',
        }

    def action_suggestion(self):
        """ Perform nothing. """
        return False

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

    def action_invoice_response_out(self):
        return {            
            'name': _('Invoice Response'),
            'res_model': 'invoice.response.prefill.status',
            'view_mode': 'form',
            'context': {
                'active_model': 'peppol.queue.in',
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    # List all the Matches Invoice Bills and also By domain move_type.
    def action_view_invoice_bill(self):
        extracted_senderid = self.extracted_senderid
        partner_ids = self.env['res.partner'].search([('peppol_identifier', 'ilike', extracted_senderid)])        
        cleaned_partner_ids = self.env['res.partner'].search(['|',('peppol_identifier', '=', extracted_senderid.split(":")[1]),
                ('peppol_identifier', 'ilike', extracted_senderid.split(":")[1])]) # Remove the "0195:" prefix from partner's peppol_identifier
        move_ids = self.env['account.move'].search([('partner_id', 'in', cleaned_partner_ids.ids)])
        return {
            'name': _('Bills'),
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('metro_einvoice_datapost.view_pepppol_in_invoice_tree_view').id, 'tree'),
                (self.env.ref('account.view_move_form').id, 'form'),
            ],
            'search_view_id': self.env.ref('account.view_account_invoice_filter').id,
            'res_model': 'account.move',
            'domain': [('move_type', '=', 'in_invoice'), ('id', 'in', move_ids.ids)],
            'type': 'ir.actions.act_window',
            'context': {'default_move_type': 'in_invoice'}
        }
    
    # def action_convert_to_purchase_invoice(self):
    #     """Opens the bill form pre-filled with default values from peppol.queue.in"""
    #     return {
    #         'name': 'Create Vendor Bill',
    #         'view_mode': 'form',
    #         'view_id': self.env.ref('account.view_move_form').id,
    #         'res_model': 'account.move',
    #         'type': 'ir.actions.act_window',
    #         'context': {
    #             'active_id': self.id,
    #             'default_move_type': 'in_invoice',
    #
    #         },
    #         'target': 'current',  # Open in the same window
    #     }

    def action_convert_to_purchase_invoice(self):
        # queue_obj = self.env['peppol.queue.in'].browse(self._context['active_id'])
        if self.doc_type == 'invoices':
            vals = {'move_type': 'in_invoice'}
        else:
            vals = {'move_type': 'in_refund'}
        partner = self.env['res.partner'].search(
            ['|', ('peppol_identifier', '=', self.extracted_senderid.split(":")[1]),
             ('peppol_identifier', 'ilike', self.extracted_senderid.split(":")[1])], limit=1)
        if partner:
            vals['partner_id'] = partner.id
        else:
            country_obj, child_dic = False, {}
            if self.sender_address_country:
                country_obj = self.env['res.country'].search(['|', ('name', '=', self.sender_address_country),
                                                              ('code', '=', self.sender_address_country)], limit=1)
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
            vals['partner_id'] = partner.id

        if self.due_date:
            vals['invoice_date_due'] = self.due_date
        elif self.payment_terms:
            numbers = re.findall(r'\d+\.\d+|\d+', self.payment_terms)
            print("numbers ==", numbers)
            if numbers:
                pobjs = self.env['account.payment.term'].search([('name', 'ilike', numbers[0])], limit=1)
                print("pobjs ==", pobjs)
                if pobjs:
                    vals['invoice_payment_term_id'] = pobjs.id
        if self.issue_date:
            vals['invoice_date'] = self.issue_date
        if self.note:
            vals['narration'] = self.note

        invoice_lines = []
        for line in self.invoice_line_ids:
            default_codes, barcodes = [], []
            if line.buyers_item_identification:
                product = self.env['product.product'].search(
                    ['|', ('default_code', '=', line.buyers_item_identification),
                     ('barcode', '=', line.buyers_item_identification)], limit=1)
            elif line.sellers_item_identification:
                product = self.env['product.product'].search(
                    ['|', ('default_code', '=', line.sellers_item_identification),
                     ('barcode', '=', line.sellers_item_identification)], limit=1)
            elif line.standard_item_identification:
                product = self.env['product.product'].search(
                    ['|', ('default_code', '=', line.standard_item_identification),
                     ('barcode', '=', line.standard_item_identification)], limit=1)
            elif line.item_classification_identifier:
                product = self.env['product.product'].search(
                    ['|', ('default_code', '=', line.item_classification_identifier),
                     ('barcode', '=', line.item_classification_identifier)], limit=1)
            else:
                product = self.env['product.product'].search(
                    ['|', ('name', '=', line.name), ('name', 'ilike', line.name)], limit=1)

            res = self.env['account.move.line'].default_get(['partner_id', 'account_id'])
            print("line_res ==", res)
            tax = self.env['account.tax'].search([
                ('type_tax_use', '=', 'purchase'),
                ('amount', '=', line.tax_percentage),
                ('unece_categ_id', '!=', False),
            ], limit=1)
            invoice_line_values = {
                'product_id': product.id if product else False,
                'name': line.name,
                'quantity': line.quantity,
                'price_unit': line.price_amount,
                'product_uom_id': product.uom_id.id if product and product.uom_id else False,
                'display_type': False,
                'tax_ids': [(6, 0, tax.ids)] if tax else False,
                # 'account_id': 112,
                'sequence': 1
            }
            discount = (line.quantity * line.price_amount) - line.amount_excluding_tax
            if discount > 0.0:
                discount_percentage = (discount / (line.quantity * line.price_amount)) * 100
                invoice_line_values.update({'discount': discount_percentage})
            invoice_lines.append((0, 0, invoice_line_values))

        vals['invoice_line_ids'] = invoice_lines
        bill = self.env['account.move'].create(vals)
        if self.doc_type == 'invoices':
            return {
                'name': 'Vendor Bill',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': bill.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'name': 'Refunds',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': bill.id,
                'view_mode': 'form',
                'target': 'current',
            }


class IncomingInvoiceLines(models.Model):
    _name = "incoming.invoice.lines"
    _description = "Incoming Invoice Lines"

    parent_id = fields.Many2one('peppol.queue.in', 'Parent')
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
    note = fields.Text('Note')
    buyers_item_identification = fields.Char('Buyers Item Identifier')
    sellers_item_identification = fields.Char('Sellers Item Identifier')
    standard_item_identification = fields.Char('Standard Item Identifier')
    item_classification_identifier = fields.Char('Item Classification Identifier')
