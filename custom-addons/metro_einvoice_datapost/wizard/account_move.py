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

TIMEOUT = 20


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "base.ubl"]

    @api.model
    def default_get(self, fields):
        print("\nCUSTOM >> default_get() AccountMove >>>>>>")
        res = super(AccountMove, self).default_get(fields)
        print("res ==",res)
        ctx = self._context or {}
        print(ctx)
        if ctx.get('active_model') == 'peppol.queue.in' and ctx.get('active_id'):
            queue_obj = self.env['peppol.queue.in'].browse(self._context['active_id'])

            partner = self.env['res.partner'].search(['|',('peppol_identifier', '=', queue_obj.extracted_senderid.split(":")[1]),
                ('peppol_identifier', 'ilike', queue_obj.extracted_senderid.split(":")[1])], limit=1)
            if partner:
                res['partner_id'] = partner.id
            else:
                country_obj, child_dic = False, {}
                if queue_obj.sender_address_country:
                    country_obj = self.env['res.country'].search(['|',('name','=',queue_obj.sender_address_country), ('code','=',queue_obj.sender_address_country)], limit=1)
                if queue_obj.sender_contact_name:
                    child_dic = {'type': 'contact', 'name': queue_obj.sender_contact_name, 'email': queue_obj.sender_contact_email, 'phone': queue_obj.sender_contact_phone}
                partner = self.env['res.partner'].create({
                    'company_type': 'company',
                    'name': queue_obj.sender_party_name,
                    'street': queue_obj.sender_address_line1,
                    'street2': queue_obj.sender_address_line2,
                    'city':queue_obj.sender_address_city,
                    'zip': queue_obj.sender_address_zip,
                    'country_id': country_obj and country_obj.id or False,
                    'peppol_identifier': queue_obj.extracted_senderid.split(":")[1],
                    'peppol_scheme': '0195',
                    'child_ids': child_dic and [(0,0,child_dic)] or False
                    })
                res['partner_id'] = partner.id

            if queue_obj.due_date:
                res['invoice_date_due'] = queue_obj.due_date
            elif queue_obj.payment_terms:
                numbers = re.findall(r'\d+\.\d+|\d+', queue_obj.payment_terms)
                print("numbers ==",numbers)
                if numbers:
                    pobjs = self.env['account.payment.term'].search([('name', 'ilike', numbers[0])], limit=1)
                    print("pobjs ==",pobjs)
                    if pobjs:
                        res['invoice_payment_term_id'] = pobjs.id
            if queue_obj.issue_date:
                res['invoice_date'] = queue_obj.issue_date
            if queue_obj.note:
                res['narration'] = queue_obj.note

            invoice_lines = []
            for line in queue_obj.invoice_line_ids:
                default_codes, barcodes = [], []
                if line.buyers_item_identification:
                    product = self.env['product.product'].search(['|',('default_code', '=', line.buyers_item_identification), ('barcode', '=', line.buyers_item_identification)], limit=1)
                elif line.sellers_item_identification:
                    product = self.env['product.product'].search(['|',('default_code', '=', line.sellers_item_identification), ('barcode', '=', line.sellers_item_identification)], limit=1)
                elif line.standard_item_identification:
                    product = self.env['product.product'].search(['|',('default_code', '=', line.standard_item_identification), ('barcode', '=', line.standard_item_identification)], limit=1)
                elif line.item_classification_identifier:
                    product = self.env['product.product'].search(['|',('default_code', '=', line.item_classification_identifier), ('barcode', '=', line.item_classification_identifier)], limit=1)
                else:
                    product = self.env['product.product'].search(['|',('name', '=', line.name), ('name', 'ilike', line.name)], limit=1)

                res = self.env['account.move.line'].default_get(['partner_id', 'account_id'])
                print("line_res ==",res)
                invoice_line_values = {
                    'product_id': product.id if product else False,
                    'name': line.name,
                    'quantity': line.quantity,
                    'price_unit': line.price_amount,
                    'product_uom_id': product.uom_id.id if product and product.uom_id else False,
                    'display_type': False,
                    'account_id': 112,
                    'sequence': 1
                }
                discount = (line.quantity * line.price_amount) - line.amount_excluding_tax
                if discount > 0.0:
                    discount_percentage = (discount / (line.quantity * line.price_amount)) * 100
                    invoice_line_values.update({'discount': discount_percentage})
                invoice_lines.append((0, 0, invoice_line_values))
                
            res['invoice_line_ids'] = invoice_lines
            print("FINAL res ===",res)
        return res

    peppol_invoice_no = fields.Char(string="Peppol Invoice No", copy=False)
    peppol_invoice_doc_ids = fields.Many2many(
        'ir.attachment', 'account_move_peppol_docs_rel', 'move_id', 'attachment_id',
        string='Received Documents', copy=False)
    outgoing_inv_doc_ref = fields.Many2one('peppol.queue.out', string="Document Ref", copy=False)
    outgoing_inv_doc_ref_c5 = fields.Many2one('peppol.queue.c5.out', string="Document Ref", copy=False)
    bulk_c5_invoice = fields.Boolean(string="Is Bulk C5 Invoice", default=False)

    @api.model
    def create(self, vals):
        print("create == vals",vals)
        ctx = self._context
        print(ctx)
        obj =  super(AccountMove, self).create(vals)
        return obj

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
        if self.move_type == "out_invoice":
            if self.narration:
                note = etree.SubElement(parent_node, ns["cbc"] + "Note")
                note.text = self.narration
        else:
            if not self.ref:
                raise ValidationError("Please provide the reason/note for this Credit Note. Hint: Provide it under the Customer Reference field.")
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

        if self.partner_id.parent_id:
            partner_obj = self.partner_id.parent_id
        else:
            partner_obj = self.partner_id

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
        if is_gst: #not float_is_zero(self.amount_tax, precision_digits=prec)
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
            
            for _group, amounts in res:
                self._ubl_add_tax_subtotal(
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
                self._ubl_add_tax_subtotal(
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
        description = etree.SubElement(item, ns["cbc"] + "Description")
        description.text = name
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
        self._ubl_add_item(
            iline.name, iline.product_id, line_root, ns, iline, type_="sale", version=version
        )
        price_node = etree.SubElement(line_root, ns["cac"] + "Price")
        price_amount = etree.SubElement(
            price_node, ns["cbc"] + "PriceAmount", currencyID=cur_name
        )
        price_unit = 0.0
        # Use price_subtotal/qty to compute price_unit to be sure
        # to get a *tax_excluded* price unit
        if not float_is_zero(qty, precision_digits=qty_precision):
            price_unit = float_round(
                iline.price_subtotal / float(qty), precision_digits=price_precision
            )
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
        if self.company_id.embed_pdf_in_ubl_xml_invoice and not self.env.context.get(
                "no_embedded_pdf"
        ):
            for attachment in self.env['ir.attachment'].search([('res_id', '=', self.id)]):
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
                binary_node.text = base64.b64encode(attachment.datas)

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
            if sale_obj and sale_obj.origin:
                order_ref = etree.SubElement(parent_node, ns["cac"] + "OrderReference")
                order_ref_id = etree.SubElement(order_ref, ns["cbc"] + "ID")
                order_ref_id.text = sale_obj.origin

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


    def generate_invoice_ubl_xml_etree(self, version="2.1"):
        self.ensure_one()
        nsmap, ns = self._ubl_get_nsmap_namespace("Invoice-2", version=version)
        xml_root = etree.Element("Invoice", nsmap=nsmap)
        self._ubl_add_header(xml_root, ns, version=version)
        self._ubl_add_order_reference(xml_root, ns, version=version)
        self._ubl_add_attachments(xml_root, ns, version=version)
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
        endpoint = etree.SubElement(party, ns["cbc"] + "EndpointID", schemeID=commercial_partner.peppol_scheme or '')
        endpoint.text = commercial_partner.peppol_identifier or ''
        if commercial_partner.seller_identifier:
            party_name = etree.SubElement(party, ns["cac"] + "PartyIdentification")
            name = etree.SubElement(party_name, ns["cbc"] + "ID", schemeID=commercial_partner.seller_identifier_scheme or '')
            name.text = commercial_partner.seller_identifier
        else:
            party_name = etree.SubElement(party, ns["cac"] + "PartyIdentification")
            name = etree.SubElement(party_name, ns["cbc"] + "ID", schemeID='')
            name.text = commercial_partner.name
        self._ubl_credit_add_address(
            commercial_partner, "PostalAddress", party, ns, version=version
        )
        self._ubl_add_party_tax_scheme(commercial_partner, party, ns, version=version)
        if company or partner:
            self._ubl_add_party_legal_entity(
                commercial_partner, party, ns, version="2.1"
            )
        self._ubl_credit_add_contact(partner, party, ns, version=version)

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
        self._ubl_credit_customer_add_contact(partner, party, ns, version=version)


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
        price_unit = 0.0
        # Use price_subtotal/qty to compute price_unit to be sure
        # to get a *tax_excluded* price unit
        if not float_is_zero(qty, precision_digits=qty_precision):
            price_unit = float_round(
                iline.price_subtotal / float(qty), precision_digits=price_precision
            )
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

    def action_send_via_peppol(self):
        self.ensure_one()
        Queue = self.env['peppol.queue.out']
        queue_ref = Queue._add_to_queue(self)
        self.write({'outgoing_inv_doc_ref': queue_ref.id})

        return {
            'name': self.sudo().env.ref('metro_einvoice_datapost.peppol_queue_out_action').name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'peppol.queue.out',
            'domain': [('id','=',queue_ref.id)]
        }

    # prakash
    def action_send_via_peppol_c5(self):
        self.ensure_one()
        Queue = self.env['peppol.queue.c5.out']
        # self.partner_id.verify_identifier_registered()  #UNCOMMENT LATER
        queue_data = {'invoice_type': self.move_type, 'invoice_id': self.id}
        if self.partner_id.is_peppol_participant:
            queue_data['peppol_c5_purchase_inv'] = True
        else:
            queue_data['nonpeppol_c5_purchase_inv'] = True
        queue_ref = Queue.create(queue_data)
        print('\n\n\n\n\nqueue_ref', queue_ref)
        self.write({'outgoing_inv_doc_ref_c5': queue_ref.id})
        action_mapping = {
            ('in_invoice', True): 'metro_einvoice_datapost.peppol_queue_c5_out_action',
            ('in_invoice', False): 'metro_einvoice_datapost.non_peppol_queue_c5_purchase_inv_action',
            ('in_refund', True): 'metro_einvoice_datapost.peppol_credit_queue_c5_out_action',
            ('in_refund', False): 'metro_einvoice_datapost.non_peppol_queue_c5_purchase_credit_action'
        }
        action_ref = action_mapping.get(
            ('in_invoice' if queue_ref.invoice_type == 'in_invoice' else 'in_refund',
             self.partner_id.is_peppol_participant)
        )
        print('\n\n\n\n\naction_ref', action_ref)
        return {
            'name': self.sudo().env.ref(action_ref).name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'peppol.queue.c5.out',
            'domain': [('id', '=', queue_ref.id)]
        }

    def _peppol_action_manual_send(self):
        moves = self.filtered(lambda doc: doc.move_type in ('out_invoice', 'out_refund'))
        #UNCOMMENT LATER
        # for move in moves:
        #     move.partner_id.verify_identifier_registered()
        cus_peppol = moves.filtered(lambda doc: doc.partner_id.is_peppol_participant)
        print('\n\n\n\n\ncus_peppol', cus_peppol)
        cus_nonpeppol = moves.filtered(lambda doc: doc.partner_id.is_peppol_participant != True)
        print('\n\n\n\n\ncus_nonpeppol', cus_nonpeppol)
        default_is_both = bool(cus_peppol) and bool(cus_nonpeppol)
        print('\n\n\n\n\ndefault_is_both', default_is_both)
        if not moves:
            action = self.sudo().env.ref('metro_einvoice_datapost.action_peppol_manual_nosend_wizard').read()[0]
            action.update({
                'name': 'Warning:',
                'context': {
                    'default_message': 'You must not select these to perform this action.\n Note: Select only Sales Invoices.'
                }
            })
            return action
        for documents in self:
            document_count = len(self.filtered(lambda l: l.state == 'posted'))
            action = self.sudo().env.ref('metro_einvoice_datapost.action_peppol_manual_send_wizard').read()[0] if document_count >= 1 else self.sudo().env.ref('metro_einvoice_datapost.action_peppol_warning_wizard').read()[0]
            document_name_plural = documents._peppol_document_name_4type(plural=True if len(documents) > 1 else False)
            wiz_name = _("Send %s via PEPPOL") % document_name_plural if document_count >= 1 else _("Warning:")
            if document_count >= 1:
                if default_is_both:
                    message = _("Send %s %s to PEPPOL or NON-PEPPOL.") % (document_count, document_name_plural)
                else:
                    peppol_type = "PEPPOL" if cus_peppol else "NON-PEPPOL"
                    message = _("Send %s %s to %s.") % (document_count, document_name_plural, peppol_type)
            else:
                _("Only 'Posted' Invoices can be sent to Peppol.")
        if cus_peppol and not default_is_both:
            context = {
                'default_message': message,
                'active_ids': cus_peppol.ids,
                'default_is_both': default_is_both,
                'is_peppol': True
                }
        elif cus_nonpeppol and not default_is_both:
            context = {
                'default_message': message,
                'active_ids': cus_nonpeppol.ids,
                'default_is_both': default_is_both,
                'is_nonpeppol': True,
                }
        elif default_is_both:
            context = {
                'default_message': message,
                'cus_peppol_inv': cus_peppol.ids,
                'cus_nonpeppol_inv': cus_nonpeppol.ids,
                'default_is_both': default_is_both,
            }
        if moves and moves.filtered(lambda doc: doc.move_type == 'out_refund'):
            context.update({"default_is_sale_credit": True})
        action.update({
            'name': wiz_name,
            'context': context,
        })
        return action

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

    # C5 BUlk invoice and credit note start.
    def generate_c5_bulk_invoice_ubl_xml_etree(self, version="2.1"):
        self.ensure_one()
        assert self.state == "posted"
        assert self.move_type in ("out_invoice")
        logger.debug("Starting to generate UBL XML Invoice file")
        #####
        if self.move_type in ("out_invoice"):
            nsmap, ns = self._c5_bulk_ubl_get_nsmap_namespace("Invoice-2")
            print('\n\n\n\nnsmap', nsmap, '\n\n\nns', ns)
            invoice_root = etree.Element("Invoice", nsmap=nsmap)
        self._ubl_c5_add_header(invoice_root, ns, version=version)
        if self.outgoing_inv_doc_ref_c5.invoice_id:
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

    def _ubl_c5_add_header(self, parent_node, ns, version="2.1"):
        self.ensure_one()
        ubl_customization_id = etree.SubElement(parent_node, ns["cbc"] + "CustomizationID")
        ubl_profile_id = etree.SubElement(parent_node, ns["cbc"] + "ProfileID")
        if self.move_type == "in_invoice":
            ubl_customization_id.text = "urn:peppol:pint:billing-1@sg-1:LocalTaxInvoice:sg:1.0"
            ubl_profile_id.text = "urn:peppol:bis:Payables"
        else:
            ubl_customization_id.text = "urn:peppol:pint:billing-1@sg-1:LocalTaxInvoice:sg:1.0"
            ubl_profile_id.text = "urn:peppol:bis:billing"
        doc_id = etree.SubElement(parent_node, ns["cbc"] + "ID")
        doc_id.text = self.name
        access_point = self.env['peppol.access.point.sg'].sudo().search([('company_id', '=', self.company_id.id)],
                                                                        order="create_date")
        client_ref = access_point.get_uuid()
        doc_uuid = etree.SubElement(parent_node, ns["cbc"] + "UUID")
        doc_uuid.text = client_ref
        issue_date = etree.SubElement(parent_node, ns["cbc"] + "IssueDate")
        issue_date.text = self.invoice_date.strftime("%Y-%m-%d")
        due_date = etree.SubElement(parent_node, ns["cbc"] + "DueDate")
        due_date.text = self.invoice_date_due.strftime("%Y-%m-%d")
        type_code = etree.SubElement(parent_node, ns["cbc"] + "InvoiceTypeCode")
        if self.move_type in ("out_invoice", "in_invoice"):
            type_code.text = "380"
        if self.narration:
            note = etree.SubElement(parent_node, ns["cbc"] + "Note")
            note.text = self.narration
        doc_currency = etree.SubElement(parent_node, ns["cbc"] + "DocumentCurrencyCode")
        doc_currency.text = self.currency_id.name

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
        commercial_partner = partner.commercial_partner_id
        party = etree.SubElement(parent_node, ns["cac"] + node_name)
        endpoint = etree.SubElement(party, ns["cbc"] + "EndpointID", schemeID=commercial_partner.peppol_scheme or '')
        if company:
            endpoint.text = commercial_partner.peppol_identifier or ''
        else:
            uen = commercial_partner.l10n_sg_unique_entity_number
            endpoint.text = f"C5UID{uen}" if uen else "C5UID"
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
        if self.move_type in ("out_invoice") and self.outgoing_inv_doc_ref_c5.invoice_ids: #bulk sale invoice only
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

    @api.model
    def _ubl_c5_add_notax_category(self, tax, parent_node, ns, node_name="ClassifiedTaxCategory", version="2.1"):
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
        price_unit = 0.0
        # Use price_subtotal/qty to compute price_unit to be sure
        # to get a *tax_excluded* price unit
        if not float_is_zero(qty, precision_digits=qty_precision):
            price_unit = float_round(
                iline.price_subtotal / float(qty), precision_digits=price_precision
            )
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
    def generate_c5_bulk_credit_ubl_xml_etree(self, version="2.1"):
        self.ensure_one()
        assert self.state == "posted"
        assert self.move_type in ("out_refund")
        logger.debug("Starting to generate UBL XML Invoice file")
        #####
        if self.move_type in ("out_refund"):
            nsmap, ns = self._c5_bulk_ubl_get_nsmap_namespace("CreditNote-2")
            invoice_root = etree.Element("CreditNote", nsmap=nsmap)
        self._ubl_c5_credit_add_header(invoice_root, ns, version=version)
        self._ubl_c5_add_order_reference(invoice_root, ns, version=version)
        self._ubl_c5_credit_add_billing_reference(invoice_root, ns, version=version)
        if self.currency_id.id != self.company_id.currency_id.id:
            self._ubl_add_additional_documents(invoice_root, ns, version=version)
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

    def _ubl_c5_credit_add_header(self, parent_node, ns, version="2.1"):
        self.ensure_one()
        if self.move_type in ("out_refund"):
            ubl_version = etree.SubElement(parent_node, ns["cbc"] + "UBLVersionID")
            ubl_version.text = version
        ubl_customization_id = etree.SubElement(parent_node, ns["cbc"] + "CustomizationID")
        ubl_profile_id = etree.SubElement(parent_node, ns["cbc"] + "ProfileID")
        if self.move_type == 'out_refund':
            ubl_customization_id.text = "urn:peppol:pint:billing-1@sg-1:LocalTaxInvoice:sg:1.0"
            ubl_profile_id.text = "urn:peppol:bis:billing"
        elif self.move_type in ("in_refund"):
            ubl_customization_id.text = "urn:peppol:pint:billing-1@sg-1:LocalTaxInvoice:sg:1.0"
            ubl_profile_id.text = "urn:peppol:bis:Payables"
        doc_id = etree.SubElement(parent_node, ns["cbc"] + "ID")
        doc_id.text = self.name
        access_point = self.env['peppol.access.point.sg'].sudo().search([('company_id', '=', self.company_id.id)],
                                                                        order="create_date")
        client_ref = access_point.get_uuid()
        doc_uuid = etree.SubElement(parent_node, ns["cbc"] + "UUID")
        doc_uuid.text = client_ref
        issue_date = etree.SubElement(parent_node, ns["cbc"] + "IssueDate")
        issue_date.text = self.invoice_date.strftime("%Y-%m-%d")
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
        billing_ref = etree.SubElement(parent_node, ns["cac"] + "BillingReference")
        if self.reversed_entry_id:
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
        commercial_partner = partner.commercial_partner_id
        party = etree.SubElement(parent_node, ns["cac"] + node_name)
        endpoint = etree.SubElement(party, ns["cbc"] + "EndpointID", schemeID=commercial_partner.peppol_scheme or '')
        if company:
            endpoint.text = commercial_partner.peppol_identifier or ''
        else:
            uen = commercial_partner.l10n_sg_unique_entity_number
            endpoint.text = f"C5UID{uen}" if uen else "C5UID"
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
        price_unit = 0.0
        # Use price_subtotal/qty to compute price_unit to be sure
        # to get a *tax_excluded* price unit
        if not float_is_zero(qty, precision_digits=qty_precision):
            price_unit = float_round(
                iline.price_subtotal / float(qty), precision_digits=price_precision
            )
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

        self._ubl_c5_credit_add_header(invoice_root, ns, version=version)
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