# -*- coding: utf-8 -*-
import base64
import traceback
from lxml import etree
import logging
import requests
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError,UserError
from odoo.tools import float_is_zero, float_round
from datetime import date, datetime, time
import json
import re
import xml.etree.ElementTree as ET
import uuid

logger = logging.getLogger(__name__)

SELECTION_PEPPOL_QUEUE_OUT_STATE = [
    ('ready_to_send', 'Ready to Send'),
    ('Pending', 'Pending'),
    ('Processing', 'Processing'),
    ('Send Success', 'Send Success'),
    ('Send Error', 'Send Error'),
    ('Receive Success', 'Receive Success'),
    ('Completed', 'Completed'),
    ('error', 'Failed'),
    ('cancelled', 'Cancelled'),
]

TIMEOUT = 20


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "base.ubl"]

    # @api.model
    # def default_get(self, fields):
    #     print("\nCUSTOM >> default_get() AccountMove >>>>>>")
    #     res = super(AccountMove, self).default_get(fields)
    #     print("res ==",res)
    #     ctx = self._context or {}
    #     print(ctx)
    #     if ctx.get('active_model') == 'peppol.queue.in' and ctx.get('active_id'):
    #         queue_obj = self.env['peppol.queue.in'].browse(self._context['active_id'])
    #
    #         partner = self.env['res.partner'].search(['|',('peppol_identifier', '=', queue_obj.extracted_senderid.split(":")[1]),
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
    #         if queue_obj.due_date:
    #             res['invoice_date_due'] = queue_obj.due_date
    #         elif queue_obj.payment_terms:
    #             numbers = re.findall(r'\d+\.\d+|\d+', queue_obj.payment_terms)
    #             print("numbers ==",numbers)
    #             if numbers:
    #                 pobjs = self.env['account.payment.term'].search([('name', 'ilike', numbers[0])], limit=1)
    #                 print("pobjs ==",pobjs)
    #                 if pobjs:
    #                     res['invoice_payment_term_id'] = pobjs.id
    #         if queue_obj.issue_date:
    #             res['invoice_date'] = queue_obj.issue_date
    #         if queue_obj.note:
    #             res['narration'] = queue_obj.note
    #
    #         invoice_lines = []
    #         for line in queue_obj.invoice_line_ids:
    #             default_codes, barcodes = [], []
    #             if line.buyers_item_identification:
    #                 product = self.env['product.product'].search(['|',('default_code', '=', line.buyers_item_identification), ('barcode', '=', line.buyers_item_identification)], limit=1)
    #             elif line.sellers_item_identification:
    #                 product = self.env['product.product'].search(['|',('default_code', '=', line.sellers_item_identification), ('barcode', '=', line.sellers_item_identification)], limit=1)
    #             elif line.standard_item_identification:
    #                 product = self.env['product.product'].search(['|',('default_code', '=', line.standard_item_identification), ('barcode', '=', line.standard_item_identification)], limit=1)
    #             elif line.item_classification_identifier:
    #                 product = self.env['product.product'].search(['|',('default_code', '=', line.item_classification_identifier), ('barcode', '=', line.item_classification_identifier)], limit=1)
    #             else:
    #                 product = self.env['product.product'].search(['|',('name', '=', line.name), ('name', 'ilike', line.name)], limit=1)
    #
    #             res = self.env['account.move.line'].default_get(['partner_id', 'account_id'])
    #             print("line_res ==",res)
    #             invoice_line_values = {
    #                 'product_id': product.id if product else False,
    #                 'name': line.name,
    #                 'quantity': line.quantity,
    #                 'price_unit': line.price_amount,
    #                 'product_uom_id': product.uom_id.id if product and product.uom_id else False,
    #                 'display_type': False,
    #                 'account_id': 112,
    #                 'sequence': 1
    #             }
    #             discount = (line.quantity * line.price_amount) - line.amount_excluding_tax
    #             if discount > 0.0:
    #                 discount_percentage = (discount / (line.quantity * line.price_amount)) * 100
    #                 invoice_line_values.update({'discount': discount_percentage})
    #             invoice_lines.append((0, 0, invoice_line_values))
    #
    #         res['invoice_line_ids'] = invoice_lines
    #         print("FINAL res ===",res)
    #     return res

    peppol_invoice_no = fields.Char(string="Peppol Invoice No", copy=False)
    peppol_invoice_doc_ids = fields.Many2many(
        'ir.attachment', 'account_move_peppol_docs_rel', 'move_id', 'attachment_id',
        string='Received Documents', copy=False)
    outgoing_inv_doc_ref = fields.Many2one('peppol.queue.out', string="Document Ref", copy=False)
    outgoing_inv_doc_ref_c5 = fields.Many2one('peppol.queue.c5.out', string="Document Ref(C5)", copy=False)
    b2c_outgoing_inv_doc_ref = fields.Many2one('b2c.outgoing.invoices', string="Document Ref(POS/STI)", copy=False)
    pcp_outgoing_inv_doc_ref = fields.Many2one('pcp.outgoing.invoices', string="Document Ref(PCP)", copy=False)

    bulk_c5_invoice = fields.Boolean(string="Is Bulk C5 Invoice", default=False)
    peppol_document_type = fields.Selection([('peppol','Peppol'),('nonpeppol','Non-Peppol')], compute="_compute_peppol_document_type",string="Document Type", tracking=1)
    peppol_state = fields.Selection(SELECTION_PEPPOL_QUEUE_OUT_STATE, string="Status", default='ready_to_send', index=True, compute='_compute_peppol_state')
    sale_order_id = fields.Many2one('sale.order', string="Order ID")
    note = fields.Text(string="Note", readonly=True)
    vendor_id = fields.Many2one('res.partner', string="Vendor")
    document_type = fields.Selection([
        ('initial', 'Initial'),
        ('balance', 'Balance'),
        ('variation', 'Variation'),
        ('cancel', 'Cancel')], string="Document Type", default='initial')
    supplier_email_address = fields.Char('Supplier Email')
    business_unit_id = fields.Many2one('ministries.statuary.boards', string="Business Unit")
    customer_contact_person = fields.Char(string="Customer Contact Person")
    order_ref = fields.Char(string="Order Ref")
    vendor_identification = fields.Char(
        string="Vendor ID",
        compute="_compute_vendor_identification",
        store=True
    )

    @api.depends('vendor_id')
    def _compute_vendor_identification(self):
        for record in self:
            record.vendor_identification = record.vendor_id.l10n_sg_unique_entity_number if record.vendor_id and record.vendor_id.l10n_sg_unique_entity_number else False


    @api.model
    def create(self, vals):
        print("create == vals",vals)
        ctx = self._context
        print(ctx)
        obj =  super(AccountMove, self).create(vals)
        return obj

    @api.depends('partner_id')
    def _compute_peppol_document_type(self):
        for invoice in self:
            invoice.peppol_document_type = 'nonpeppol'
            if invoice.partner_id and invoice.partner_id.peppol_identifier:
                if invoice.partner_id.is_peppol_participant:
                    invoice.peppol_document_type = 'peppol'
                else:
                    invoice.peppol_document_type = 'nonpeppol'
            else:
                invoice.peppol_document_type = False

    @api.depends('outgoing_inv_doc_ref', 'outgoing_inv_doc_ref_c5', 'b2c_outgoing_inv_doc_ref')
    def _compute_peppol_state(self):
        for invoice in self:
            if invoice.outgoing_inv_doc_ref:
                invoice.peppol_state = invoice.outgoing_inv_doc_ref.state
            elif invoice.outgoing_inv_doc_ref_c5:
                invoice.peppol_state = invoice.outgoing_inv_doc_ref_c5.state
            elif invoice.b2c_outgoing_inv_doc_ref:
                invoice.peppol_state = invoice.b2c_outgoing_inv_doc_ref.state
            else:
                invoice.peppol_state = False

    def _pint_add_header(self, parent_node, ns, version="2.1"):
        self.ensure_one()
        ubl_version = etree.SubElement(parent_node, ns["cbc"] + "UBLVersionID")
        ubl_version.text = version
        ubl_customization_id = etree.SubElement(parent_node, ns["cbc"] + "CustomizationID")
        ubl_customization_id.text = "urn:peppol:pint:billing-1@sg-1"
        ubl_profile_id = etree.SubElement(parent_node, ns["cbc"] + "ProfileID")
        ubl_profile_id.text = "urn:peppol:bis:billing"
        ubl_version.text = version
        doc_id = etree.SubElement(parent_node, ns["cbc"] + "ID")
        doc_id.text = self.name
        random_uuid = uuid.uuid4()
        uuid_var = etree.SubElement(parent_node, ns["cbc"] + "UUID")
        uuid_var.text = str(random_uuid)
        issue_date = etree.SubElement(parent_node, ns["cbc"] + "IssueDate")
        issue_date.text = self.invoice_date.strftime("%Y-%m-%d")
        if self.move_type == "out_invoice":
            due_date = etree.SubElement(parent_node, ns["cbc"] + "DueDate")
            due_date.text = self.invoice_date_due.strftime("%Y-%m-%d")
        if self.move_type == "out_invoice":
            type_code = etree.SubElement(parent_node, ns["cbc"] + "InvoiceTypeCode")
        else:
            type_code = etree.SubElement(parent_node, ns["cbc"] + "CreditNoteTypeCode")
        if self.move_type == "out_invoice":
            type_code.text = "380"
        elif self.move_type == "out_refund":
            type_code.text = "381"

        if self.move_type == "out_refund":
            if not self.narration:
                raise ValidationError("Please provide the reason/note for this Credit Note.")
        if self.narration:
            note = etree.SubElement(parent_node, ns["cbc"] + "Note")
            note.text = self.narration

        # else:
        #     if not self.ref:
        #         raise ValidationError("Please provide the reason/note for this Credit Note. Hint: Provide it under the Customer Reference field.")
        #     note = etree.SubElement(parent_node, ns["cbc"] + "Note")
        #     note.text = self.ref
        doc_currency = etree.SubElement(parent_node, ns["cbc"] + "DocumentCurrencyCode")
        doc_currency.text = self.currency_id.name

        if self.currency_id.id != self.company_id.currency_id.id:
            logger.error("\n\nForegin currency......")
            tax_curr_code = etree.SubElement(parent_node, ns["cbc"] + "TaxCurrencyCode")
            tax_curr_code.text = self.company_id.currency_id.name

        if self.move_type == "out_invoice":
            if self.ref:
                buyer_reference = etree.SubElement(parent_node, ns["cbc"] + "BuyerReference")
                buyer_reference.text = self.ref
        if self.invoice_user_id:
            buyer_reference = etree.SubElement(parent_node, ns["cbc"] + "BuyerReference") #TODO::
            buyer_reference.text = self.invoice_user_id.name

    def _ubl_add_additional_documents(self, parent_node, ns, version="2.1"):
        # Excluding
        doc_ref = etree.SubElement(parent_node, ns["cac"] + "AdditionalDocumentReference")
        doc_ref_id = etree.SubElement(doc_ref, ns["cbc"] + "ID")
        doc_ref_id.text = self.company_id.currency_id.name

        doc_ref_code = etree.SubElement(doc_ref, ns["cbc"] + "DocumentTypeCode")
        doc_ref_code.text = 'sgdtotal-excl-gst'

        total_without_gst = self.currency_id._convert(
            self.amount_untaxed, self.company_id.currency_id, self.company_id, self.invoice_date or fields.Date.today()
        )
        logger.error("total_without_gst ===")
        logger.error(total_without_gst)

        doc_ref_desc = etree.SubElement(doc_ref, ns["cbc"] + "DocumentDescription")
        doc_ref_desc.text = str(total_without_gst)

        # Included
        doc_ref = etree.SubElement(parent_node, ns["cac"] + "AdditionalDocumentReference")
        doc_ref_id = etree.SubElement(doc_ref, ns["cbc"] + "ID")
        doc_ref_id.text = self.company_id.currency_id.name

        doc_ref_code = etree.SubElement(doc_ref, ns["cbc"] + "DocumentTypeCode")
        doc_ref_code.text = 'sgdtotal-incl-gst'

        total_with_gst = self.currency_id._convert(
            self.amount_total, self.company_id.currency_id, self.company_id, self.invoice_date or fields.Date.today()
        )
        logger.error("total_with_gst ===")
        logger.error(total_with_gst)

        doc_ref_desc = etree.SubElement(doc_ref, ns["cbc"] + "DocumentDescription")
        doc_ref_desc.text = str(total_with_gst)

    def _ubl_add_tax_total_foreign_currency(self, parent_node, ns, version="2.1"):
        tax_total = etree.SubElement(parent_node, ns["cac"] + "TaxTotal")
        tax_amount = etree.SubElement(tax_total, ns["cbc"] + "TaxAmount", currencyID=self.company_id.currency_id.name)
        prec = self.currency_id.decimal_places
        total_tax_foreign = self.currency_id._convert(
            self.amount_tax, self.company_id.currency_id, self.company_id, self.invoice_date or fields.Date.today()
        )
        logger.error("total_tax_foreign ===")
        logger.error(total_tax_foreign)
        tax_amount.text = "%0.*f" % (prec, total_tax_foreign)

    def generate_pint_xml(self, version="2.1"):
        self.ensure_one()
        assert self.state == "posted"
        assert self.move_type in ("out_invoice", "out_refund")
        lang = self.get_ubl_lang()


        company_partner = self.company_id.partner_id

        if self.partner_id.l10n_sg_unique_entity_number:
            partner_obj = self.partner_id
        else:
            partner_obj = self.partner_id.parent_id

        if self.currency_id.id != self.company_id.currency_id.id:
            is_foreign_curr = True
        else:
            is_foreign_curr = False

        if self.move_type == 'out_invoice':
            nsmap, ns = self._ubl_get_nsmap_namespace("Invoice-2", version=version)
            xml_root = etree.Element("Invoice", nsmap=nsmap)
            self._pint_add_header(xml_root, ns, version=version)
            self._ubl_add_order_reference(xml_root, ns, version=version)
            self._ubl_add_attachments(xml_root, ns, version=version)
            if is_foreign_curr:
                self._ubl_add_additional_documents(xml_root, ns, version=version)

            # Accounting Supplier Party
            supplier = etree.SubElement(xml_root, ns["cac"] + "AccountingSupplierParty")
            supplier_party = etree.SubElement(supplier, ns["cac"] + "Party")
            if not company_partner.peppol_identifier:
                raise ValidationError("The Peppol Identifer cannot be empty for the Partner: " + str(company_partner.name))
            if not company_partner.peppol_scheme:
                raise ValidationError("The Peppol Scheme cannot be empty for the Partner: " + str(company_partner.name))
            supplier_party_endpoint = etree.SubElement(supplier_party, ns["cbc"] + "EndpointID", schemeID=company_partner.peppol_scheme)
            supplier_party_endpoint.text = company_partner.peppol_identifier

            party_ident = etree.SubElement(supplier_party, ns["cac"] + "PartyIdentification")
            etree.SubElement(party_ident, ns["cbc"] + "ID", schemeID="0195").text = company_partner.l10n_sg_unique_entity_number
            party_name = etree.SubElement(supplier_party, ns["cac"] + "PartyName")
            etree.SubElement(party_name, ns["cbc"] + "Name").text = company_partner.name
            address = etree.SubElement(supplier_party, ns["cac"] + "PostalAddress")
            if not company_partner.street:
                raise ValidationError('Address information (i.e, Street field) of the Partner: ' + str(company_partner.name) + ' cannot be empty.')
            else:
                etree.SubElement(address, ns["cbc"] + "StreetName").text = company_partner.street
            if company_partner.street2:
                etree.SubElement(address, ns["cbc"] + "AdditionalStreetName").text = company_partner.street2
            if company_partner.city:
                etree.SubElement(address, ns["cbc"] + "CityName").text = company_partner.city
            if not company_partner.zip:
                raise ValidationError('Address information (i.e, Zip field) of the Partner: ' + str(company_partner.name) + ' cannot be empty.')
            else:
                etree.SubElement(address, ns["cbc"] + "PostalZone").text = company_partner.zip
            if not company_partner.country_id:
                raise ValidationError('Address information (i.e, Country field) of the Partner: ' + str(company_partner.name) + ' cannot be empty.')
            else:
                country = etree.SubElement(address, ns["cac"] + "Country")
                etree.SubElement(country, ns["cbc"] + "IdentificationCode").text = company_partner.country_id.code

            party_tax_scheme = etree.SubElement(supplier_party, ns["cac"] + "PartyTaxScheme")
            if not company_partner.vat:
                raise ValidationError('GST Reg No. is not provided to the Partner: ' + str(company_partner.name))
            etree.SubElement(party_tax_scheme, ns["cbc"] + "CompanyID").text = company_partner.vat
            party_tax_scheme_1 = etree.SubElement(party_tax_scheme, ns["cac"] + "TaxScheme")
            etree.SubElement(party_tax_scheme_1, ns["cbc"] + "ID").text = 'GST'

            party_legal_entity = etree.SubElement(supplier_party, ns["cac"] + "PartyLegalEntity")
            etree.SubElement(party_legal_entity, ns["cbc"] + "RegistrationName").text = company_partner.name
            if not company_partner.l10n_sg_unique_entity_number:
                raise ValidationError('UEN no is not defined to the Partner: ' + str(company_partner.name))
            etree.SubElement(party_legal_entity, ns["cbc"] + "CompanyID").text = company_partner.l10n_sg_unique_entity_number

            # Accounting Customer Party
            customer = etree.SubElement(xml_root, ns["cac"] + "AccountingCustomerParty")
            customer_party = etree.SubElement(customer, ns["cac"] + "Party")
            if not partner_obj.peppol_identifier:
                raise ValidationError("The Peppol Identifer cannot be empty for the Partner: " + str(partner_obj.name))
            if not partner_obj.peppol_scheme:
                raise ValidationError("The Peppol Scheme cannot be empty for the Partner: " + str(partner_obj.name))
            if not partner_obj.l10n_sg_unique_entity_number:
                raise ValidationError('UEN no is not defined to the Partner: ' + str(partner_obj.name))
            if not partner_obj.is_peppol_participant:
                peppol_identifier = 'C5UID' + str(partner_obj.l10n_sg_unique_entity_number)
            else:
                peppol_identifier = partner_obj.peppol_identifier
            customer_party_endpoint = etree.SubElement(customer_party, ns["cbc"] + "EndpointID", schemeID=partner_obj.peppol_scheme)
            customer_party_endpoint.text = peppol_identifier

            party_ident = etree.SubElement(customer_party, ns["cac"] + "PartyIdentification")
            etree.SubElement(party_ident, ns["cbc"] + "ID", schemeID="0195").text = partner_obj.l10n_sg_unique_entity_number

            party_name = etree.SubElement(customer_party, ns["cac"] + "PartyName")
            etree.SubElement(party_name, ns["cbc"] + "Name").text = partner_obj.name
            address = etree.SubElement(customer_party, ns["cac"] + "PostalAddress")
            if not partner_obj.street:
                raise ValidationError('Address information (i.e, Street field) of the Partner: ' + str(partner_obj.name) + ' cannot be empty.')
            else:
                etree.SubElement(address, ns["cbc"] + "StreetName").text = partner_obj.street
            if partner_obj.street2:
                etree.SubElement(address, ns["cbc"] + "AdditionalStreetName").text = partner_obj.street2
            if partner_obj.city:
                etree.SubElement(address, ns["cbc"] + "CityName").text = partner_obj.city
            if not partner_obj.zip:
                raise ValidationError('Address information (i.e, Zip field) of the Partner: ' + str(partner_obj.name) + ' cannot be empty.')
            else:
                etree.SubElement(address, ns["cbc"] + "PostalZone").text = partner_obj.zip

            country = etree.SubElement(address, ns["cac"] + "Country")
            if not partner_obj.country_id:
                raise ValidationError('Address information (i.e, Country field) of the Partner: ' + str(partner_obj.name) + ' cannot be empty.')
            else:
                etree.SubElement(country, ns["cbc"] + "IdentificationCode").text = partner_obj.country_id.code

            party_legal_entity = etree.SubElement(customer_party, ns["cac"] + "PartyLegalEntity")
            etree.SubElement(party_legal_entity, ns["cbc"] + "RegistrationName").text = partner_obj.name
            
            etree.SubElement(party_legal_entity, ns["cbc"] + "CompanyID").text = partner_obj.l10n_sg_unique_entity_number

            if self.invoice_payment_term_id:
                self._ubl_add_payment_terms(
                    self.invoice_payment_term_id, xml_root, ns, version=version
                )
            self._ubl_add_tax_total(xml_root, ns, version=version)

            if is_foreign_curr:
                self._ubl_add_tax_total_foreign_currency(xml_root, ns, version=version)

            self._ubl_add_legal_monetary_total(xml_root, ns, version=version)

            line_number = 0
            for iline in self.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_section', 'line_note')): 
                line_number += 1
                if not iline.product_uom_id:
                    raise ValidationError("'Unit of Measure(UOM)' is not defined for the Invoice line.")
                elif not iline.product_uom_id.unece_code:
                    raise ValidationError("'UNECE Code' is not defined for the UOM: " + str(iline.product_uom_id.name))
                self._ubl_add_invoice_line(
                    xml_root, iline, line_number, ns, version=version
                )
        else:
            nsmap, ns = self._ubl_get_credit_nsmap_namespace("CreditNote-2", version=version)
            xml_root = etree.Element("CreditNote", nsmap=nsmap)
            self._pint_add_header(xml_root, ns, version=version)
            self._ubl_add_order_reference(xml_root, ns, version=version)
            self._ubl_add_attachments(xml_root, ns, version=version)
            if is_foreign_curr:
                self._ubl_add_additional_documents(xml_root, ns, version=version)

            # Accounting Supplier Party
            supplier = etree.SubElement(xml_root, ns["cac"] + "AccountingSupplierParty")
            supplier_party = etree.SubElement(supplier, ns["cac"] + "Party")
            if not company_partner.peppol_identifier:
                raise ValidationError("The Peppol Identifer cannot be empty for the Partner: " + str(company_partner.name))
            if not company_partner.peppol_scheme:
                raise ValidationError("The Peppol Scheme cannot be empty for the Partner: " + str(company_partner.name))
            supplier_party_endpoint = etree.SubElement(supplier_party, ns["cbc"] + "EndpointID", schemeID=company_partner.peppol_scheme)
            supplier_party_endpoint.text = company_partner.peppol_identifier

            party_ident = etree.SubElement(supplier_party, ns["cac"] + "PartyIdentification")
            etree.SubElement(party_ident, ns["cbc"] + "ID", schemeID="0195").text = company_partner.l10n_sg_unique_entity_number
            party_name = etree.SubElement(supplier_party, ns["cac"] + "PartyName")
            etree.SubElement(party_name, ns["cbc"] + "Name").text = company_partner.name
            address = etree.SubElement(supplier_party, ns["cac"] + "PostalAddress")
            if not company_partner.street:
                raise ValidationError('Address information (i.e, Street field) of the Partner: ' + str(company_partner.name) + ' cannot be empty.')
            else:
                etree.SubElement(address, ns["cbc"] + "StreetName").text = company_partner.street
            if company_partner.street2:
                etree.SubElement(address, ns["cbc"] + "AdditionalStreetName").text = company_partner.street2
            if company_partner.city:
                etree.SubElement(address, ns["cbc"] + "CityName").text = company_partner.city
            if not company_partner.zip:
                raise ValidationError('Address information (i.e, Zip field) of the Partner: ' + str(company_partner.name) + ' cannot be empty.')
            else:
                etree.SubElement(address, ns["cbc"] + "PostalZone").text = company_partner.zip
            if not company_partner.country_id:
                raise ValidationError('Address information (i.e, Country field) of the Partner: ' + str(company_partner.name) + ' cannot be empty.')
            else:
                country = etree.SubElement(address, ns["cac"] + "Country")
                etree.SubElement(country, ns["cbc"] + "IdentificationCode").text = company_partner.country_id.code

            party_tax_scheme = etree.SubElement(supplier_party, ns["cac"] + "PartyTaxScheme")
            if not company_partner.vat:
                raise ValidationError('GST Reg No. is not provided to the Partner: ' + str(company_partner.name))
            etree.SubElement(party_tax_scheme, ns["cbc"] + "CompanyID").text = company_partner.vat
            party_tax_scheme_1 = etree.SubElement(party_tax_scheme, ns["cac"] + "TaxScheme")
            etree.SubElement(party_tax_scheme_1, ns["cbc"] + "ID").text = 'GST'

            party_legal_entity = etree.SubElement(supplier_party, ns["cac"] + "PartyLegalEntity")
            etree.SubElement(party_legal_entity, ns["cbc"] + "RegistrationName").text = company_partner.name
            if not company_partner.l10n_sg_unique_entity_number:
                raise ValidationError('UEN no is not defined to the Partner: ' + str(company_partner.name))
            etree.SubElement(party_legal_entity, ns["cbc"] + "CompanyID").text = company_partner.l10n_sg_unique_entity_number

            # Accounting Customer Party
            customer = etree.SubElement(xml_root, ns["cac"] + "AccountingCustomerParty")
            customer_party = etree.SubElement(customer, ns["cac"] + "Party")
            if not partner_obj.peppol_identifier:
                raise ValidationError("The Peppol Identifer cannot be empty for the Partner: " + str(partner_obj.name))
            if not partner_obj.peppol_scheme:
                raise ValidationError("The Peppol Scheme cannot be empty for the Partner: " + str(partner_obj.name))
            if not partner_obj.l10n_sg_unique_entity_number:
                raise ValidationError('UEN no is not defined to the Partner: ' + str(partner_obj.name))
            if not partner_obj.is_peppol_participant:
                peppol_identifier = 'C5UID' + str(partner_obj.l10n_sg_unique_entity_number)
            else:
                peppol_identifier = partner_obj.peppol_identifier
            customer_party_endpoint = etree.SubElement(customer_party, ns["cbc"] + "EndpointID", schemeID=partner_obj.peppol_scheme)
            customer_party_endpoint.text = peppol_identifier

            party_ident = etree.SubElement(customer_party, ns["cac"] + "PartyIdentification")
            etree.SubElement(party_ident, ns["cbc"] + "ID", schemeID="0195").text = partner_obj.l10n_sg_unique_entity_number

            party_name = etree.SubElement(customer_party, ns["cac"] + "PartyName")
            etree.SubElement(party_name, ns["cbc"] + "Name").text = partner_obj.name
            address = etree.SubElement(customer_party, ns["cac"] + "PostalAddress")
            if not partner_obj.street:
                raise ValidationError('Address information (i.e, Street field) of the Partner: ' + str(partner_obj.name) + ' cannot be empty.')
            else:
                etree.SubElement(address, ns["cbc"] + "StreetName").text = partner_obj.street
            if partner_obj.street2:
                etree.SubElement(address, ns["cbc"] + "AdditionalStreetName").text = partner_obj.street2
            if partner_obj.city:
                etree.SubElement(address, ns["cbc"] + "CityName").text = partner_obj.city
            if not partner_obj.zip:
                raise ValidationError('Address information (i.e, Zip field) of the Partner: ' + str(partner_obj.name) + ' cannot be empty.')
            else:
                etree.SubElement(address, ns["cbc"] + "PostalZone").text = partner_obj.zip

            country = etree.SubElement(address, ns["cac"] + "Country")
            if not partner_obj.country_id:
                raise ValidationError('Address information (i.e, Country field) of the Partner: ' + str(partner_obj.name) + ' cannot be empty.')
            else:
                etree.SubElement(country, ns["cbc"] + "IdentificationCode").text = partner_obj.country_id.code

            party_legal_entity = etree.SubElement(customer_party, ns["cac"] + "PartyLegalEntity")
            etree.SubElement(party_legal_entity, ns["cbc"] + "RegistrationName").text = partner_obj.name
            
            etree.SubElement(party_legal_entity, ns["cbc"] + "CompanyID").text = partner_obj.l10n_sg_unique_entity_number

            if self.invoice_payment_term_id:
                self._ubl_add_payment_terms(
                    self.invoice_payment_term_id, xml_root, ns, version=version
                )

            self._ubl_add_tax_total(xml_root, ns, version=version)
            if is_foreign_curr:
                self._ubl_add_tax_total_foreign_currency(xml_root, ns, version=version)
            self._ubl_credit_add_legal_monetary_total(xml_root, ns, version=version)

            line_number = 0
            for iline in self.invoice_line_ids:
                line_number += 1
                if not iline.product_uom_id:
                    raise ValidationError("'Unit of Measure(UOM)' is not defined for the Credit line.")
                elif not iline.product_uom_id.unece_code:
                    raise ValidationError("'UNECE Code' is not defined for the UOM: " + str(iline.product_uom_id.name))
                self._ubl_add_creditnote_line(
                        xml_root, iline, line_number, ns, version=version
                    )

        xml_string = etree.tostring(
            xml_root, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )
        print("\nxml_string ===",xml_string)
        return xml_string


    def _ubl_add_tax_total(self, xml_root, ns, version="2.1"):
        print("\n\n_ubl_add_tax_total() >>>>>>>>")
        self.ensure_one()
        cur_name = self.currency_id.name
        tax_total_node = etree.SubElement(xml_root, ns["cac"] + "TaxTotal")
        tax_amount_node = etree.SubElement(
            tax_total_node, ns["cbc"] + "TaxAmount", currencyID=cur_name
        )
        prec = self.currency_id.decimal_places
        tax_amount_node.text = "%0.*f" % (prec, self.amount_tax)
        added_tax_subtotal = False
        is_gst = False
        tax_objs = self.line_ids.mapped('tax_ids')
        print("tax_objs ===",tax_objs)
        if any(tax.unece_categ_id and tax.unece_categ_id.code == 'SR' for tax in tax_objs):
            is_gst = True
        if is_gst == True: #TODO: #is_gst
            tax_lines = self.line_ids.filtered(lambda line: line.tax_line_id)
            print("tax_lines ===",tax_lines)
            # Metro commented
            # res = {}
            # done_taxes = set()
            # for line in tax_lines:
            #     res.setdefault(
            #         line.tax_line_id.tax_group_id,
            #         {"base": 0.0, "amount": 0.0, "tax": False},
            #     )
            #     res[line.tax_line_id.tax_group_id]["amount"] += line.price_subtotal
            #     tax_key_add_base = tuple(self._get_tax_key_for_group_add_base(line))
            #     if tax_key_add_base not in done_taxes:
            #         res[line.tax_line_id.tax_group_id]["base"] += line.tax_base_amount
            #         res[line.tax_line_id.tax_group_id]["tax"] = line.tax_line_id
            #         done_taxes.add(tax_key_add_base)
            # res = sorted(res.items(), key=lambda l: l[0].sequence)

            res = {}
            done_taxes = set()

            for line in self.invoice_line_ids:
                print('\n\n\n\n\nlineeee', line)
                # Loop through all taxes in Many2many field
                for tax in line.tax_ids:
                    print('\n\n\n\n\ntax<<<<', tax, tax.name)
                    tax_values = tax.compute_all(
                        line.price_unit * line.quantity,  # Line subtotal before tax
                        currency=self.currency_id,
                        quantity=1.0,  # Compute tax per unit
                        product=line.product_id,
                        partner=self.partner_id,
                    )
                    tax_categ = tax.unece_categ_id
                    res.setdefault(
                        tax_categ, {"base": 0.0, "amount": 0.0, "tax": False}
                    )
                    # Use correct computed tax amount
                    for computed_tax in tax_values['taxes']:
                        if computed_tax['id'] == tax.id:
                            res[tax_categ]["amount"] += computed_tax['amount']
                    # Unique key per tax per line
                    tax_key_add_base = (tax.id, line.id)

                    if tax_key_add_base not in done_taxes:
                        res[tax_categ]["base"] += tax_values["total_excluded"]
                        res[tax_categ]["tax"] = tax
                        done_taxes.add(tax_key_add_base)                        
            # Sort by tax group sequence
            res = sorted(res.items(), key=lambda l: l[0].id)
            print("\nres ===",res)
            prec = self.currency_id.decimal_places
            for _group, amounts in res:
                self._ubl_add_tax_subtotal(
                    self.amount_untaxed if self.discount_total > 0 else amounts["base"],
                    self.amount_tax if self.discount_total > 0 else amounts["amount"],
                    amounts["tax"],
                    cur_name,
                    tax_total_node,
                    ns,
                    version=version,
                )
                added_tax_subtotal = True
            if not added_tax_subtotal:
                self._ubl_add_tax_subtotal(
                    0.0,
                    0.0,
                    tax_objs[0] if tax_objs else 0.0,
                    cur_name,
                    tax_total_node,
                    ns,
                    version=version,
                )
                added_tax_subtotal = True
        if not added_tax_subtotal:
            print("\nadded_tax_subtotal is FALSEEE")
            prec = self.env["decimal.precision"].precision_get("Account")
            tax_subtotal = etree.SubElement(tax_total_node, ns["cac"] + "TaxSubtotal")
            taxable_amount_node = etree.SubElement(
                tax_subtotal, ns["cbc"] + "TaxableAmount", currencyID=cur_name
            )
            taxable_amount_node.text = "%0.*f" % (prec, self.amount_total)
            tax_amount_node = etree.SubElement(
                tax_subtotal, ns["cbc"] + "TaxAmount", currencyID=cur_name
            )
            tax_amount_node.text = "0.00"
            self._ubl_add_notax_category(False, tax_subtotal, ns, node_name="TaxCategory", version=version)

    def _ubl_add_tax_subtotal(
            self,
            taxable_amount,
            tax_amount,
            tax,
            currency_code,
            parent_node,
            ns,
            version="2.1",
    ):
        """ Overidden method from base_ubl module. """
        prec = self.env["decimal.precision"].precision_get("Account")
        tax_subtotal = etree.SubElement(parent_node, ns["cac"] + "TaxSubtotal")
        if not float_is_zero(taxable_amount, precision_digits=prec):
            taxable_amount_node = etree.SubElement(
                tax_subtotal, ns["cbc"] + "TaxableAmount", currencyID=currency_code
            )
            taxable_amount_node.text = "%0.*f" % (prec, taxable_amount)
        tax_amount_node = etree.SubElement(
            tax_subtotal, ns["cbc"] + "TaxAmount", currencyID=currency_code
        )
        tax_amount_node.text = "%0.*f" % (prec, tax_amount)
        self._ubl_add_tax_category(tax, tax_subtotal, ns, node_name="TaxCategory", version=version)

    @api.model
    def _ubl_add_tax_category(self, tax, parent_node, ns, node_name="ClassifiedTaxCategory", version="2.1"):
        """ Overidden method from base_ubl module. """
        if tax:
            if not tax.unece_categ_id:
                raise UserError(_("Missing UNECE Tax Category on tax '%s'" % tax.name))
            classified_tax_categ_node = etree.SubElement(parent_node, ns["cac"] + node_name)
            unece_categ_code_node = etree.SubElement(classified_tax_categ_node, ns["cbc"] + "ID")
            unece_categ_code_node.text = tax.unece_categ_code
            tax_percent_node = etree.SubElement(classified_tax_categ_node, ns["cbc"] + "Percent")
            tax_percent_node.text = str(float_round(tax.amount, precision_digits=1))
            tax_scheme_node = etree.SubElement(classified_tax_categ_node, ns["cac"] + "TaxScheme")
            tax_scheme_id_node = etree.SubElement(tax_scheme_node, ns["cbc"] + "ID")
            tax_scheme_id_node.text = 'GST'

    @api.model
    def _ubl_add_notax_category(self, tax, parent_node, ns, node_name="ClassifiedTaxCategory", version="2.1"):
        print("Called _ubl_add_notax_category() >>>")
        unece_categ = self.env['unece.code.list'].sudo().search([('type', '=', 'tax_categ'), ('code', '=', 'NA')])
        if not unece_categ:
            raise UserError(_("Missing UNECE Tax Category: '%s'" % unece_categ.code))
        classified_tax_categ_node = etree.SubElement(parent_node, ns["cac"] + node_name)
        if unece_categ:
            unece_categ_code_node = etree.SubElement(classified_tax_categ_node, ns["cbc"] + "ID")
            unece_categ_code_node.text = unece_categ.code
        tax_percent_node = etree.SubElement(classified_tax_categ_node, ns["cbc"] + "Percent")
        tax_percent_node.text = "0"
        tax_scheme_node = etree.SubElement(classified_tax_categ_node, ns["cac"] + "TaxScheme")
        tax_scheme_id_node = etree.SubElement(tax_scheme_node, ns["cbc"] + "ID")
        tax_scheme_id_node.text = 'GST'

    def _ubl_add_legal_monetary_total(self, parent_node, ns, version="2.1"):
        self.ensure_one()
        monetary_total = etree.SubElement(parent_node, ns["cac"] + "LegalMonetaryTotal")
        cur_name = self.currency_id.name
        prec = self.currency_id.decimal_places
        line_total = etree.SubElement(
            monetary_total, ns["cbc"] + "LineExtensionAmount", currencyID=cur_name
        )
        line_total.text = "%0.*f" % (prec, self.amount_untaxed)
        tax_excl_total = etree.SubElement(
            monetary_total, ns["cbc"] + "TaxExclusiveAmount", currencyID=cur_name
        )
        tax_excl_total.text = "%0.*f" % (prec, self.amount_untaxed)
        tax_incl_total = etree.SubElement(
            monetary_total, ns["cbc"] + "TaxInclusiveAmount", currencyID=cur_name
        )
        tax_incl_total.text = "%0.*f" % (prec, self.amount_total)


        prepaid_amount = etree.SubElement(
            monetary_total, ns["cbc"] + "PrepaidAmount", currencyID=cur_name
        )
        prepaid_value = self.amount_total - self.amount_residual
        prepaid_amount.text = "%0.*f" % (prec, prepaid_value)
        payable_amount = etree.SubElement(
            monetary_total, ns["cbc"] + "PayableAmount", currencyID=cur_name
        )
        payable_amount.text = "%0.*f" % (prec, self.amount_residual)

    @api.model
    def _ubl_add_item(
        self,
        name,
        product,
        parent_node,
        ns,
        iline,
        type_="purchase",
        seller=False,
        version="2.1"):
        """Beware that product may be False (in particular on invoices)"""
        assert type_ in ("sale", "purchase"), "Wrong type param"
        # assert name, "name is a required arg"
        item = etree.SubElement(parent_node, ns["cac"] + "Item")
        product_name = False
        seller_code = False
        if product:
            if type_ == "purchase":
                if seller:
                    sellers = product._select_seller(
                        partner_id=seller, quantity=0.0, date=None, uom_id=False
                    )
                    if sellers:
                        product_name = sellers[0].product_name
                        seller_code = sellers[0].product_code
            if not seller_code:
                seller_code = product.default_code
            if not product_name:
                variant = ", ".join(product.attribute_line_ids.mapped("value_ids.name"))
                product_name = (
                    variant and "{} ({})".format(product.name, variant) or product.name
                )
        description = etree.SubElement(item, ns["cbc"] + "Description")
        description.text = product_name or name.split("\n")[0]
        name_node = etree.SubElement(item, ns["cbc"] + "Name")
        name_node.text = product_name or name.split("\n")[0]
        if seller_code:
            seller_identification = etree.SubElement(
                item, ns["cac"] + "SellersItemIdentification"
            )
            seller_identification_id = etree.SubElement(
                seller_identification, ns["cbc"] + "ID"
            )
            seller_identification_id.text = seller_code
        if product:
            if product.barcode:
                std_identification = etree.SubElement(
                    item, ns["cac"] + "StandardItemIdentification"
                )
                std_identification_id = etree.SubElement(
                    std_identification,
                    ns["cbc"] + "ID",
                    schemeID="0195",
                )
                std_identification_id.text = product.barcode
            # I'm not 100% sure, but it seems that ClassifiedTaxCategory
            # contains the taxes of the product without taking into
            # account the fiscal position
            # if type_ == "sale":
            #     taxes = iline.tax_ids
            # else:
            #     taxes = product.supplier_taxes_id
            # print("product ===",product)
            # sr_tax_obj = False
            # tax_objs = iline.move_id.invoice_line_ids.mapped('tax_ids')
            # for tax in tax_objs:
            #     if tax.unece_categ_id and tax.unece_categ_id.code == 'SR':
            #         sr_tax_obj = tax
            # print("sr_tax_obj ===",sr_tax_obj)
            # if taxes:
            #     for tax in taxes:
            #         self._ubl_add_tax_category(
            #             tax,
            #             item,
            #             ns,
            #             node_name="ClassifiedTaxCategory",
            #             version=version,
            #         )
            # else:
            #     if sr_tax_obj:
            #         self._ubl_add_tax_category(
            #             sr_tax_obj,
            #             item,
            #             ns,
            #             node_name="ClassifiedTaxCategory",
            #             version=version,
            #         )
            #     else:
            #         self._ubl_add_notax_category(
            #                 False,
            #                 item,
            #                 ns,
            #                 node_name="ClassifiedTaxCategory",
            #                 version=version,
            #             )
            if type_ in ("sale", "purchase"):
                taxes = iline.tax_ids
                if taxes:
                    for tax in taxes:
                        print('\n\n\nline_tax', tax)
                        self._ubl_add_tax_category(
                            tax,
                            item,
                            ns,
                            node_name="ClassifiedTaxCategory",
                            version=version,
                        )
                else:
                    self._ubl_add_notax_category(
                        False,
                        item,
                        ns,
                        node_name="ClassifiedTaxCategory",
                        version=version,
                    )
            for attribute_value in product.attribute_line_ids.mapped("value_ids"):
                item_property = etree.SubElement(
                    item, ns["cac"] + "AdditionalItemProperty"
                )
                property_name = etree.SubElement(item_property, ns["cbc"] + "Name")
                property_name.text = attribute_value.attribute_id.name
                property_value = etree.SubElement(item_property, ns["cbc"] + "Value")
                property_value.text = attribute_value.name

    def _ubl_add_invoice_line(self, parent_node, iline, line_number, ns, version="2.1"):
        self.ensure_one()
        cur_name = self.currency_id.name
        line_root = etree.SubElement(parent_node, ns["cac"] + "InvoiceLine")
        dpo = self.env["decimal.precision"]
        qty_precision = dpo.precision_get("Product Unit of Measure")
        price_precision = dpo.precision_get("Product Price")
        account_precision = self.currency_id.decimal_places
        line_id = etree.SubElement(line_root, ns["cbc"] + "ID")
        line_id.text = str(line_number)
        uom_unece_code = False
        # product_uom_id is not a required field on account.move.line
        if iline.product_uom_id.unece_code:
            uom_unece_code = iline.product_uom_id.unece_code
            quantity = etree.SubElement(
                line_root, ns["cbc"] + "InvoicedQuantity", unitCode=uom_unece_code
            )
        else:
            quantity = etree.SubElement(line_root, ns["cbc"] + "InvoicedQuantity")        
        qty = iline.quantity
        quantity.text = "%0.*f" % (qty_precision, qty)
        line_amount = etree.SubElement(
            line_root, ns["cbc"] + "LineExtensionAmount", currencyID=cur_name
        )
        line_amount.text = "%0.*f" % (account_precision, iline.price_subtotal)
        # :: NOT REQUIRED ::
        # self._ubl_add_invoice_line_tax_total(iline, line_root, ns, version=version)
        #
        # :: NOT REQUIRED ::
        # self._ubl_add_invoice_line_tax_category(
        #     iline, line_root, ns, version=version
        # )
        # Adding the OrderLineReference 
        if iline.sale_line_ids and iline.sale_line_ids[0].incoming_order_line_id:
            order_line_ref_root = etree.SubElement(line_root, ns["cac"] + "OrderLineReference")
            order_lineref_id = etree.SubElement(order_line_ref_root, ns["cbc"] + "LineID")
            order_lineref_id.text = iline.sale_line_ids[0].incoming_order_line_id.line_item_id
        else: #TODO..
            if iline.line_item_id:
                order_line_ref_root = etree.SubElement(line_root, ns["cac"] + "OrderLineReference")
                order_lineref_id = etree.SubElement(order_line_ref_root, ns["cbc"] + "LineID")
                order_lineref_id.text = iline.line_item_id

        self._ubl_add_item(
            iline.name, iline.product_id, line_root, ns, iline, type_="sale", version=version
        )
        price_node = etree.SubElement(line_root, ns["cac"] + "Price")
        price_amount = etree.SubElement(
            price_node, ns["cbc"] + "PriceAmount", currencyID=cur_name
        )
        # price_unit = 0.0
        # Use price_subtotal/qty to compute price_unit to be sure
        # to get a *tax_excluded* price unit
        # if not float_is_zero(qty, precision_digits=qty_precision):

            # price_amount.text = "%0.*f" % (price_precision, price_unit)
            # price_unit = float_round(
            #     iline.price_subtotal / float(qty), precision_digits=price_precision
            # )
        price_unit = iline.price_unit
        price_amount.text = "%0.*f" % (price_precision, price_unit)
        if uom_unece_code:
            base_qty = etree.SubElement(
                price_node, ns["cbc"] + "BaseQuantity", unitCode=uom_unece_code
            )
        else:
            base_qty = etree.SubElement(price_node, ns["cbc"] + "BaseQuantity")
        base_qty.text = "%0.*f" % (qty_precision, 1.0)
        # TODO :: Review :: My Custom Code
        #  if iline.discount != 0.0:
        #     self._ubl_add_invoice_line_allowance_charge(
        #         iline, line_root, ns, version=version
        #     )

    def _ubl_add_attachments(self, parent_node, ns, version="2.1"):
        self.ensure_one()
        print('\n\n')
        if self.company_id.embed_pdf_in_ubl_xml_invoice and not self.env.context.get(
                "no_embedded_pdf"
        ):
            for attachment in self.env['ir.attachment'].search([('res_id', '=', self.id),('res_model','=','account.move')]):
                print('\n\n\n\n\nattachment', attachment)
                docu_reference = etree.SubElement(
                    parent_node, ns["cac"] + "AdditionalDocumentReference"
                )
                docu_reference_id = etree.SubElement(docu_reference, ns["cbc"] + "ID")
                docu_reference_id.text = attachment.name
                if attachment.description:
                    docu_description = etree.SubElement(docu_reference, ns["cbc"] + "DocumentDescription")
                    docu_description.text = attachment.description
                attach_node = etree.SubElement(docu_reference, ns["cac"] + "Attachment")
                binary_node = etree.SubElement(
                    attach_node,
                    ns["cbc"] + "EmbeddedDocumentBinaryObject",
                    mimeCode=attachment.mimetype,
                    filename=attachment.name,
                )   
                # binary_node.text = base64.b64encode(attachment.datas)
                binary_node.text = attachment.datas.decode()

            # filename = "Invoice-" + self.name + ".pdf"
            # docu_reference = etree.SubElement(
            #     parent_node, ns["cac"] + "AdditionalDocumentReference"
            # )
            # docu_reference_id = etree.SubElement(docu_reference, ns["cbc"] + "ID")
            # docu_reference_id.text = filename
            # attach_node = etree.SubElement(docu_reference, ns["cac"] + "Attachment")
            # binary_node = etree.SubElement(
            #     attach_node,
            #     ns["cbc"] + "EmbeddedDocumentBinaryObject",
            #     mimeCode="application/pdf",
            #     filename=filename,
            # )
            # ctx = dict()
            # ctx["no_embedded_ubl_xml"] = True
            # ctx["force_report_rendering"] = True
            # pdf_inv = (
            #     self.with_context(ctx).env.ref("account.account_invoices")._render_qweb_pdf(self.ids)[0]
            # )
            # binary_node.text = base64.b64encode(pdf_inv)

    def _ubl_add_order_reference(self, parent_node, ns, version="2.1"):
        self.ensure_one()
        if self.invoice_origin:
            sale_obj = self.env['sale.order'].sudo().search([('name', '=', self.invoice_origin)], limit=1)
                # advance order invoice codition
            if sale_obj and sale_obj.incoming_order_id and (sale_obj.document_type or sale_obj.incoming_order_id.document_type):
                order_ref = etree.SubElement(parent_node, ns["cac"] + "OrderReference")
                order_ref_id = etree.SubElement(order_ref, ns["cbc"] + "ID")
                order_ref_id.text = sale_obj.incoming_order_id.order_reference or self.order_ref or 'NA'
                so_ref_id = etree.SubElement(order_ref, ns["cbc"] + "SalesOrderID")
                so_ref_id.text = sale_obj.origin
            elif sale_obj and sale_obj.origin and (not sale_obj.document_type):
                order_ref = etree.SubElement(parent_node, ns["cac"] + "OrderReference")
                order_ref_id = etree.SubElement(order_ref, ns["cbc"] + "ID")
                order_ref_id.text = sale_obj.origin or 'NA'

    def _ubl_add_header(self, parent_node, ns, version="2.1"):
        self.ensure_one()
        ubl_version = etree.SubElement(parent_node, ns["cbc"] + "UBLVersionID")
        ubl_version.text = version
        ubl_customization_id = etree.SubElement(parent_node, ns["cbc"] + "CustomizationID")
        ubl_customization_id.text = "urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:sg:3.0"
        ubl_profile_id = etree.SubElement(parent_node, ns["cbc"] + "ProfileID")
        ubl_profile_id.text = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"
        doc_id = etree.SubElement(parent_node, ns["cbc"] + "ID")
        doc_id.text = self.name
        random_uuid = uuid.uuid4()
        uuid_var = etree.SubElement(parent_node, ns["cbc"] + "UUID")
        uuid_var.text = str(random_uuid)
        issue_date = etree.SubElement(parent_node, ns["cbc"] + "IssueDate")
        issue_date.text = self.invoice_date.strftime("%Y-%m-%d")
        due_date = etree.SubElement(parent_node, ns["cbc"] + "DueDate")
        due_date.text = self.invoice_date_due.strftime("%Y-%m-%d")
        type_code = etree.SubElement(parent_node, ns["cbc"] + "InvoiceTypeCode")
        if self.move_type == "out_invoice":
            type_code.text = "380"
        elif self.move_type == "out_refund":
            type_code.text = "381"
        if self.narration:
            note = etree.SubElement(parent_node, ns["cbc"] + "Note")
            note.text = self.narration
        doc_currency = etree.SubElement(parent_node, ns["cbc"] + "DocumentCurrencyCode")
        doc_currency.text = self.currency_id.name
        if self.currency_id.id != self.company_id.currency_id.id:
            logger.error("\n\nForegin currency......")
            tax_curr_code = etree.SubElement(parent_node, ns["cbc"] + "TaxCurrencyCode")
            tax_curr_code.text = self.company_id.currency_id.name
        if self.business_unit_id:
            buyer_reference = etree.SubElement(parent_node, ns["cbc"] + "BuyerReference")
            buyer_reference.text = self.business_unit_id.business_unit_code
        else:
            if self.ref:
                buyer_reference = etree.SubElement(parent_node, ns["cbc"] + "BuyerReference")
                buyer_reference.text = self.ref
            elif self.invoice_user_id:
                buyer_reference = etree.SubElement(parent_node, ns["cbc"] + "BuyerReference") #TODO::
                buyer_reference.text = self.invoice_user_id.name

    @api.model
    def _ubl_get_nsmap_namespace(self, doc_name, version="2.1"):
        """ Overidden method from base_ubl module. """
        nsmap = {
            None: "urn:oasis:names:specification:ubl:schema:xsd:" + doc_name,
            "cac": "urn:oasis:names:specification:ubl:"
                   "schema:xsd:CommonAggregateComponents-2",
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:"
                   "CommonBasicComponents-2",
            "ccts": "urn:un:unece:uncefact:documentation:2",
            "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
            "qdt": "urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2",
            "udt": "urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2",
            "xsd": "http://www.w3.org/2001/XMLSchema",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        }
        ns = {
            "cac": "{urn:oasis:names:specification:ubl:schema:xsd:"
                   "CommonAggregateComponents-2}",
            "cbc": "{urn:oasis:names:specification:ubl:schema:xsd:"
                   "CommonBasicComponents-2}",
        }
        return nsmap, ns

    @api.model
    def _ubl_get_contact_id(self, partner):
        return False

    @api.model
    def _ubl_add_contact(
            self, partner, parent_node, ns, node_name="Contact", version="2.1"
    ):
        contact = etree.SubElement(parent_node, ns["cac"] + node_name)
        contact_id_text = self._ubl_get_contact_id(partner)
        if contact_id_text:
            contact_id = etree.SubElement(contact, ns["cbc"] + "ID")
            contact_id.text = contact_id_text
        # if partner.parent_id:
        #     contact_name = etree.SubElement(contact, ns["cbc"] + "Name")
        #     contact_name.text = partner.name or partner.parent_id.name
        # contact_name = etree.SubElement(contact, ns["cbc"] + "Name")
        # contact_name.text = partner.name
        contact_obj = partner.child_ids.filtered(lambda x: x.type == 'contact')[0]
        if contact_obj:
            contact_name = etree.SubElement(contact, ns["cbc"] + "Name")
            contact_name.text = contact_obj.name
        phone = partner.phone or partner.commercial_partner_id.phone
        if phone:
            telephone = etree.SubElement(contact, ns["cbc"] + "Telephone")
            telephone.text = phone
        email = partner.email or partner.commercial_partner_id.email
        if email:
            electronicmail = etree.SubElement(contact, ns["cbc"] + "ElectronicMail")
            electronicmail.text = email

    @api.model
    def _ubl_add_party_legal_entity(
            self, commercial_partner, parent_node, ns, version="2.1"
    ):
        party_legal_entity = etree.SubElement(
            parent_node, ns["cac"] + "PartyLegalEntity"
        )
        registration_name = etree.SubElement(
            party_legal_entity, ns["cbc"] + "RegistrationName"
        )
        registration_name.text = commercial_partner.name

        company_id = etree.SubElement(party_legal_entity, ns["cbc"] + "CompanyID", schemeID=commercial_partner.peppol_scheme or '')
        company_id.text = commercial_partner.l10n_sg_unique_entity_number

    @api.model
    def _ubl_add_tax_scheme(self, tax_scheme_dict, parent_node, ns, version="2.1"):
        tax_scheme = etree.SubElement(parent_node, ns["cac"] + "TaxScheme")
        if tax_scheme_dict.get("id"):
            tax_scheme_id = etree.SubElement(
                tax_scheme, ns["cbc"] + "ID"
            )
            tax_scheme_id.text = tax_scheme_dict["id"]

    @api.model
    def _ubl_get_tax_scheme_dict_from_partner(self, commercial_partner):
        tax_scheme_dict = {"id": "GST", "name": False, "type_code": False}
        return tax_scheme_dict

    @api.model
    def _ubl_add_party_tax_scheme(
            self, commercial_partner, parent_node, ns, version="2.1"):
        print("\n_ubl_add_party_tax_scheme() >>>>")
        if commercial_partner.vat:
            party_tax_scheme = etree.SubElement(
                parent_node, ns["cac"] + "PartyTaxScheme"
            )
            company_id = etree.SubElement(party_tax_scheme, ns["cbc"] + "CompanyID")
            company_id.text = commercial_partner.vat
            tax_scheme_dict = self._ubl_get_tax_scheme_dict_from_partner(
                commercial_partner
            )
            self._ubl_add_tax_scheme(
                tax_scheme_dict, party_tax_scheme, ns, version=version
            )

    @api.model
    def _ubl_add_country(self, country, parent_node, ns, version="2.1"):
        country_root = etree.SubElement(parent_node, ns["cac"] + "Country")
        country_code = etree.SubElement(country_root, ns["cbc"] + "IdentificationCode")
        country_code.text = country.code
        # country_name = etree.SubElement(country_root, ns["cbc"] + "Name")
        # country_name.text = country.name

    @api.model
    def _ubl_add_address(self, partner, node_name, parent_node, ns, version="2.1"):
        address = etree.SubElement(parent_node, ns["cac"] + node_name)
        if partner.street:
            streetname = etree.SubElement(address, ns["cbc"] + "StreetName")
            streetname.text = partner.street
        if partner.street2:
            addstreetname = etree.SubElement(
                address, ns["cbc"] + "AdditionalStreetName"
            )
            addstreetname.text = partner.street2
        if partner.city:
            city = etree.SubElement(address, ns["cbc"] + "CityName")
            city.text = partner.city
        if partner.zip:
            zip_code = etree.SubElement(address, ns["cbc"] + "PostalZone")
            zip_code.text = partner.zip
        if partner.state_id:
            state = etree.SubElement(address, ns["cbc"] + "CountrySubentity")
            state.text = partner.state_id.name
        addressline = etree.SubElement(address, ns["cac"] + "AddressLine")
        addressline_line = etree.SubElement(addressline, ns["cbc"] + "Line")
        addressline_line.text = "Sales department"
        if partner.country_id:
            self._ubl_add_country(partner.country_id, address, ns, version=version)
        else:
            logger.warning("UBL: missing country on partner %s", partner.name)

    # @api.model
    # def _ubl_get_party_identification(self, commercial_partner):
    #     """This method is designed to be inherited in localisation modules
    #     Should return a dict with key=SchemeName, value=Identifier"""
    #     return {}

    @api.model
    def _ubl_add_party(
            self, partner, company, node_name, parent_node, ns, version="2.1"):
        print("\n >>>>  _ubl_add_party() >>>>")
        print("partner ==",partner)
        print("company ==",company)
        commercial_partner = partner.commercial_partner_id
        print("commercial_partner ==",commercial_partner)
        party = etree.SubElement(parent_node, ns["cac"] + node_name)
        endpoint = etree.SubElement(party, ns["cbc"] + "EndpointID", schemeID=commercial_partner.peppol_scheme or '')
        endpoint.text = commercial_partner.peppol_identifier or ''
        if commercial_partner.seller_identifier:
            party_name = etree.SubElement(party, ns["cac"] + "PartyIdentification")
            name = etree.SubElement(party_name, ns["cbc"] + "ID")
            name.text = commercial_partner.seller_identifier
        else:
            party_name = etree.SubElement(party, ns["cac"] + "PartyIdentification")
            name = etree.SubElement(party_name, ns["cbc"] + "ID")
            name.text = commercial_partner.name
        party_name = etree.SubElement(party, ns["cac"] + "PartyName")
        name = etree.SubElement(party_name, ns["cbc"] + "Name")
        name.text = commercial_partner.name
        self._ubl_add_address(
            commercial_partner, "PostalAddress", party, ns, version=version
        )
        print("commercial_partner.vat ==",commercial_partner.vat)
        print("self.amount_tax_signed != 0.00 ==",self.amount_tax_signed != 0.00)
        # if commercial_partner.vat and self.amount_tax_signed != 0.00:
        if commercial_partner.vat:
            self._ubl_add_party_tax_scheme(commercial_partner, party, ns, version=version)
        if company or partner:
            self._ubl_add_party_legal_entity(
                commercial_partner, party, ns, version="2.1"
            )
        self._ubl_add_contact(partner, party, ns, version=version)

    @api.model
    def _ubl_add_supplier_party(
        self, partner, company, node_name, parent_node, ns, version="2.1"):
        print("\n_ubl_add_supplier_party() >>",partner, company)
        if company:
            if partner:
                assert (
                        partner.commercial_partner_id == company.partner_id
                ), "partner is wrong"
            else:
                partner = company.partner_id
        print("partner ==",partner)
        supplier_party_root = etree.SubElement(parent_node, ns["cac"] + node_name)
        self._ubl_add_party(
            partner, company, "Party", supplier_party_root, ns, version=version
        )

    @api.model
    def _ubl_add_customer_party(
        self, partner, company, node_name, parent_node, ns, version="2.1"
    ):
        print("\n_ubl_add_customer_party() >>",partner, company)
        if company:
            if partner:
                assert (
                    partner.commercial_partner_id == company.partner_id
                ), "partner is wrong"
            else:
                partner = company.partner_id
        print("partner ==",partner)
        customer_party_root = etree.SubElement(parent_node, ns["cac"] + node_name)
        self._ubl_add_party(
            partner, company, "Party", customer_party_root, ns, version=version
        )

    def _ubl_add_payee_party(self, parent_node, ns, version="2.1"):
        self.ensure_one()
        payee_partner = self.company_id.partner_id
        payee_party = etree.SubElement(parent_node, ns["cac"] + "PayeeParty")

        # 1️PartyIdentification (optional)
        if payee_partner.vat:
            party_identification = etree.SubElement(
                payee_party, ns["cac"] + "PartyIdentification"
            )
            party_id = etree.SubElement(
                party_identification, ns["cbc"] + "ID"
            )
            party_id.text = payee_partner.vat

        # 2️PartyName (mandatory)
        party_name = etree.SubElement(payee_party, ns["cac"] + "PartyName")
        name = etree.SubElement(party_name, ns["cbc"] + "Name")
        name.text = payee_partner.name


    def generate_invoice_ubl_xml_etree(self, version="2.1"):
        self.ensure_one()
        nsmap, ns = self._ubl_get_nsmap_namespace("Invoice-2", version=version)
        xml_root = etree.Element("Invoice", nsmap=nsmap)
        self._ubl_add_header(xml_root, ns, version=version)
        self._ubl_add_order_reference(xml_root, ns, version=version)
        self._ubl_add_attachments(xml_root, ns, version=version)
        if self.currency_id.id != self.company_id.currency_id.id:
            self._ubl_add_additional_documents(xml_root, ns, version=version)
        self._ubl_add_supplier_party(
            False,
            self.company_id,
            "AccountingSupplierParty",
            xml_root,
            ns,
            version=version,
        )
        self._ubl_add_customer_party(
            self.partner_id,
            False,
            "AccountingCustomerParty",
            xml_root,
            ns,
            version=version,
        )
        if self.company_id.partner_id.vat == self.company_id.partner_id.seller_identifier:
            pass
        else:
            self._ubl_add_payee_party(xml_root, ns, version=version)

        # the field 'partner_shipping_id' is defined in the 'sale' module
        # :: I SET IT AS OPTIONAL ::
        # if hasattr(self, "partner_shipping_id") and self.partner_shipping_id:
        #     self._ubl_add_delivery(self.partner_shipping_id, xml_root, ns)
        # # Put paymentmeans block even when invoice is paid ?
        # :: I SET IT AS OPTIONAL ::
        # payment_identifier = self.get_payment_identifier()
        # self._ubl_add_payment_means(
        #     self.invoice_partner_bank_id,
        #     self.payment_mode_id,
        #     self.invoice_date_due,
        #     xml_root,
        #     ns,
        #     payment_identifier=payment_identifier,
        #     version=version,
        #
        if self.invoice_payment_term_id:
            self._ubl_add_payment_terms(
                self.invoice_payment_term_id, xml_root, ns, version=version
            )
        self._ubl_add_tax_total(xml_root, ns, version=version)
        if self.currency_id.id != self.company_id.currency_id.id:
            self._ubl_add_tax_total_foreign_currency(xml_root, ns, version=version)
        self._ubl_add_legal_monetary_total(xml_root, ns, version=version)

        line_number = 0
        for iline in self.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_section', 'line_note')): 
            line_number += 1
            self._ubl_add_invoice_line(
                xml_root, iline, line_number, ns, version=version
            )
        return xml_root

    def get_ubl_filename(self, version="2.1"):
        """This method is designed to be inherited"""
        return "UBL-Invoice-%s.xml" % version

    def get_ubl_version(self):
        return self.env.context.get("ubl_version") or "2.1"

    def get_ubl_lang(self):
        self.ensure_one()
        return self.partner_id.lang or "en_US"

    def generate_ubl_xml_string(self, version="2.1"):
        self.ensure_one()
        assert self.state == "posted"
        assert self.move_type in ("out_invoice", "out_refund")
        logger.debug("Starting to generate UBL XML Invoice file")
        lang = self.get_ubl_lang()
        # The aim of injecting lang in context
        # is to have the content of the XML in the partner's lang
        # but the problem is that the error messages will also be in
        # that lang. But the error messages should almost never
        # happen except the first days of use, so it's probably
        # not worth the additional code to handle the 2 langs
        xml_root = self.with_context(lang=lang).generate_invoice_ubl_xml_etree(
            version=version
        )
        xml_string = etree.tostring(
            xml_root, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )
        self._ubl_check_xml_schema(xml_string, "Invoice", version=version)
        logger.debug(
            "Invoice UBL XML file generated for account invoice ID %d " "(state %s)",
            self.id,
            self.state,
        )
        logger.debug(xml_string.decode("utf-8"))
        return xml_string

    def generate_ubl_report(self, version='2.1'):
        self.ensure_one()
        assert self.move_type in ("out_invoice", "out_refund")
        assert self.state == "posted"
        version = self.get_ubl_version()
        xml_string = self.generate_ubl_xml_string(version=version)
        filename = self.get_ubl_filename(version=version)
        attach = (
            self.env["ir.attachment"]
                .with_context({})
                .create(
                {
                    "name": filename,
                    "res_id": self.id,
                    "res_model": self._name,
                    "datas": base64.b64encode(xml_string),
                    # If default_type = 'out_invoice' in context, 'type'
                    # would take 'out_invoice' value by default !
                    "type": "binary",
                }
            )
        )
        action = self.env["ir.attachment"].action_get()
        action.update({"res_id": attach.id, "views": False, "view_mode": "form,tree"})
        return action

    def generate_credit_ubl_xml_string(self, version="2.1"):
        self.ensure_one()
        assert self.state == "posted"
        assert self.move_type in ("out_invoice", "out_refund")
        logger.debug("Starting to generate UBL XML CreditNote file")
        lang = self.get_ubl_lang()
        xml_root = self.with_context(lang=lang).generate_credit_ubl_xml_etree(
            version=version
        )
        print("xml_root >>>>>>>>>>", xml_root)
        xml_string = etree.tostring(
            xml_root, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )
        print("xml_string >>>>>>>>>>",xml_string)
        self._ubl_check_xml_schema(xml_string, "CreditNote", version=version)
        logger.debug(
            "Credit Note UBL XML file generated for account Credit ID %d " "(state %s)",
            self.id,
            self.state,
        )
        logger.debug(xml_string.decode("utf-8"))
        return xml_string

    # prakash
    def _ubl_credit_add_sbd_header(self, parent_node):
        """ Creates the StandardBusinessDocumentHeader part of the XML. """
        sbdh_ns = {None: "http://www.unece.org/cefact/namespaces/StandardBusinessDocumentHeader"}

        sbd_header = etree.SubElement(parent_node, "StandardBusinessDocumentHeader", nsmap=sbdh_ns)

        # Header Version
        header_version = etree.SubElement(sbd_header, "HeaderVersion")
        header_version.text = "1.0"

        # Sender
        sender = etree.SubElement(sbd_header, "Sender")
        sender_id = etree.SubElement(sender, "Identifier", Authority="iso6523-actorid-upis")
        sender_id.text = self.company_id.partner_id.commercial_partner_id.peppol_identifier

        # Receiver
        receiver = etree.SubElement(sbd_header, "Receiver")
        receiver_id = etree.SubElement(receiver, "Identifier", Authority="iso6523-actorid-upis")
        receiver_id.text = "IRAS"

        # Document Identification
        doc_ident = etree.SubElement(sbd_header, "DocumentIdentification")
        standard = etree.SubElement(doc_ident, "Standard")
        standard.text = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"

        type_version = etree.SubElement(doc_ident, "TypeVersion")
        type_version.text = "2.1"

        access_point = self.env['peppol.access.point.sg'].sudo().search([('company_id', '=', self.company_id.id)],
                                                                        order="create_date")
        transmission_uuid = access_point.get_uuid()
        instance_id = etree.SubElement(doc_ident, "InstanceIdentifier")
        instance_id.text = transmission_uuid

        doc_type = etree.SubElement(doc_ident, "Type")
        doc_type.text = "CreditNote"

        creation_date = etree.SubElement(doc_ident, "CreationDateAndTime")
        creation_date.text = fields.Datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Business Scope
        business_scope = etree.SubElement(sbd_header, "BusinessScope")

        # Scope 1
        scope1 = etree.SubElement(business_scope, "Scope")
        scope1_type = etree.SubElement(scope1, "Type")
        scope1_type.text = "DOCUMENTID"
        scope1_instance = etree.SubElement(scope1, "InstanceIdentifier")
        scope1_instance.text = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:peppol:pint:billing-1@sg-1:LocalTaxInvoice:sg:1.0::2.1"
        scope1_id = etree.SubElement(scope1, "Identifier")
        scope1_id.text = "peppol-doctype-wildcard"

        # Scope 2
        scope2 = etree.SubElement(business_scope, "Scope")
        scope2_type = etree.SubElement(scope2, "Type")
        scope2_type.text = "PROCESSID"
        scope2_instance = etree.SubElement(scope2, "InstanceIdentifier")
        scope2_instance.text = "urn:peppol:bis:billing"
        scope2_id = etree.SubElement(scope2, "Identifier")
        scope2_id.text = "cenbii-procid-ubl"

        # Scope 3
        scope3 = etree.SubElement(business_scope, "Scope")
        scope3_type = etree.SubElement(scope3, "Type")
        scope3_type.text = "Document_UUID"
        scope3_instance = etree.SubElement(scope3, "InstanceIdentifier")
        scope3_instance.text = transmission_uuid


    def generate_credit_ubl_xml_etree(self, version="2.1"):
        self.ensure_one()
        nsmap, ns = self._ubl_get_credit_nsmap_namespace("CreditNote-2", version=version)
        xml_root = etree.Element("CreditNote", nsmap=nsmap)
        self._ubl_credit_add_header(xml_root, ns, version=version)
        self._ubl_credit_add_supplier_party(
            False,
            self.company_id,
            "AccountingSupplierParty",
            xml_root,
            ns,
            version=version,
        )
        self._ubl_credit_add_customer_party(
            self.partner_id,
            False,
            "AccountingCustomerParty",
            xml_root,
            ns,
            version=version,
        )
        if self.invoice_payment_term_id:
            self._ubl_add_payment_terms(
                self.invoice_payment_term_id, xml_root, ns, version=version
            )
        self._ubl_add_tax_total(xml_root, ns, version=version)
        self._ubl_credit_add_legal_monetary_total(xml_root, ns, version=version)

        line_number = 0
        for iline in self.invoice_line_ids:
            line_number += 1
            self._ubl_add_creditnote_line(
                    xml_root, iline, line_number, ns, version=version
                )
        return xml_root

    @api.model
    def _ubl_credit_add_customer_party(
            self, partner, company, node_name, parent_node, ns, version="2.1"
    ):
        if company:
            if partner:
                assert (
                        partner.commercial_partner_id == company.partner_id
                ), "partner is wrong"
            else:
                partner = company.partner_id
        supplier_party_root = etree.SubElement(parent_node, ns["cac"] + node_name)
        if not company and partner.commercial_partner_id.ref:
            supplier_ref = etree.SubElement(
                supplier_party_root, ns["cbc"] + "CustomerAssignedAccountID"
            )
            supplier_ref.text = partner.commercial_partner_id.ref
        self._ubl_credit_customer_add_party(
            partner, company, "Party", supplier_party_root, ns, version=version
        )

    @api.model
    def _ubl_credit_add_supplier_party(
            self, partner, company, node_name, parent_node, ns, version="2.1"
    ):
        if company:
            if partner:
                assert (
                        partner.commercial_partner_id == company.partner_id
                ), "partner is wrong"
            else:
                partner = company.partner_id
        supplier_party_root = etree.SubElement(parent_node, ns["cac"] + node_name)
        if not company and partner.commercial_partner_id.ref:
            supplier_ref = etree.SubElement(
                supplier_party_root, ns["cbc"] + "CustomerAssignedAccountID"
            )
            supplier_ref.text = partner.commercial_partner_id.ref
        self._ubl_credit_add_party(
            partner, company, "Party", supplier_party_root, ns, version=version
        )

    @api.model
    def _ubl_credit_add_party(
            self, partner, company, node_name, parent_node, ns, version="2.1"
    ):
        commercial_partner = partner.commercial_partner_id
        party = etree.SubElement(parent_node, ns["cac"] + node_name)
        endpoint = etree.SubElement(party, ns["cbc"] + "EndpointID", schemeID='0195' or '')
        endpoint.text = commercial_partner.peppol_identifier or ''
        if commercial_partner.seller_identifier:
            party_name = etree.SubElement(party, ns["cac"] + "PartyIdentification")
            name = etree.SubElement(party_name, ns["cbc"] + "ID", schemeID='0195' or '')
            name.text = commercial_partner.seller_identifier
        else:
            party_name = etree.SubElement(party, ns["cac"] + "PartyIdentification")
            name = etree.SubElement(party_name, ns["cbc"] + "ID", schemeID='0195')
            name.text = commercial_partner.name
        self._ubl_credit_add_address(
            commercial_partner, "PostalAddress", party, ns, version=version
        )
        self._ubl_add_party_tax_scheme(commercial_partner, party, ns, version=version)
        if company or partner:
            self._ubl_add_party_legal_entity(
                commercial_partner, party, ns, version="2.1"
            )
        # self._ubl_credit_add_contact(partner, party, ns, version=version)

    @api.model
    def _ubl_credit_customer_add_party(
            self, partner, company, node_name, parent_node, ns, version="2.1"
    ):
        commercial_partner = partner.commercial_partner_id
        party = etree.SubElement(parent_node, ns["cac"] + node_name)
        endpoint = etree.SubElement(party, ns["cbc"] + "EndpointID", schemeID=commercial_partner.peppol_scheme or '')
        endpoint.text = commercial_partner.peppol_identifier or ''
        self._ubl_credit_add_address(
            commercial_partner, "PostalAddress", party, ns, version=version
        )
        self._ubl_add_party_tax_scheme(commercial_partner, party, ns, version=version)
        if company or partner:
            self._ubl_add_party_legal_entity(
                commercial_partner, party, ns, version="2.1"
            )
        # self._ubl_credit_customer_add_contact(partner, party, ns, version=version) #TODO:


    @api.model
    def _ubl_credit_add_contact(
            self, partner, parent_node, ns, node_name="Contact", version="2.1"
    ):
        contact = etree.SubElement(parent_node, ns["cac"] + node_name)
        contact_id_text = self._ubl_get_contact_id(partner)
        if contact_id_text:
            contact_id = etree.SubElement(contact, ns["cbc"] + "ID")
            contact_id.text = contact_id_text
        contact_name = etree.SubElement(contact, ns["cbc"] + "Name")
        contact_name.text = partner.name

    @api.model
    def _ubl_credit_customer_add_contact(
            self, partner, parent_node, ns, node_name="Contact", version="2.1"
    ):
        contact = etree.SubElement(parent_node, ns["cac"] + node_name)
        contact_id_text = self._ubl_get_contact_id(partner)
        email = partner.email or partner.commercial_partner_id.email
        if email:
            electronicmail = etree.SubElement(contact, ns["cbc"] + "ElectronicMail")
            electronicmail.text = email

    @api.model
    def _ubl_credit_add_address(self, partner, node_name, parent_node, ns, version="2.1"):
        address = etree.SubElement(parent_node, ns["cac"] + node_name)
        if partner.street:
            streetname = etree.SubElement(address, ns["cbc"] + "StreetName")
            streetname.text = partner.street
            print("streetname.text",streetname.text)
        if partner.street2:
            addstreetname = etree.SubElement(
                address, ns["cbc"] + "AdditionalStreetName"
            )
            addstreetname.text = partner.street2
        if partner.city:
            city = etree.SubElement(address, ns["cbc"] + "CityName")
            city.text = partner.city
        if partner.zip:
            zip_code = etree.SubElement(address, ns["cbc"] + "PostalZone")
            zip_code.text = partner.zip
        if partner.state_id:
            state = etree.SubElement(address, ns["cbc"] + "CountrySubentity")
            state.text = partner.state_id.name
        if partner.country_id:
            self._ubl_add_country(partner.country_id, address, ns, version=version)
        else:
            logger.warning("UBL: missing country on partner %s", partner.name)

    @api.model
    def _ubl_credit_add_header(self, parent_node, ns, version="2.1"):
        self.ensure_one()
        ubl_version = etree.SubElement(parent_node, ns["cbc"] + "UBLVersionID")
        ubl_version.text = version
        ubl_customization_id = etree.SubElement(parent_node, ns["cbc"] + "CustomizationID")
        ubl_customization_id.text = "urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:sg:3.0"
        ubl_profile_id = etree.SubElement(parent_node, ns["cbc"] + "ProfileID")
        ubl_profile_id.text = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"
        doc_id = etree.SubElement(parent_node, ns["cbc"] + "ID")
        doc_id.text = self.name
        random_uuid = uuid.uuid4()
        uuid_var = etree.SubElement(parent_node, ns["cbc"] + "UUID")
        uuid_var.text = str(random_uuid)
        issue_date = etree.SubElement(parent_node, ns["cbc"] + "IssueDate")
        issue_date.text = self.invoice_date.strftime("%Y-%m-%d")
        type_code = etree.SubElement(parent_node, ns["cbc"] + "CreditNoteTypeCode")
        type_code.text = "381"
        if self.narration:
            note = etree.SubElement(parent_node, ns["cbc"] + "Note")
            note.text = self.narration
        doc_currency = etree.SubElement(parent_node, ns["cbc"] + "DocumentCurrencyCode")
        doc_currency.text = self.currency_id.name
        if self.ref:
            buyer_reference = etree.SubElement(parent_node, ns["cbc"] + "BuyerReference")
            buyer_reference.text = self.ref
        elif self.invoice_user_id:
            buyer_reference = etree.SubElement(parent_node, ns["cbc"] + "BuyerReference") #TODO::
            buyer_reference.text = self.invoice_user_id.name

    @api.model
    def _ubl_get_credit_nsmap_namespace(self, doc_name, version="2.1"):
        """ Overidden method from base_ubl module. """
        nsmap = {
            None: "urn:oasis:names:specification:ubl:schema:xsd:" + doc_name,
            "cac": "urn:oasis:names:specification:ubl:"
                   "schema:xsd:CommonAggregateComponents-2",
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:"
                   "CommonBasicComponents-2",
        }
        ns = {
            "cac": "{urn:oasis:names:specification:ubl:schema:xsd:"
                   "CommonAggregateComponents-2}",
            "cbc": "{urn:oasis:names:specification:ubl:schema:xsd:"
                   "CommonBasicComponents-2}",
        }
        return nsmap, ns

    def _ubl_credit_add_legal_monetary_total(self, parent_node, ns, version="2.1"):
        self.ensure_one()
        monetary_total = etree.SubElement(parent_node, ns["cac"] + "LegalMonetaryTotal")
        cur_name = self.currency_id.name
        prec = self.currency_id.decimal_places
        line_total = etree.SubElement(
            monetary_total, ns["cbc"] + "LineExtensionAmount", currencyID=cur_name
        )
        line_total.text = "%0.*f" % (prec, self.amount_untaxed)
        tax_excl_total = etree.SubElement(
            monetary_total, ns["cbc"] + "TaxExclusiveAmount", currencyID=cur_name
        )
        tax_excl_total.text = "%0.*f" % (prec, self.amount_untaxed)
        tax_incl_total = etree.SubElement(
            monetary_total, ns["cbc"] + "TaxInclusiveAmount", currencyID=cur_name
        )
        tax_incl_total.text = "%0.*f" % (prec, self.amount_total)
        # NOTE:: Commented below 'prepaid_amount' because Storecove mentioned: invoice.prepaidAmount and invoice.payableRoundingAmount are not acceptable
        payable_amount = etree.SubElement(
            monetary_total, ns["cbc"] + "PayableAmount", currencyID=cur_name
        )
        payable_amount.text = "%0.*f" % (prec, self.amount_residual)

    def _ubl_add_creditnote_line(self, parent_node, iline, line_number, ns, version="2.1"):
        self.ensure_one()
        cur_name = self.currency_id.name
        line_root = etree.SubElement(parent_node, ns["cac"] + "CreditNoteLine")
        dpo = self.env["decimal.precision"]
        qty_precision = dpo.precision_get("Product Unit of Measure")
        price_precision = dpo.precision_get("Product Price")
        account_precision = self.currency_id.decimal_places
        line_id = etree.SubElement(line_root, ns["cbc"] + "ID")
        line_id.text = str(line_number)
        uom_unece_code = False
        # product_uom_id is not a required field on account.move.line
        if iline.product_uom_id.unece_code:
            uom_unece_code = iline.product_uom_id.unece_code
            quantity = etree.SubElement(
                line_root, ns["cbc"] + "CreditedQuantity", unitCode=uom_unece_code
            )
        else:
            quantity = etree.SubElement(line_root, ns["cbc"] + "CreditedQuantity")
        qty = iline.quantity
        quantity.text = "%0.*f" % (qty_precision, qty)
        line_amount = etree.SubElement(
            line_root, ns["cbc"] + "LineExtensionAmount", currencyID=cur_name
        )
        line_amount.text = "%0.*f" % (account_precision, iline.price_subtotal)
        self._ubl_add_item(
            iline.name, iline.product_id, line_root, ns, iline, type_="sale", version=version
        )
        price_node = etree.SubElement(line_root, ns["cac"] + "Price")
        price_amount = etree.SubElement(
            price_node, ns["cbc"] + "PriceAmount", currencyID=cur_name
        )
        # price_unit = 0.0
        # Use price_subtotal/qty to compute price_unit to be sure
        # to get a *tax_excluded* price unit
        # if not float_is_zero(qty, precision_digits=qty_precision):
        #     price_unit = float_round(
        #         iline.price_subtotal / float(qty), precision_digits=price_precision
        #     )
        price_unit = iline.price_unit
        price_amount.text = "%0.*f" % (price_precision, price_unit)
        # if uom_unece_code:
        #     base_qty = etree.SubElement(
        #         price_node, ns["cbc"] + "BaseQuantity", unitCode=uom_unece_code
        #     )
        # else:
        #     base_qty = etree.SubElement(price_node, ns["cbc"] + "BaseQuantity")
        # base_qty.text = "%0.*f" % (qty_precision, 1.0)

    @api.model
    def _peppol_document_name_4type(self, plural=False):
        if plural:
            return _("Invoices")
        return _("Invoice")

    # def action_send_via_peppol(self):
    #     self.ensure_one()
    #     Queue = self.env['peppol.queue.out']
    #     queue_ref = Queue._add_to_queue(self)
    #     self.write({'outgoing_inv_doc_ref': queue_ref.id})
    #
    #     return {
    #         'name': self.sudo().env.ref('metro_einvoice_datapost.peppol_queue_out_action').name,
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'tree,form',
    #         'view_type': 'form',
    #         'res_model': 'peppol.queue.out',
    #         'domain': [('id','=',queue_ref.id)]
    #     }

    def check_nongst_to_peppol(self):
        self.ensure_one()
        if not self.company_id.partner_id.is_peppol_participant and self.partner_id.is_peppol_participant:
            if self.amount_tax and self.move_type == 'out_invoice':
                raise ValidationError("GST should not be charged as UEN '%s' is not GST-registered." % (self.company_id.partner_id.l10n_sg_unique_entity_number))

    # prakash
    def verify_partner_peppol_identifier(self, partner):
        params = self.env['ir.config_parameter'].sudo()
        peppol_endpoint = params.get_param('peppol_endpoint', default=False)
        token = params.get_param('peppol_apikey', default=False)
        electronic_address_scheme = params.get_param('electronic_address_scheme', default="0195")
        url = "{}private/api/search/exist?pid=iso6523-actorid-upis::{}:{}".format(peppol_endpoint,
                                                                                  electronic_address_scheme,
                                                                                  partner.peppol_identifier or '')
        headers = {'Content-type': 'application/json;charset=UTF-8', 'Authorization': 'Bearer {}'.format(token)}
        response = requests.get(url, headers=headers)
        params = self.env['ir.config_parameter'].sudo()
        is_true = params.get_param('is_peppol', default=0)
        print('\n\n\nis_true', is_true, response.status_code)
        if response.status_code in [200, 204] or is_true == "1":
            partner.write({'is_peppol_participant': True})
            return True
        else:
            if not self.env.user.has_group("metro_einvoice_datapost.group_c5_submitter"):
                raise ValidationError("Partner %s is not a Peppol participant, Responded with Status Code as %s" % (
                    partner.name, response.status_code))
            return False
        # else:


    # prakash
    def action_send_via_peppol(self): # Prakash comment
        self.ensure_one()
        # company partner detail check
        company_partner = self.company_id.partner_id
        if not company_partner.l10n_sg_unique_entity_number:
            raise ValidationError('UEN no is not defined to the Partner: ' + str(company_partner.name))
        if not company_partner.peppol_scheme:
            raise ValidationError("The Peppol Scheme cannot be empty for the Partner: " + str(company_partner.name))
        if company_partner.peppol_identifier:
            is_company_peppol_participant = self.verify_partner_peppol_identifier(company_partner)

        # partner detail check when peppol..

        if self.env.user.has_group("metro_einvoice_datapost.group_peppol_submitter"):
            partner = self.partner_id
            # Check UEN on partner first, else fallback to parent
            uen = partner.l10n_sg_unique_entity_number or partner.parent_id.l10n_sg_unique_entity_number
            if not uen:
                raise ValidationError(
                    'UEN no is not defined for the Partner: %s' % (partner.name or partner.parent_id.name)
                )

        # customer detail check with child
        if self.partner_id.l10n_sg_unique_entity_number:
            is_peppol_participant = self.verify_partner_peppol_identifier(self.partner_id)
            print('\nis_peppol_participant11', is_peppol_participant)
            partner_obj = self.partner_id
            # is_peppol_participant = self.partner_id.is_peppol_participant
        elif self.partner_id.parent_id.l10n_sg_unique_entity_number:
            is_peppol_participant = self.verify_partner_peppol_identifier(self.partner_id.parent_id)
            print('\nis_peppol_participant222', is_peppol_participant)

            partner_obj = self.partner_id.parent_id
            # is_peppol_participant = self.partner_id.parent_id.is_peppol_participant
        else:
            b2c_invoice = self._create_b2c_outgoing_invoice()
            print('\nb2c_invoice', b2c_invoice)
            self.b2c_outgoing_inv_doc_ref = b2c_invoice.id
            return {
                'name': self.sudo().env.ref('metro_einvoice_datapost.action_b2c_outgoing_invoices').name,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': b2c_invoice.id,
                'res_model': 'b2c.outgoing.invoices',
            }
            # raise ValidationError('UEN no is not defined to the Partner: ' + str(self.partner_id.name))

        # peppol identifier base check document type of (PINT or BIS)
        partner = self.partner_id
        print('\npartner', partner)
        if not partner.peppol_identifier:
            partner = partner.parent_id
        print('\npartner', self.business_unit_id, partner.is_sg_government_customer)
        if not self.business_unit_id  and partner.is_sg_government_customer:
            raise ValidationError('Business Unit is not defined')
        if not partner.peppol_identifier:
            raise ValidationError('Peppol Identifier no is not defined to the Partner: ' + str(partner.name))
        elif not partner.peppol_scheme:
            raise ValidationError('Peppol Scheme no is not defined to the Partner: ' + str(partner.name))
        else:
            if partner.peppol_scheme and partner.peppol_identifier:
                url = "https://directory.peppol.eu/search/1.0/json?participant=iso6523-actorid-upis::{}:{}".format(
                    partner.peppol_scheme,
                    partner.peppol_identifier)
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    matches = data.get("matches", [])
                    if matches:
                        match = matches[0]
                        doc_types = match.get("docTypes", [])
                        if doc_types:
                            has_pint = any('urn:peppol:pint:' in d['value'].lower() for d in doc_types)
                            has_bis = any('urn:cen.eu:en16931' in d['value'].lower() for d in doc_types)
                            print('\nhas_pint', has_pint, has_bis)
                            if has_pint:
                                partner.peppol_document_type = 'PINT'
                            elif has_bis:
                                partner.peppol_document_type = 'BIS'
                            else:
                                partner.peppol_document_type = False
                                raise ValidationError(
                                    _("No valid PEPPOL document type (PINT or BIS) was found for the participant identifier: %s")
                                    % (partner.peppol_identifier)
                                )
                    else:
                        partner.peppol_document_type = 'PINT'
                        # raise ValidationError(
                        #     _("No valid PEPPOL document type (PINT or BIS) was found for the participant identifier: %s")
                        #     % (partner.peppol_identifier)
                        # )
        if not company_partner.zip:
            raise UserError(_("Missing Postal Code for supplier '%s'" % company_partner.name))
        if not partner.zip:
            raise UserError(_("Missing Postal Code for customer '%s'" % partner.name))
        # unit and unit code check
        for iline in self.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_section', 'line_note')):
            if not iline.product_id and self.env.user.has_group("metro_einvoice_datapost.group_peppol_submitter"):
                raise ValidationError("Product is not defined for the Invoice line.")
            elif not iline.product_uom_id:
                raise ValidationError("'Unit of Measure(UOM)' is not defined for the Invoice line.")
            elif not iline.product_uom_id.unece_code:
                raise ValidationError("'UNECE Code' is not defined for the UOM: " + str(iline.product_uom_id.name))
        # tax check for company
        if self.env.user.has_group("metro_einvoice_datapost.group_c5_submitter") and self.amount_tax > 0:
            if not company_partner.vat:
                raise UserError(_("Missing GST No for supplier '%s'" % company_partner.name))
            company_partner.check_gst_register(company_partner)
            if is_company_peppol_participant and company_partner.registration_status == 'unregistered' and is_peppol_participant:
                raise UserError(_("GST should not be charged as '%s' is not GST-registered " % company_partner.vat))
        # Taxes UNECE Tax Category check
        if self.env.user.has_group("metro_einvoice_datapost.group_c5_submitter"): # oct-13 made changes
            tax_objs = self.line_ids.mapped('tax_ids')
            if self.move_type in ['out_invoice','out_refund']: #prakash_17feb26
                if not tax_objs:
                    raise UserError(_("Missing taxes for this Invoice/Credit Note."))
                for tax in tax_objs:
                    if not tax.unece_categ_id:
                        raise UserError(_("Missing UNECE Tax Category on tax '%s'" % tax.name))
        if not self.narration and self.move_type in ['out_refund', 'in_refund']:
            raise UserError(_("Missing Note for this Credit Note."))

        # self.check_nongst_to_peppol()
        action_mapping = {
            ('out_invoice', True): 'metro_einvoice_datapost.peppol_queue_out_action',
            ('out_refund', True): 'metro_einvoice_datapost.peppol_queue_out_action',
            ('in_invoice', True): 'metro_einvoice_datapost.peppol_queue_c5_out_action',
            ('in_refund', True): 'metro_einvoice_datapost.peppol_queue_c5_out_action',
            ('out_invoice', False): 'metro_einvoice_datapost.peppol_sales_invoice_queue_c5_action',
            ('out_refund', False): 'metro_einvoice_datapost.peppol_sales_invoice_queue_c5_action',
            ('in_invoice', False): 'metro_einvoice_datapost.peppol_queue_out_action',
            ('in_refund', False): 'metro_einvoice_datapost.peppol_queue_out_action'

            # ('in_invoice', True): 'metro_einvoice_datapost.peppol_queue_c5_out_action',
            # ('in_refund', True): 'metro_einvoice_datapost.peppol_credit_queue_c5_out_action',
            # ('out_invoice', False): 'metro_einvoice_datapost.peppol_sales_invoice_queue_c5_action',
            # ('out_refund', False): 'metro_einvoice_datapost.peppol_sales_creditnote_queue_c5_action',
            # ('in_invoice', False): 'metro_einvoice_datapost.non_peppol_queue_c5_purchase_inv_action',
            # ('in_refund', False): 'metro_einvoice_datapost.non_peppol_queue_c5_purchase_credit_action'
        }
        queue_ref = False
        queue_data = {'invoice_type': self.move_type, 'invoice_id': self.id, 'peppol_document_type': partner.peppol_document_type}
        if is_peppol_participant:
            if self.move_type in ['out_invoice', 'out_refund']:
                Queue = self.env['peppol.queue.out']
                queue_ref = Queue.create(queue_data)
                self.write({'outgoing_inv_doc_ref': queue_ref.id})
                res_model = 'peppol.queue.out'
            else:
                Queue = self.env['peppol.queue.c5.out']
                queue_ref = Queue.create(queue_data)
                self.write({'outgoing_inv_doc_ref_c5': queue_ref.id})
                res_model = 'peppol.queue.c5.out'
        else:
            Queue = self.env['peppol.queue.c5.out']
            queue_ref = Queue.create(queue_data)
            self.write({'outgoing_inv_doc_ref_c5': queue_ref.id})
            res_model = 'peppol.queue.c5.out'
        # else:
        #     raise ValidationError("Partner %s is not a Peppol participant!!" % (
        #         partner_obj.name))
        action_ref = action_mapping.get((self.move_type, is_peppol_participant))
        return {
            'name': self.sudo().env.ref(action_ref).name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': res_model,
            'domain': [('id', '=', queue_ref.id)]
        }

    def show_invoice_feature_popup(self):

        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Feature Restricted',
                'res_model': 'invoice.popup.wizard',
                'view_mode': 'form',
                'target': 'new',
            }

    def _peppol_action_manual_send(self):
        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user'):
            return self.show_invoice_feature_popup()
        moves = self.filtered(lambda doc: doc.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'))
        already_sent_moves = moves.filtered(lambda m: m.outgoing_inv_doc_ref or m.outgoing_inv_doc_ref_c5)
        if already_sent_moves:
            names = ', '.join(already_sent_moves.mapped('name'))
            raise UserError(_(
                "The following invoices/credit notes have already been sent:\n%s\n\n"
                "Please apply filters to choose the correct records."
            ) % names)
        if moves:
            # UNCOMMENT LATER
            # for move in moves:
            #     move.partner_id.verify_identifier_registered()
            # cus_peppol = moves.filtered(lambda doc: doc.partner_id.is_peppol_participant)
            # cus_nonpeppol = moves.filtered(lambda doc: doc.partner_id.is_peppol_participant != True)
            # default_is_both = bool(cus_peppol) and bool(cus_nonpeppol)
            # if not moves:
            #     action = self.sudo().env.ref('metro_einvoice_datapost.action_peppol_manual_nosend_wizard').read()[0]
            #     action.update({
            #         'name': 'Warning:',
            #         'context': {
            #             'default_message': 'You must not select these to perform this action.\n Note: Select only Sales Invoices.'
            #         }
            #     })
            #     return action
            document_count = len(moves.filtered(lambda l: l.state == 'posted'))
            if moves.pos_order_ids:
                message = 'Send %s Invoice to GST InvoiceNow' % document_count
                return {
                    'name': 'Send Payments',
                    'type': 'ir.actions.act_window',
                    'res_model': 'peppol.manual.send.payment.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'default_message': message, 'active_ids': moves.ids,
                                'active_model': 'account.move'},
                }
            else:
                action = self.sudo().env.ref('metro_einvoice_datapost.action_peppol_manual_send_wizard').read()[
                    0] if document_count >= 1 else \
                    self.sudo().env.ref('metro_einvoice_datapost.action_peppol_warning_wizard').read()[0]
                document_name_plural = self._peppol_document_name_4type(plural=True if len(moves) > 1 else False)
                wiz_name = _("Send %s via PEPPOL") % document_name_plural if document_count >= 1 else _("Warning:")
                peppol_invoices = moves.filtered(lambda inv: inv.partner_id.is_peppol_participant and inv.state == 'posted')
                non_peppol_invoices = moves.filtered(
                    lambda inv: not inv.partner_id.is_peppol_participant and inv.state == 'posted')
                default_is_both = bool(peppol_invoices and non_peppol_invoices)
                cus_peppol = bool(peppol_invoices and not non_peppol_invoices)
                move_type = list(set(moves.mapped('move_type')))

                # for documents in self:
                #     document_count = len(self.filtered(lambda l: l.state == 'posted'))
                #     action = self.sudo().env.ref('metro_einvoice_datapost.action_peppol_manual_send_wizard').read()[0] if document_count >= 1 else self.sudo().env.ref('metro_einvoice_datapost.action_peppol_warning_wizard').read()[0]
                #     document_name_plural = documents._peppol_document_name_4type(plural=True if len(documents) > 1 else False)
                #     wiz_name = _("Send %s via PEPPOL") % document_name_plural if document_count >= 1 else _("Warning:")
                group_c5 = self.env.user.has_group("metro_einvoice_datapost.group_c5_submitter")
                group_peppol = self.env.user.has_group("metro_einvoice_datapost.group_peppol_submitter")

                if document_count >= 1 and group_c5:
                    if default_is_both:
                        message = _("Send %s %s to PEPPOL or NON-PEPPOL.") % (document_count, document_name_plural)
                    else:
                        peppol_type = "PEPPOL" if cus_peppol else "NON-PEPPOL"
                        message = _("Send %s %s to %s.") % (document_count, document_name_plural, peppol_type)
                elif document_count >= 1 and group_peppol:
                    if non_peppol_invoices:
                        raise UserError(_("Please send only Peppol Invoice."))
                    else:
                        peppol_type = "PEPPOL"
                        message = _("Send %s %s to %s.") % (document_count, document_name_plural, peppol_type)
                else:
                    message = _("Only 'Posted' Invoices can be sent")
                context = dict(self.env.context or {})
                context.update({'default_message': message})
                if move_type:
                    context.update({
                        'default_move_type': move_type,
                    })
                if default_is_both and self.env.user.has_group("metro_einvoice_datapost.group_c5_submitter"):
                    context.update({
                        'default_peppol_invoices': peppol_invoices.ids,
                        'default_nonpeppol_invoices': non_peppol_invoices.ids,
                        'default_is_both': default_is_both,
                    })
                elif cus_peppol:
                    context.update({'default_peppol_invoices': peppol_invoices.ids})
                else:
                    context.update({'default_nonpeppol_invoices': non_peppol_invoices.ids})
                action.update({
                    'name': wiz_name,
                    'context': context,
                })
                return action
        else:
            spend_money_inv = self.filtered(lambda doc: doc.move_type in ('entry'))
            already_sent_moves = spend_money_inv.filtered(lambda m: m.pcp_outgoing_inv_doc_ref)
            if already_sent_moves:
                names = ', '.join(already_sent_moves.mapped('name'))
                raise UserError(_(
                    "The following Spend Money have already been sent:\n%s\n\n"
                    "Please apply filters to choose the correct records."
                ) % names)
            message = 'Send %s Spend Money to GST InvoiceNow' % len(spend_money_inv)
            return {
                'name': 'Send Payments',
                'type': 'ir.actions.act_window',
                'res_model': 'peppol.manual.send.payment.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_message': message, 'active_ids': spend_money_inv.ids,
                            'active_model': 'account.move'},
            }

        # if cus_peppol and not default_is_both:
        #     context = {
        #         'default_message': message,
        #         'active_ids': cus_peppol.ids,
        #         'default_is_both': default_is_both,
        #         'is_peppol': True
        #         }
        # elif cus_nonpeppol and not default_is_both:
        #     context = {
        #         'default_message': message,
        #         'active_ids': cus_nonpeppol.ids,
        #         'default_is_both': default_is_both,
        #         'is_nonpeppol': True,
        #         }
        # elif default_is_both:
        #     context = {
        #         'default_message': message,
        #         'cus_peppol_inv': cus_peppol.ids,
        #         'cus_nonpeppol_inv': cus_nonpeppol.ids,
        #         'default_is_both': default_is_both,
        #     }
        # if moves and moves.filtered(lambda doc: doc.move_type == 'out_refund'):
        #     context.update({"default_is_sale_credit": True})
        # action.update({
        #     'name': wiz_name,
        #     'context': context,
        # })
        # return action

    def map_to_incoming_invoice(self):
        ctx = self._context
        self.ensure_one()
        if ctx.get('active_model') == 'peppol.queue.in':
            queue_obj = self.env['peppol.queue.in'].browse(ctx['active_id'])
            if not self.partner_id.peppol_identifier:
                raise ValidationError("Peppol Identifier for Customer %s is not defined." % (self.partner_id.name))
            sender_peppol_id = queue_obj.extracted_senderid.split(":")[1]
            if self.partner_id.peppol_identifier.lower() != sender_peppol_id.lower():
                raise ValidationError("Customer's Peppol identifier does not match. Mapping cannot be allowed.")
            mapped_orderlines = []
            for line in queue_obj.invoice_line_ids:
                print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>peppol.queue.in-line",line.name,line.tax_percentage)
                for orderline in self.invoice_line_ids:
                    if line.quantity == orderline.quantity and line.price_amount == orderline.price_unit and line.id not in mapped_orderlines:
                        mapped_orderlines.append(orderline.id)
            if len(mapped_orderlines) != len(queue_obj.invoice_line_ids.ids):
                print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>mapped_orderlines",mapped_orderlines)
                print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>len(mapped_orderlines)",len(mapped_orderlines))
                print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>len(queue_obj.invoice_line_ids.ids)",len(queue_obj.invoice_line_ids.ids))
                raise ValidationError("The Order lines does not match. Mapping cannot be allowed.")                 
            if self.amount_untaxed != queue_obj.amt_untaxed:
                raise ValidationError("The Total Untaxed Amount does not match. Mapping cannot be allowed.")
            if self.amount_total != queue_obj.amt_including_tax:
                raise ValidationError("The Total Amount does not match. Mapping cannot be allowed.")
            queue_obj.write({
                'po_id': self.id,
                'state': 'success',
                'message': 'Invoice Bill mapped Successfully!',
            })
            return {
                'type': 'ir.actions.act_url',
                'url': "/web#id=" + str(queue_obj.id) + "&action=" + str(self.env.ref(
                    'metro_einvoice_datapost.action_pepppol_log_sg_view2').id) + "&model=peppol.queue.in&view_type=form&cids=&menu_id=" + str(
                    self.env.ref('metro_einvoice_datapost.menu_sub_peppol_log2').id)
            }

    # C5 BUlk invoice and credit note for both sale and purchase.
    def generate_c5_bulk_invoice_ubl_xml_etree(self, version="2.1", transmission_uuid=None):
        self.ensure_one()
        assert self.state == "posted"
        assert self.move_type in ("out_invoice", "in_invoice")
        logger.debug("Starting to generate UBL XML Invoice file")
        #####

        nsmap, ns = self._c5_bulk_ubl_get_nsmap_namespace("Invoice-2")
        print('\n\n\n\nnsmap', nsmap, '\n\n\nns', ns)
        invoice_root = etree.Element("Invoice", nsmap=nsmap)
        self._ubl_c5_add_header(invoice_root, ns, version=version, transmission_uuid=transmission_uuid)
        self._ubl_c5_add_order_reference(invoice_root, ns, version=version)
        
        if self.move_type == 'out_invoice':
            self._ubl_c5_add_supplier_party(
                False,
                self.company_id,
                "AccountingSupplierParty",
                invoice_root,
                ns,
                version=version,
            )
            self._ubl_c5_add_customer_party(
                self.partner_id,
                False,
                "AccountingCustomerParty",
                invoice_root,
                ns,
                version=version,
            )
        else:
            self._ubl_c5_add_supplier_party(
                self.partner_id,
                False,
                "AccountingSupplierParty",
                invoice_root,
                ns,
                version=version,
            )
            self._ubl_c5_add_customer_party(
                False,
                self.company_id,
                "AccountingCustomerParty",
                invoice_root,
                ns,
                version=version,
            )
        # if self.invoice_payment_term_id:
        #     self._ubl_add_payment_terms(
        #         self.invoice_payment_term_id, invoice_root, ns, version=version
        #     )
        self._ubl_c5_add_tax_total(invoice_root, ns, version=version)
        self._ubl_c5_add_legal_monetary_total(invoice_root, ns, version=version)

        line_number = 0
        for iline in self.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_section', 'line_note')):
            line_number += 1
            self._ubl_c5_add_invoice_line(
                invoice_root, iline, line_number, ns, version=version
            )
        return invoice_root

    @api.model
    def _c5_bulk_ubl_get_nsmap_namespace(self, doc_name, version="2.1"):
        """ Overidden method from base_ubl module. """
        if self.outgoing_inv_doc_ref_c5.invoice_ids:
            nsmap = {
                None: "urn:oasis:names:specification:ubl:schema:xsd:" + doc_name,
                "cac": "urn:oasis:names:specification:ubl:"
                       "schema:xsd:CommonAggregateComponents-2",
                "cbc": "urn:oasis:names:specification:ubl:"
                       "schema:xsd:CommonBasicComponents-2",
            }
        elif self.outgoing_inv_doc_ref_c5.invoice_id:
            nsmap = {
                None: "urn:oasis:names:specification:ubl:schema:xsd:" + doc_name,
                "cac": "urn:oasis:names:specification:ubl:"
                       "schema:xsd:CommonAggregateComponents-2",
                "cbc": "urn:oasis:names:specification:ubl:schema:xsd:"
                       "CommonBasicComponents-2",
                "ccts": "urn:un:unece:uncefact:documentation:2",
                "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
                "qdt": "urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2",
                "udt": "urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2",
                "xsd": "http://www.w3.org/2001/XMLSchema",
                "xsi": "http://www.w3.org/2001/XMLSchema-instance",
            }
        ns = {
            "cac": "{urn:oasis:names:specification:ubl:schema:xsd:"
                   "CommonAggregateComponents-2}",
            "cbc": "{urn:oasis:names:specification:ubl:schema:xsd:"
                   "CommonBasicComponents-2}",
        }
        print('\n\n\n\n\n\nnsmap111', nsmap, '\n\n\n\nns1111', ns)
        return nsmap, ns

    def _ubl_c5_add_order_reference(self, parent_node, ns, version="2.1"):
        self.ensure_one()
        if self.invoice_origin:
            if self.move_type in ("out_invoice", "out_refund"):
                sale_obj = self.env['sale.order'].sudo().search([('name','=',self.invoice_origin)], limit=1)
                if sale_obj and sale_obj.origin:
                    order_ref = etree.SubElement(parent_node, ns["cac"] + "OrderReference")
                    order_ref_id = etree.SubElement(order_ref, ns["cbc"] + "ID")
                    order_ref_id.text = sale_obj.origin
            elif self.move_type in ("in_invoice", "in_refund"):
                purchase_obj = self.env['purchase.order'].sudo().search([('name', '=', self.invoice_origin)], limit=1)
                if purchase_obj and purchase_obj.origin:
                    order_ref = etree.SubElement(parent_node, ns["cac"] + "OrderReference")
                    order_ref_id = etree.SubElement(order_ref, ns["cbc"] + "ID")
                    order_ref_id.text = purchase_obj.origin

    @api.model
    def _ubl_c5_add_supplier_party(
            self, partner, company, node_name, parent_node, ns, version="2.1"):
        if company:
            if partner:
                assert (
                        partner.commercial_partner_id == company.partner_id
                ), "partner is wrong"
            else:
                partner = company.partner_id
        supplier_party_root = etree.SubElement(parent_node, ns["cac"] + node_name)
        self._ubl_c5_add_party(
            partner, company, "Party", supplier_party_root, ns, version=version
        )

    @api.model
    def _ubl_c5_add_party(
            self, partner, company, node_name, parent_node, ns, version="2.1"):
        print('\npartnercompany', partner, company)
        if partner.l10n_sg_unique_entity_number:
            commercial_partner = partner
        else:
            commercial_partner = partner.commercial_partner_id
        print('\ncommercial_partner11111111111', commercial_partner)
        party = etree.SubElement(parent_node, ns["cac"] + node_name)
        endpoint = etree.SubElement(party, ns["cbc"] + "EndpointID", schemeID=commercial_partner.peppol_scheme or '')

        if company:
            endpoint.text = partner.commercial_partner_id.peppol_identifier or ''
        else:

            if commercial_partner.is_peppol_participant == False:
                uen = commercial_partner.l10n_sg_unique_entity_number
                endpoint.text = f"C5UID{uen}" if uen else "C5UID"
            else:
                endpoint.text = commercial_partner.peppol_identifier
        self._ubl_c5_add_address(
            commercial_partner, "PostalAddress", party, ns, version=version
        )
        if commercial_partner.vat:
            self._ubl_c5_add_party_tax_scheme(commercial_partner, party, ns, version=version)
        if company or partner:
            self._ubl_c5_add_party_legal_entity(
                commercial_partner, party, ns, version="2.1"
            )

    @api.model
    def _ubl_c5_add_address(self, partner, node_name, parent_node, ns, version="2.1"):
        address = etree.SubElement(parent_node, ns["cac"] + node_name)
        if partner.street:
            streetname = etree.SubElement(address, ns["cbc"] + "StreetName")
            streetname.text = partner.street
        if partner.street2:
            addstreetname = etree.SubElement(
                address, ns["cbc"] + "AdditionalStreetName"
            )
            addstreetname.text = partner.street2
        if partner.city:
            city = etree.SubElement(address, ns["cbc"] + "CityName")
            city.text = partner.city
        if partner.zip:
            zip_code = etree.SubElement(address, ns["cbc"] + "PostalZone")
            zip_code.text = partner.zip
        if partner.state_id:
            state = etree.SubElement(address, ns["cbc"] + "CountrySubentity")
            state.text = partner.state_id.name
        if self.outgoing_inv_doc_ref_c5.invoice_ids: #bulk  invoice only
            addressline = etree.SubElement(address, ns["cac"] + "AddressLine")
            addressline_line = etree.SubElement(addressline, ns["cbc"] + "Line")
            addressline_line.text = "Sales department"
        if partner.country_id:
            self._ubl_c5_add_country(partner.country_id, address, ns, version=version)
        else:
            logger.warning("UBL: missing country on partner %s", partner.name)

    @api.model
    def _ubl_c5_add_country(self, country, parent_node, ns, version="2.1"):
        country_root = etree.SubElement(parent_node, ns["cac"] + "Country")
        country_code = etree.SubElement(country_root, ns["cbc"] + "IdentificationCode")
        country_code.text = country.code

    @api.model
    def _ubl_c5_add_party_tax_scheme(self, commercial_partner, parent_node, ns, version="2.1"):
        print("\n_ubl_add_party_tax_scheme() >>>>")
        if commercial_partner.vat:
            party_tax_scheme = etree.SubElement(
                parent_node, ns["cac"] + "PartyTaxScheme"
            )
            company_id = etree.SubElement(party_tax_scheme, ns["cbc"] + "CompanyID")
            company_id.text = commercial_partner.vat
            tax_scheme_dict = {"id": "GST", "name": False, "type_code": False}
            self._ubl_c5_add_tax_scheme(
                tax_scheme_dict, party_tax_scheme, ns, version=version
            )

    @api.model
    def _ubl_c5_add_tax_scheme(self, tax_scheme_dict, parent_node, ns, version="2.1"):
        tax_scheme = etree.SubElement(parent_node, ns["cac"] + "TaxScheme")
        if tax_scheme_dict.get("id"):
            tax_scheme_id = etree.SubElement(
                tax_scheme, ns["cbc"] + "ID"
            )
            tax_scheme_id.text = tax_scheme_dict["id"]

    @api.model
    def _ubl_c5_add_party_legal_entity(self, commercial_partner, parent_node, ns, version="2.1"):
        party_legal_entity = etree.SubElement(
            parent_node, ns["cac"] + "PartyLegalEntity"
        )
        registration_name = etree.SubElement(
            party_legal_entity, ns["cbc"] + "RegistrationName"
        )
        registration_name.text = commercial_partner.name

        company_id = etree.SubElement(party_legal_entity, ns["cbc"] + "CompanyID",
                                      schemeID=commercial_partner.peppol_scheme or '')
        if not commercial_partner.l10n_sg_unique_entity_number:
            raise ValidationError("UEN of customer %s is not defined." % (commercial_partner.name))
        else:
            company_id.text = commercial_partner.l10n_sg_unique_entity_number

    @api.model
    def _ubl_c5_add_contact(self, partner, parent_node, ns, node_name="Contact", version="2.1"):
        contact = etree.SubElement(parent_node, ns["cac"] + node_name)
        contact_id_text = self._ubl_get_contact_id(partner)
        if contact_id_text:
            contact_id = etree.SubElement(contact, ns["cbc"] + "ID")
            contact_id.text = contact_id_text
        # if partner.parent_id:
        #     contact_name = etree.SubElement(contact, ns["cbc"] + "Name")
        #     contact_name.text = partner.name or partner.parent_id.name
        contact_name = etree.SubElement(contact, ns["cbc"] + "Name")
        contact_name.text = partner.name
        phone = partner.phone or partner.commercial_partner_id.phone
        if phone:
            telephone = etree.SubElement(contact, ns["cbc"] + "Telephone")
            telephone.text = phone
        email = partner.email or partner.commercial_partner_id.email
        if email:
            electronicmail = etree.SubElement(contact, ns["cbc"] + "ElectronicMail")
            electronicmail.text = email

    @api.model
    def _ubl_c5_add_customer_party(self, partner, company, node_name, parent_node, ns, version="2.1"):
        print("\n_ubl_add_customer_party() >>", partner, company)
        if company:
            if partner:
                assert (
                        partner.commercial_partner_id == company.partner_id
                ), "partner is wrong"
            else:
                partner = company.partner_id
        print("partner ==", partner)
        customer_party_root = etree.SubElement(parent_node, ns["cac"] + node_name)
        self._ubl_c5_add_party(
            partner, company, "Party", customer_party_root, ns, version=version
        )

    def _ubl_c5_add_tax_total(self, xml_root, ns, version="2.1"):
        self.ensure_one()
        cur_name = self.currency_id.name
        tax_total_node = etree.SubElement(xml_root, ns["cac"] + "TaxTotal")
        tax_amount_node = etree.SubElement(
            tax_total_node, ns["cbc"] + "TaxAmount", currencyID=cur_name
        )
        prec = self.currency_id.decimal_places
        tax_amount_node.text = "%0.*f" % (prec, self.amount_tax)
        added_tax_subtotal = False
        is_gst = False
        print('\n\n\n\n\nline_isdssssss', self.line_ids)
        tax_objs = self.line_ids.mapped('tax_ids')
        print("tax_objs ===",tax_objs)
        if tax_objs:
            is_gst = True
        # if self.move_type in ("out_invoice", "out_refund"):
        #     if any(tax.unece_categ_id and tax.unece_categ_id.code == 'SR' for tax in tax_objs):
        #         is_gst = True
        # else:
        #     if any(tax.unece_categ_id and tax.unece_categ_id.code == 'TX' for tax in tax_objs):
        #         is_gst = True
        if is_gst: #not float_is_zero(self.amount_tax, precision_digits=prec)
            tax_lines = self.line_ids.filtered(lambda line: line.tax_line_id)
            print("tax_lines>>",tax_lines)
            res = {}
            done_taxes = set()

            for line in self.invoice_line_ids:
                print('\n\n\n\n\nlineeee', line)
                # Loop through all taxes in Many2many field
                for tax in line.tax_ids:
                    print('\n\n\n\n\ntax<<<<', tax, tax.name)
                    tax_values = tax.compute_all(
                        line.price_unit * line.quantity,  # Line subtotal before tax
                        currency=self.currency_id,
                        quantity=1.0,  # Compute tax per unit
                        product=line.product_id,
                        partner=self.partner_id,
                    )
                    tax_categ = tax.unece_categ_id
                    res.setdefault(
                        tax_categ, {"base": 0.0, "amount": 0.0, "tax": False}
                    )
                    # Use correct computed tax amount
                    for computed_tax in tax_values['taxes']:
                        if computed_tax['id'] == tax.id:
                            res[tax_categ]["amount"] += computed_tax['amount']
                    # Unique key per tax per line
                    tax_key_add_base = (tax.id, line.id)

                    if tax_key_add_base not in done_taxes:
                        res[tax_categ]["base"] += tax_values["total_excluded"]
                        res[tax_categ]["tax"] = tax
                        done_taxes.add(tax_key_add_base)
                        
            # Sort by tax group sequence
            res = sorted(res.items(), key=lambda l: l[0].id)
            print("\nresssssss ===",res)
            print("\nadded_tax_subtotal>>", added_tax_subtotal)
            for _group, amounts in res:
                print('\n\n_group', _group)
                print('\n\namounts', amounts)
                self._ubl_c5_add_tax_subtotal(
                    amounts["base"],
                    amounts["amount"],
                    amounts["tax"],
                    cur_name,
                    tax_total_node,
                    ns,
                    version=version,
                )
                added_tax_subtotal = True
            if not added_tax_subtotal:
                self._ubl_c5_add_tax_subtotal(
                    0.0,
                    0.0,
                    tax_objs[0],
                    cur_name,
                    tax_total_node,
                    ns,
                    version=version,
                )
                added_tax_subtotal = True
        if not added_tax_subtotal:
            print("\nadded_tax_subtotal is FALSEEE")
            prec = self.env["decimal.precision"].precision_get("Account")
            tax_subtotal = etree.SubElement(tax_total_node, ns["cac"] + "TaxSubtotal")
            taxable_amount_node = etree.SubElement(
                tax_subtotal, ns["cbc"] + "TaxableAmount", currencyID=cur_name
            )
            taxable_amount_node.text = "%0.*f" % (prec, self.amount_total)
            tax_amount_node = etree.SubElement(
                tax_subtotal, ns["cbc"] + "TaxAmount", currencyID=cur_name
            )
            tax_amount_node.text = "0.00"
            self._ubl_c5_add_notax_category(False, tax_subtotal, ns, node_name="TaxCategory", version=version)

    def _ubl_c5_add_tax_subtotal(
            self,
            taxable_amount,
            tax_amount,
            tax,
            currency_code,
            parent_node,
            ns,
            version="2.1",
    ):
        """ Overidden method from base_ubl module. """
        prec = self.env["decimal.precision"].precision_get("Account")
        tax_subtotal = etree.SubElement(parent_node, ns["cac"] + "TaxSubtotal")
        if not float_is_zero(taxable_amount, precision_digits=prec):
            taxable_amount_node = etree.SubElement(
                tax_subtotal, ns["cbc"] + "TaxableAmount", currencyID=currency_code
            )
            taxable_amount_node.text = "%0.*f" % (prec, taxable_amount)
        tax_amount_node = etree.SubElement(
            tax_subtotal, ns["cbc"] + "TaxAmount", currencyID=currency_code
        )
        tax_amount_node.text = "%0.*f" % (prec, tax_amount)
        print('\n\n\n\n\ntax>>>>>>>>>', tax)
        self._ubl_c5_add_tax_category(tax, tax_subtotal, ns, node_name="TaxCategory", version=version)

    # Code Not used #prakash_17feb2026
    @api.model
    def _ubl_c5_add_notax_category_OLD(self, tax, parent_node, ns, node_name="ClassifiedTaxCategory", version="2.1"):
        print("Called _ubl_add_notax_category() >>>")
        if self.move_type in ("out_invoice", "out_refund"):
            unece_categ = self.env['unece.code.list'].sudo().search([('type', '=', 'tax_categ'), ('code', '=', 'NA')])
        else:
            unece_categ = self.env['unece.code.list'].sudo().search([('type','=','tax_categ'),('code','=','TXNA')])
        if not unece_categ:
            raise UserError(_("Missing UNECE Tax Category: '%s'" % unece_categ.code))
        classified_tax_categ_node = etree.SubElement(parent_node, ns["cac"] + node_name)
        unece_categ_code_node = etree.SubElement(classified_tax_categ_node, ns["cbc"] + "ID")
        unece_categ_code_node.text = unece_categ.code
        tax_percent_node = etree.SubElement(classified_tax_categ_node, ns["cbc"] + "Percent")
        tax_percent_node.text = "0"
        tax_scheme_node = etree.SubElement(classified_tax_categ_node, ns["cac"] + "TaxScheme")
        tax_scheme_id_node = etree.SubElement(tax_scheme_node, ns["cbc"] + "ID")
        tax_scheme_id_node.text = 'GST'

    #prakash_17feb2026
    @api.model
    def _ubl_c5_add_notax_category(self, tax, parent_node, ns, node_name="ClassifiedTaxCategory", version="2.1"):
        print("Called _ubl_add_notax_category() >>>")
        if self.move_type in ("out_invoice", "out_refund"):
            unece_categ = 'NA'
        else:
            unece_categ = 'TXNA'
        #if not unece_categ:
        #    raise UserError(_("Missing UNECE Tax Category: '%s'" % unece_categ.code))
        classified_tax_categ_node = etree.SubElement(parent_node, ns["cac"] + node_name)
        unece_categ_code_node = etree.SubElement(classified_tax_categ_node, ns["cbc"] + "ID")
        unece_categ_code_node.text = unece_categ
        tax_percent_node = etree.SubElement(classified_tax_categ_node, ns["cbc"] + "Percent")
        tax_percent_node.text = "0"
        tax_scheme_node = etree.SubElement(classified_tax_categ_node, ns["cac"] + "TaxScheme")
        tax_scheme_id_node = etree.SubElement(tax_scheme_node, ns["cbc"] + "ID")
        tax_scheme_id_node.text = 'GST'

    @api.model
    def _ubl_c5_add_tax_category(self, tax, parent_node, ns, node_name="ClassifiedTaxCategory", version="2.1"):
        """ Overidden method from base_ubl module. """
        print('\n\n\n\n\ntax', tax.unece_categ_id, tax)
        if not tax.unece_categ_id:
            raise UserError(_("Missing UNECE Tax Category on tax '%s'" % tax.name))
        classified_tax_categ_node = etree.SubElement(parent_node, ns["cac"] + node_name)
        unece_categ_code_node = etree.SubElement(classified_tax_categ_node, ns["cbc"] + "ID")
        unece_categ_code_node.text = tax.unece_categ_code
        tax_percent_node = etree.SubElement(classified_tax_categ_node, ns["cbc"] + "Percent")
        tax_percent_node.text = str(float_round(tax.amount, precision_digits=1))
        tax_scheme_node = etree.SubElement(classified_tax_categ_node, ns["cac"] + "TaxScheme")
        tax_scheme_id_node = etree.SubElement(tax_scheme_node, ns["cbc"] + "ID")
        tax_scheme_id_node.text = 'GST'

    def _ubl_c5_add_legal_monetary_total(self, parent_node, ns, version="2.1"):
        self.ensure_one()
        monetary_total = etree.SubElement(parent_node, ns["cac"] + "LegalMonetaryTotal")
        cur_name = self.currency_id.name
        prec = self.currency_id.decimal_places
        line_total = etree.SubElement(
            monetary_total, ns["cbc"] + "LineExtensionAmount", currencyID=cur_name
        )
        line_total.text = "%0.*f" % (prec, self.amount_untaxed)
        tax_excl_total = etree.SubElement(
            monetary_total, ns["cbc"] + "TaxExclusiveAmount", currencyID=cur_name
        )
        tax_excl_total.text = "%0.*f" % (prec, self.amount_untaxed)
        tax_incl_total = etree.SubElement(
            monetary_total, ns["cbc"] + "TaxInclusiveAmount", currencyID=cur_name
        )
        tax_incl_total.text = "%0.*f" % (prec, self.amount_total)

        charge_total = etree.SubElement(
            monetary_total, ns["cbc"] + "ChargeTotalAmount", currencyID=cur_name
        )
        charge_total.text = "%0.*f" % (prec, self.amount_total)

        prepaid_amount = etree.SubElement(
            monetary_total, ns["cbc"] + "PrepaidAmount", currencyID=cur_name
        )
        prepaid_value = self.amount_total - self.amount_residual
        prepaid_amount.text = "%0.*f" % (prec, prepaid_value)
        payable_amount = etree.SubElement(
            monetary_total, ns["cbc"] + "PayableAmount", currencyID=cur_name
        )
        payable_amount.text = "%0.*f" % (prec, self.amount_residual)

    def _ubl_c5_add_invoice_line(self, parent_node, iline, line_number, ns, version="2.1"):
        self.ensure_one()
        cur_name = self.currency_id.name
        line_root = etree.SubElement(parent_node, ns["cac"] + "InvoiceLine")
        dpo = self.env["decimal.precision"]
        qty_precision = dpo.precision_get("Product Unit of Measure")
        price_precision = dpo.precision_get("Product Price")
        account_precision = self.currency_id.decimal_places
        line_id = etree.SubElement(line_root, ns["cbc"] + "ID")
        line_id.text = str(line_number)
        uom_unece_code = False
        # product_uom_id is not a required field on account.move.line
        if not iline.product_uom_id.unece_code:
            raise ValidationError("Product UOM Unece Code for %s is not defined." % (iline.product_uom_id.name))
        else:
            uom_unece_code = iline.product_uom_id.unece_code
            quantity = etree.SubElement(
                line_root, ns["cbc"] + "InvoicedQuantity", unitCode=uom_unece_code
            )
        qty = iline.quantity
        quantity.text = "%0.*f" % (qty_precision, qty)
        line_amount = etree.SubElement(
            line_root, ns["cbc"] + "LineExtensionAmount", currencyID=cur_name
        )
        line_amount.text = "%0.*f" % (account_precision, iline.price_subtotal)
        # :: NOT REQUIRED ::
        # self._ubl_add_invoice_line_tax_total(iline, line_root, ns, version=version)
        #
        # :: NOT REQUIRED ::
        # self._ubl_add_invoice_line_tax_category(
        #     iline, line_root, ns, version=version
        # )
        # Adding the OrderLineReference
        self._ubl_c5_add_item(
            iline.name, iline.product_id, line_root, ns, iline, type_="sale", version=version
        )
        price_node = etree.SubElement(line_root, ns["cac"] + "Price")
        price_amount = etree.SubElement(
            price_node, ns["cbc"] + "PriceAmount", currencyID=cur_name
        )
        # price_unit = 0.0
        # Use price_subtotal/qty to compute price_unit to be sure
        # to get a *tax_excluded* price unit
        # if not float_is_zero(qty, precision_digits=qty_precision):
        #     price_unit = float_round(
        #         iline.price_subtotal / float(qty), precision_digits=price_precision
        #     )
        price_unit = iline.price_unit
        price_amount.text = "%0.*f" % (price_precision, price_unit)
        if uom_unece_code:
            base_qty = etree.SubElement(
                price_node, ns["cbc"] + "BaseQuantity", unitCode=uom_unece_code
            )
        else:
            base_qty = etree.SubElement(price_node, ns["cbc"] + "BaseQuantity")
        base_qty.text = "%0.*f" % (qty_precision, 1.0)
        # TODO :: Review :: My Custom Code
        #  if iline.discount != 0.0:
        #     self._ubl_add_invoice_line_allowance_charge(
        #         iline, line_root, ns, version=version
        #     )

    @api.model
    def _ubl_c5_add_item(
            self,
            name,
            product,
            parent_node,
            ns,
            iline,
            type_="purchase",
            seller=False,
            version="2.1"):
        """Beware that product may be False (in particular on invoices)"""
        assert type_ in ("sale", "purchase"), "Wrong type param"
        assert name, "name is a required arg"
        item = etree.SubElement(parent_node, ns["cac"] + "Item")
        product_name = False
        seller_code = False
        if product:
            if type_ == "purchase":
                if seller:
                    sellers = product._select_seller(
                        partner_id=seller, quantity=0.0, date=None, uom_id=False
                    )
                    if sellers:
                        product_name = sellers[0].product_name
                        seller_code = sellers[0].product_code
            if not seller_code:
                seller_code = product.default_code
            if not product_name:
                variant = ", ".join(product.attribute_line_ids.mapped("value_ids.name"))
                product_name = (
                        variant and "{} ({})".format(product.name, variant) or product.name
                )
        name_node = etree.SubElement(item, ns["cbc"] + "Name")
        name_node.text = product_name or name.split("\n")[0]
        if seller_code:
            seller_identification = etree.SubElement(
                item, ns["cac"] + "SellersItemIdentification"
            )
            seller_identification_id = etree.SubElement(
                seller_identification, ns["cbc"] + "ID"
            )
            seller_identification_id.text = seller_code
        if product:
            # I'm not 100% sure, but it seems that ClassifiedTaxCategory
            # contains the taxes of the product without taking into
            # account the fiscal position
            if type_ in ("sale", "purchase"):
                taxes = iline.tax_ids
                if taxes:
                    for tax in taxes:
                        print('\n\n\nline_tax', tax)
                        self._ubl_c5_add_tax_category(
                            tax,
                            item,
                            ns,
                            node_name="ClassifiedTaxCategory",
                            version=version,
                        )
                else:
                    self._ubl_c5_add_notax_category(
                        False,
                        item,
                        ns,
                        node_name="ClassifiedTaxCategory",
                        version=version,
                    )
    # credit bulk start
    def generate_c5_bulk_credit_ubl_xml_etree(self, version="2.1", transmission_uuid=None):
        self.ensure_one()
        assert self.state == "posted"
        assert self.move_type in ("out_refund", "in_refund")
        logger.debug("Starting to generate UBL XML Invoice file")
        #####
        nsmap, ns = self._c5_bulk_ubl_get_nsmap_namespace("CreditNote-2")
        invoice_root = etree.Element("CreditNote", nsmap=nsmap)
        self._ubl_c5_add_header(invoice_root, ns, version=version, transmission_uuid=transmission_uuid)
        self._ubl_c5_add_order_reference(invoice_root, ns, version=version)
        self._ubl_c5_credit_add_billing_reference(invoice_root, ns, version=version)
        if self.currency_id.id != self.company_id.currency_id.id:
            self._ubl_add_additional_documents(invoice_root, ns, version=version)
        if self.move_type == 'out_refund': #Sales Credit Note
            self._ubl_c5_credit_add_supplier_party(
                False,
                self.company_id,
                "AccountingSupplierParty",
                invoice_root,
                ns,
                version=version,
            )
            self._ubl_c5_credit_add_customer_party(
                self.partner_id,
                False,
                "AccountingCustomerParty",
                invoice_root,
                ns,
                version=version,
            )
        else: # Purchase Credit Note
            self._ubl_c5_credit_add_supplier_party(
                self.partner_id,
                False,
                "AccountingSupplierParty",
                invoice_root,
                ns,
                version=version,
            )
            self._ubl_c5_credit_add_customer_party(
                False,
                self.company_id,
                "AccountingCustomerParty",
                invoice_root,
                ns,
                version=version,
            )
        # if self.invoice_payment_term_id:
        #     self._ubl_add_payment_terms(
        #         self.invoice_payment_term_id, invoice_root, ns, version=version
        #     )
        self._ubl_c5_add_tax_total(invoice_root, ns, version=version)

        if self.currency_id.id != self.company_id.currency_id.id:
            self._ubl_add_tax_total_foreign_currency(invoice_root, ns, version=version)

        self._ubl_c5_add_legal_monetary_total(invoice_root, ns, version=version)

        line_number = 0
        for iline in self.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_section', 'line_note')):
            line_number += 1
            self._ubl_c5_add_creditnote_line(
                invoice_root, iline, line_number, ns, version=version
            )
        return invoice_root

    def _ubl_c5_add_header(self, parent_node, ns, version="2.1", transmission_uuid=None):
        self.ensure_one()
        if self.move_type in ("out_refund"):
            ubl_version = etree.SubElement(parent_node, ns["cbc"] + "UBLVersionID")
            ubl_version.text = version
        ubl_customization_id = etree.SubElement(parent_node, ns["cbc"] + "CustomizationID")
        ubl_profile_id = etree.SubElement(parent_node, ns["cbc"] + "ProfileID")
        if self.move_type in ("out_refund", "out_invoice"):
            ubl_customization_id.text = "urn:peppol:pint:billing-1@sg-1:LocalTaxInvoice:sg:1.0"
            ubl_profile_id.text = "urn:peppol:bis:billing"
        elif self.move_type in ("in_refund", "in_invoice"):
            ubl_customization_id.text = "urn:peppol:pint:billing-1@sg-1:LocalTaxInvoice:sg:1.0"
            ubl_profile_id.text = "urn:peppol:bis:Payables"
        doc_id = etree.SubElement(parent_node, ns["cbc"] + "ID")
        doc_id.text = self.name
        access_point = self.env['peppol.access.point.sg'].sudo().search([('company_id', '=', self.company_id.id)],
                                                                        order="create_date")
        # client_ref = access_point.get_uuid()
        doc_uuid = etree.SubElement(parent_node, ns["cbc"] + "UUID")
        doc_uuid.text = transmission_uuid
        issue_date = etree.SubElement(parent_node, ns["cbc"] + "IssueDate")
        issue_date.text = self.invoice_date.strftime("%Y-%m-%d")
        if self.move_type in ("out_invoice", "in_invoice"):
            due_date = etree.SubElement(parent_node, ns["cbc"] + "DueDate")
            due_date.text = self.invoice_date_due.strftime("%Y-%m-%d")
        if self.move_type in ("out_invoice", "in_invoice"):
            type_code = etree.SubElement(parent_node, ns["cbc"] + "InvoiceTypeCode")
            type_code.text = "380"
        elif self.move_type in ("out_refund", "in_refund"):
            type_code = etree.SubElement(parent_node, ns["cbc"] + "CreditNoteTypeCode")
            type_code.text = "381"
        if self.narration:
            note = etree.SubElement(parent_node, ns["cbc"] + "Note")
            note.text = self.narration
        doc_currency = etree.SubElement(parent_node, ns["cbc"] + "DocumentCurrencyCode")
        doc_currency.text = self.currency_id.name

        if self.currency_id.id != self.company_id.currency_id.id:
            logger.error("\n\nForegin currency......")
            tax_curr_code = etree.SubElement(parent_node, ns["cbc"] + "TaxCurrencyCode")
            tax_curr_code.text = self.company_id.currency_id.name

    def _ubl_c5_credit_add_billing_reference(self, parent_node, ns, version="2.1"):
        self.ensure_one()
        if self.reversed_entry_id:
            billing_ref = etree.SubElement(parent_node, ns["cac"] + "BillingReference")
            invoice_doc_ref = etree.SubElement(billing_ref, ns["cac"] + "InvoiceDocumentReference")
            invoice_ref_id = etree.SubElement(invoice_doc_ref, ns["cbc"] + "ID")
            invoice_ref_id.text = self.reversed_entry_id.name
            issue_date = etree.SubElement(invoice_doc_ref, ns["cbc"] + "IssueDate")
            issue_date.text = self.reversed_entry_id.invoice_date.strftime("%Y-%m-%d")

    @api.model
    def _ubl_c5_credit_add_supplier_party(
            self, partner, company, node_name, parent_node, ns, version="2.1"
    ):
        if company:
            if partner:
                assert (
                        partner.commercial_partner_id == company.partner_id
                ), "partner is wrong"
            else:
                partner = company.partner_id
        supplier_party_root = etree.SubElement(parent_node, ns["cac"] + node_name)
        self._ubl_c5_credit_add_party(
            partner, company, "Party", supplier_party_root, ns, version=version
        )

    @api.model
    def _ubl_c5_credit_add_party(
            self, partner, company, node_name, parent_node, ns, version="2.1"
    ):
        if partner.l10n_sg_unique_entity_number:
            commercial_partner = partner
        else:
            commercial_partner = partner.commercial_partner_id
        party = etree.SubElement(parent_node, ns["cac"] + node_name)
        endpoint = etree.SubElement(party, ns["cbc"] + "EndpointID", schemeID=commercial_partner.peppol_scheme or '')
        if company:
            endpoint.text = partner.commercial_partner_id.peppol_identifier or ''
        else:
            if commercial_partner.is_peppol_participant == False:
                uen = commercial_partner.l10n_sg_unique_entity_number
                endpoint.text = f"C5UID{uen}" if uen else "C5UID"
            else:
                endpoint.text = commercial_partner.peppol_identifier

        self._ubl_c5_credit_add_address(
            commercial_partner, "PostalAddress", party, ns, version=version
        )
        if commercial_partner.vat:
            self._ubl_c5_add_party_tax_scheme(commercial_partner, party, ns, version=version)
        if company or partner:
            self._ubl_c5_add_party_legal_entity(
                commercial_partner, party, ns, version="2.1"
            )
        if self.outgoing_inv_doc_ref_c5.invoice_ids:
            self._ubl_c5_credit_add_contact(partner, party, ns, version=version)

    def _ubl_c5_credit_add_address(self, partner, node_name, parent_node, ns, version="2.1"):
        address = etree.SubElement(parent_node, ns["cac"] + node_name)
        if partner.street:
            streetname = etree.SubElement(address, ns["cbc"] + "StreetName")
            streetname.text = partner.street
            print("streetname.text",streetname.text)
        if partner.street2:
            addstreetname = etree.SubElement(
                address, ns["cbc"] + "AdditionalStreetName"
            )
            addstreetname.text = partner.street2
        if partner.city:
            city = etree.SubElement(address, ns["cbc"] + "CityName")
            city.text = partner.city
        if partner.zip:
            zip_code = etree.SubElement(address, ns["cbc"] + "PostalZone")
            zip_code.text = partner.zip
        if partner.state_id:
            state = etree.SubElement(address, ns["cbc"] + "CountrySubentity")
            state.text = partner.state_id.name
        if partner.country_id:
            self._ubl_c5_add_country(partner.country_id, address, ns, version=version)
        else:
            logger.warning("UBL: missing country on partner %s", partner.name)

    @api.model
    def _ubl_c5_credit_add_contact(
            self, partner, parent_node, ns, node_name="Contact", version="2.1"
    ):
        contact = etree.SubElement(parent_node, ns["cac"] + node_name)
        contact_id_text = self._ubl_get_contact_id(partner)
        if contact_id_text:
            contact_id = etree.SubElement(contact, ns["cbc"] + "ID")
            contact_id.text = contact_id_text
        contact_name = etree.SubElement(contact, ns["cbc"] + "Name")
        contact_name.text = partner.name

    @api.model
    def _ubl_c5_credit_add_customer_party(self, partner, company, node_name, parent_node, ns, version="2.1"):
        print("\n_ubl_add_customer_party() >>", partner, company)
        if company:
            if partner:
                assert (
                        partner.commercial_partner_id == company.partner_id
                ), "partner is wrong"
            else:
                partner = company.partner_id
        print("partner ==", partner)
        customer_party_root = etree.SubElement(parent_node, ns["cac"] + node_name)
        self._ubl_c5_credit_add_party(
            partner, company, "Party", customer_party_root, ns, version=version
        )

    def _ubl_c5_add_creditnote_line(self, parent_node, iline, line_number, ns, version="2.1"):
        self.ensure_one()
        cur_name = self.currency_id.name
        line_root = etree.SubElement(parent_node, ns["cac"] + "CreditNoteLine")
        dpo = self.env["decimal.precision"]
        qty_precision = dpo.precision_get("Product Unit of Measure")
        price_precision = dpo.precision_get("Product Price")
        account_precision = self.currency_id.decimal_places
        line_id = etree.SubElement(line_root, ns["cbc"] + "ID")
        line_id.text = str(line_number)
        uom_unece_code = False
        # product_uom_id is not a required field on account.move.line
        if iline.product_uom_id.unece_code:
            uom_unece_code = iline.product_uom_id.unece_code
            quantity = etree.SubElement(
                line_root, ns["cbc"] + "CreditedQuantity", unitCode=uom_unece_code
            )
        else:
            quantity = etree.SubElement(line_root, ns["cbc"] + "CreditedQuantity")
        qty = iline.quantity
        quantity.text = "%0.*f" % (qty_precision, qty)
        line_amount = etree.SubElement(
            line_root, ns["cbc"] + "LineExtensionAmount", currencyID=cur_name
        )
        line_amount.text = "%0.*f" % (account_precision, iline.price_subtotal)
        if iline.sale_line_ids and iline.sale_line_ids[0].incoming_order_line_id and self.outgoing_inv_doc_ref_c5.invoice_ids:
            order_line_ref_root = etree.SubElement(line_root, ns["cac"] + "OrderLineReference")
            order_lineref_id = etree.SubElement(order_line_ref_root, ns["cbc"] + "LineID")
            order_lineref_id.text = iline.sale_line_ids[0].incoming_order_line_id.line_item_id
        self._ubl_c5_add_item(
            iline.name, iline.product_id, line_root, ns, iline, type_="sale", version=version
        )
        price_node = etree.SubElement(line_root, ns["cac"] + "Price")
        price_amount = etree.SubElement(
            price_node, ns["cbc"] + "PriceAmount", currencyID=cur_name
        )
        # price_unit = 0.0
        # Use price_subtotal/qty to compute price_unit to be sure
        # to get a *tax_excluded* price unit
        # if not float_is_zero(qty, precision_digits=qty_precision):
        #     price_unit = float_round(
        #         iline.price_subtotal / float(qty), precision_digits=price_precision
        #     )
        price_unit = iline.price_unit
        price_amount.text = "%0.*f" % (price_precision, price_unit)
        # if uom_unece_code:
        #     base_qty = etree.SubElement(
        #         price_node, ns["cbc"] + "BaseQuantity", unitCode=uom_unece_code
        #     )
        # else:
        #     base_qty = etree.SubElement(price_node, ns["cbc"] + "BaseQuantity")
        # base_qty.text = "%0.*f" % (qty_precision, 1.0)

    # Peppol and nonpeppol purchase part
    def generate_ubl_xml_string_c5(self, version="2.1"):
        self.ensure_one()
        assert self.state == "posted"
        assert self.move_type in ("in_invoice", "in_refund")
        logger.debug("Starting to generate UBL XML Invoice file")
        lang = self.get_ubl_lang()
        # The aim of injecting lang in context
        # is to have the content of the XML in the partner's lang
        # but the problem is that the error messages will also be in
        # that lang. But the error messages should almost never
        # happen except the first days of use, so it's probably
        # not worth the additional code to handle the 2 langs
        xml_root = self.with_context(lang=lang).generate_c5_bill_ubl_xml_etree(
            version=version
        )
        xml_string = etree.tostring(
            xml_root, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )
        self._ubl_check_xml_schema(xml_string, "Invoice", version=version)
        logger.debug(
            "Invoice UBL XML file generated for account invoice ID %d " "(state %s)",
            self.id,
            self.state,
        )
        logger.debug(xml_string.decode("utf-8"))
        print('\n\n\n\nxml_string', xml_string)
        return xml_string

    def generate_c5_bill_ubl_xml_etree(self, version="2.1"):
        self.ensure_one()
        # sbd_root = None
        sbd_ns = {None: "http://www.unece.org/cefact/namespaces/StandardBusinessDocumentHeader"}
        sbd_root = etree.Element("StandardBusinessDocument", nsmap=sbd_ns)
        print('\n\n\n\n\nsbd_root', sbd_root)
        self._ubl_add_sbd_header(sbd_root)
        nsmap, ns = self._ubl_get_nsmap_namespace("Invoice-2", version=version)
        invoice_root = etree.SubElement(sbd_root, "Invoice", nsmap=nsmap)
        self._ubl_c5_add_header(invoice_root, ns, version=version)
        self._ubl_c5_add_order_reference(invoice_root, ns, version=version)
        self._ubl_c5_add_supplier_party(
            False,
            self.company_id,
            "AccountingSupplierParty",
            invoice_root,
            ns,
            version=version,
        )
        self._ubl_c5_add_customer_party(
            self.partner_id,
            False,
            "AccountingCustomerParty",
            invoice_root,
            ns,
            version=version,
        )
        if self.invoice_payment_term_id:
            self._ubl_add_payment_terms(
                self.invoice_payment_term_id, invoice_root, ns, version=version
            )
        self._ubl_c5_add_tax_total(invoice_root, ns, version=version)
        self._ubl_c5_add_legal_monetary_total(invoice_root, ns, version=version)

        line_number = 0
        for iline in self.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_section', 'line_note')):
            line_number += 1
            self._ubl_c5_add_invoice_line(
                invoice_root, iline, line_number, ns, version=version
            )
        return sbd_root

    def _ubl_add_sbd_header(self, parent_node):
        """ Creates the StandardBusinessDocumentHeader part of the XML. """
        sbdh_ns = {None: "http://www.unece.org/cefact/namespaces/StandardBusinessDocumentHeader"}

        sbd_header = etree.SubElement(parent_node, "StandardBusinessDocumentHeader", nsmap=sbdh_ns)

        # Header Version
        header_version = etree.SubElement(sbd_header, "HeaderVersion")
        header_version.text = "1.0"

        # Sender
        sender = etree.SubElement(sbd_header, "Sender")
        sender_id = etree.SubElement(sender, "Identifier", Authority="iso6523-actorid-upis")
        sender_id.text = self.company_id.partner_id.commercial_partner_id.peppol_identifier

        # Receiver
        receiver = etree.SubElement(sbd_header, "Receiver")
        receiver_id = etree.SubElement(receiver, "Identifier", Authority="iso6523-actorid-upis")
        receiver_id.text = "IRAS"

        # Document Identification
        doc_ident = etree.SubElement(sbd_header, "DocumentIdentification")
        standard = etree.SubElement(doc_ident, "Standard")
        standard.text = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"

        type_version = etree.SubElement(doc_ident, "TypeVersion")
        type_version.text = "2.1"

        access_point = self.env['peppol.access.point.sg'].sudo().search([('company_id', '=', self.company_id.id)],
                                                                        order="create_date")
        transmission_uuid = access_point.get_uuid()
        instance_id = etree.SubElement(doc_ident, "InstanceIdentifier")
        instance_id.text = transmission_uuid

        doc_type = etree.SubElement(doc_ident, "Type")
        doc_type.text = "Invoice"

        creation_date = etree.SubElement(doc_ident, "CreationDateAndTime")
        creation_date.text = fields.Datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Business Scope
        business_scope = etree.SubElement(sbd_header, "BusinessScope")

        # Scope 1
        scope1 = etree.SubElement(business_scope, "Scope")
        scope1_type = etree.SubElement(scope1, "Type")
        scope1_type.text = "DOCUMENTID"
        scope1_instance = etree.SubElement(scope1, "InstanceIdentifier")
        scope1_instance.text = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:peppol:pint:billing-1@sg-1:LocalTaxInvoice:sg:1.0::2.1"
        scope1_id = etree.SubElement(scope1, "Identifier")
        scope1_id.text = "peppol-doctype-wildcard"

        # Scope 2
        scope2 = etree.SubElement(business_scope, "Scope")
        scope2_type = etree.SubElement(scope2, "Type")
        scope2_type.text = "PROCESSID"
        scope2_instance = etree.SubElement(scope2, "InstanceIdentifier")
        scope2_instance.text = "urn:peppol:bis:billing"
        scope2_id = etree.SubElement(scope2, "Identifier")
        scope2_id.text = "cenbii-procid-ubl"

        # Scope 3
        scope3 = etree.SubElement(business_scope, "Scope")
        scope3_type = etree.SubElement(scope3, "Type")
        scope3_type.text = "Document_UUID"
        scope3_instance = etree.SubElement(scope3, "InstanceIdentifier")
        scope3_instance.text = transmission_uuid

    def generate_credit_ubl_xml_string_c5(self, version="2.1"):
        self.ensure_one()
        assert self.state == "posted"
        assert self.move_type in ("in_refund")
        logger.debug("Starting to generate UBL XML CreditNote file")
        lang = self.get_ubl_lang()
        xml_root = self.with_context(lang=lang).generate_c5_credit_bill_ubl_xml_etree(
            version=version
        )
        print("xml_root >>>>>>>>>>", xml_root)
        xml_string = etree.tostring(
            xml_root, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )
        print("xml_string >>>>>>>>>>",xml_string)
        self._ubl_check_xml_schema(xml_string, "CreditNote", version=version)
        logger.debug(
            "Credit Note UBL XML file generated for account Credit ID %d " "(state %s)",
            self.id,
            self.state,
        )
        logger.debug(xml_string.decode("utf-8"))
        return xml_string

    def generate_c5_credit_bill_ubl_xml_etree(self, version="2.1"):
        self.ensure_one()
        sbd_ns = {None: "http://www.unece.org/cefact/namespaces/StandardBusinessDocumentHeader"}
        sbd_root = etree.Element("StandardBusinessDocument", nsmap=sbd_ns)
        print('\n\n\n\n\nsbd_root', sbd_root)
        self._ubl_credit_add_sbd_header(sbd_root)
        nsmap, ns = self._ubl_get_nsmap_namespace("CreditNote-2", version=version)
        invoice_root = etree.SubElement(sbd_root, "CreditNote", nsmap=nsmap)

        self._ubl_c5_add_header(invoice_root, ns, version=version)
        self._ubl_c5_add_order_reference(invoice_root, ns, version=version)
        self._ubl_c5_credit_add_billing_reference(invoice_root, ns, version=version)
        self._ubl_c5_credit_add_supplier_party(
            False,
            self.company_id,
            "AccountingSupplierParty",
            invoice_root,
            ns,
            version=version,
        )
        self._ubl_c5_credit_add_customer_party(
            self.partner_id,
            False,
            "AccountingCustomerParty",
            invoice_root,
            ns,
            version=version,
        )
        self._ubl_c5_add_tax_total(invoice_root, ns, version=version)
        self._ubl_c5_add_legal_monetary_total(invoice_root, ns, version=version)

        line_number = 0
        for iline in self.invoice_line_ids:
            line_number += 1
            self._ubl_c5_add_creditnote_line(
                    invoice_root, iline, line_number, ns, version=version
                )
        return sbd_root

    def _create_b2c_outgoing_invoice(self):
        company = self.company_id  # Take company from first invoice
        currency = self.currency_id  # Use currency from invoices

        # Aggregate amounts
        tax_amount = self.amount_tax
        taxable_amount = self.amount_untaxed
        total_amount = self.amount_total

        # Get the latest invoice date
        issue_date = self.invoice_date
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

    # @api.onchange('partner_id')
    # def partner_id_onchange(self):
    #     """ this method to show the update peppol identifier button by setting boolean field"""
    #     if self.peppol_identifier:
    #         self.peppol_identifier = self.peppol_identifier.upper()
    #     if self.peppol_id_created:
    #         self.hide_update_peppol_id_btn = 0



class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    line_item_id = fields.Char("Order Line Ref")




