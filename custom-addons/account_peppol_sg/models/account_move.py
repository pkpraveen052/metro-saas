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

logger = logging.getLogger(__name__)

TIMEOUT = 20


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "base.ubl"]

    peppol_invoice_no = fields.Char(string="Peppol Invoice No", copy=False)
    peppol_invoice_doc_ids = fields.Many2many(
        'ir.attachment', 'account_move_peppol_docs_rel', 'move_id', 'attachment_id',
        string='Received Documents', copy=False)
    outgoing_inv_doc_ref = fields.Many2one('peppol.queue.out', string="Document Ref", copy=False)

    def _ubl_add_tax_total(self, xml_root, ns, version="2.1"):
        self.ensure_one()
        cur_name = self.currency_id.name
        tax_total_node = etree.SubElement(xml_root, ns["cac"] + "TaxTotal")
        tax_amount_node = etree.SubElement(
            tax_total_node, ns["cbc"] + "TaxAmount", currencyID=cur_name
        )
        prec = self.currency_id.decimal_places
        tax_amount_node.text = "%0.*f" % (prec, self.amount_tax)
        if not float_is_zero(self.amount_tax, precision_digits=prec):
            tax_lines = self.line_ids.filtered(lambda line: line.tax_line_id)
            res = {}
            # There are as many tax line as there are repartition lines
            done_taxes = set()
            for line in tax_lines:
                res.setdefault(
                    line.tax_line_id.tax_group_id,
                    {"base": 0.0, "amount": 0.0, "tax": False},
                )
                res[line.tax_line_id.tax_group_id]["amount"] += line.price_subtotal
                tax_key_add_base = tuple(self._get_tax_key_for_group_add_base(line))
                if tax_key_add_base not in done_taxes:
                    res[line.tax_line_id.tax_group_id]["base"] += line.tax_base_amount
                    res[line.tax_line_id.tax_group_id]["tax"] = line.tax_line_id
                    done_taxes.add(tax_key_add_base)
            res = sorted(res.items(), key=lambda l: l[0].sequence)
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

    @api.model
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
        self._ubl_add_tax_category(tax, tax_subtotal, ns, version=version)

    @api.model
    def _ubl_add_tax_category(self, tax, parent_node, ns, node_name="TaxCategory", version="2.1"):
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
        # if not tax.unece_type_id:
        #     raise UserError(_("Missing UNECE Tax Type on tax '%s'" % tax.name))
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
        # NOTE:: Commented below 'prepaid_amount' because Storecove mentioned: invoice.prepaidAmount and invoice.payableRoundingAmount are not acceptable
        # prepaid_amount = etree.SubElement(
        #     monetary_total, ns["cbc"] + "PrepaidAmount", currencyID=cur_name
        # )
        # prepaid_value = self.amount_total - self.amount_residual
        # prepaid_amount.text = "%0.*f" % (prec, prepaid_value)
        payable_amount = etree.SubElement(
            monetary_total, ns["cbc"] + "PayableAmount", currencyID=cur_name
        )
        payable_amount.text = "%0.*f" % (prec, self.amount_residual)

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
        self._ubl_add_item(
            iline.name, iline.product_id, line_root, ns, type_="sale", version=version
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
            filename = "Invoice-" + self.name + ".pdf"
            docu_reference = etree.SubElement(
                parent_node, ns["cac"] + "AdditionalDocumentReference"
            )
            docu_reference_id = etree.SubElement(docu_reference, ns["cbc"] + "ID")
            docu_reference_id.text = filename
            attach_node = etree.SubElement(docu_reference, ns["cac"] + "Attachment")
            binary_node = etree.SubElement(
                attach_node,
                ns["cbc"] + "EmbeddedDocumentBinaryObject",
                mimeCode="application/pdf",
                filename=filename,
            )
            ctx = dict()
            ctx["no_embedded_ubl_xml"] = True
            ctx["force_report_rendering"] = True
            pdf_inv = (
                self.with_context(ctx).env.ref("account.account_invoices")._render_qweb_pdf(self.ids)[0]
            )
            binary_node.text = base64.b64encode(pdf_inv)

    def _ubl_add_order_reference(self, parent_node, ns, version="2.1"):
        self.ensure_one()
        if self.name:
            order_ref = etree.SubElement(parent_node, ns["cac"] + "OrderReference")
            order_ref_id = etree.SubElement(order_ref, ns["cbc"] + "ID")
            order_ref_id.text = self.name

    def _ubl_add_header(self, parent_node, ns, version="2.1"):
        self.ensure_one()
        ubl_version = etree.SubElement(parent_node, ns["cbc"] + "UBLVersionID")
        ubl_version.text = version
        ubl_customization_id = etree.SubElement(parent_node, ns["cbc"] + "CustomizationID")
        ubl_customization_id.text = "urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:sg:3.0"
        ubl_profile_id = etree.SubElement(parent_node, ns["cbc"] + "ProfileID")
        ubl_profile_id.text = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"
        ubl_version.text = version
        doc_id = etree.SubElement(parent_node, ns["cbc"] + "ID")
        doc_id.text = self.name
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
        if self.invoice_user_id:
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
        # self._ubl_add_address(
        #     commercial_partner,
        #     "RegistrationAddress",
        #     party_legal_entity,
        #     ns,
        #     version=version,
        # )

    @api.model
    def _ubl_add_tax_scheme(self, tax_scheme_dict, parent_node, ns, version="2.1"):
        tax_scheme = etree.SubElement(parent_node, ns["cac"] + "TaxScheme")
        if tax_scheme_dict.get("id"):
            tax_scheme_id = etree.SubElement(
                tax_scheme, ns["cbc"] + "ID"
                # tax_scheme, ns["cbc"] + "ID", schemeID="UN/ECE 5153", schemeAgencyID="6"
            )
            tax_scheme_id.text = tax_scheme_dict["id"]

    @api.model
    def _ubl_get_tax_scheme_dict_from_partner(self, commercial_partner):
        tax_scheme_dict = {"id": "GST", "name": False, "type_code": False}
        return tax_scheme_dict

    @api.model
    def _ubl_add_party_tax_scheme(
            self, commercial_partner, parent_node, ns, version="2.1"
    ):
        if commercial_partner.vat:
            party_tax_scheme = etree.SubElement(
                parent_node, ns["cac"] + "PartyTaxScheme"
            )
            # registration_name = etree.SubElement(
            #     party_tax_scheme, ns["cbc"] + "RegistrationName"
            # )
            # registration_name.text = commercial_partner.name
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
        # if hasattr(partner, "street3") and partner.street3:
        #     blockname = etree.SubElement(address, ns["cbc"] + "BlockName")
        #     blockname.text = partner.street3
        if partner.city:
            city = etree.SubElement(address, ns["cbc"] + "CityName")
            city.text = partner.city
        if partner.zip:
            zip_code = etree.SubElement(address, ns["cbc"] + "PostalZone")
            zip_code.text = partner.zip
        if partner.state_id:
            state = etree.SubElement(address, ns["cbc"] + "CountrySubentity")
            state.text = partner.state_id.name
            # state_code = etree.SubElement(address, ns["cbc"] + "CountrySubentityCode")
            # state_code.text = partner.state_id.code
        addressline = etree.SubElement(address, ns["cac"] + "AddressLine")
        addressline_line = etree.SubElement(addressline, ns["cbc"] + "Line")
        addressline_line.text = "Sales department"
        #     blockname.text = partner.street3
        if partner.country_id:
            self._ubl_add_country(partner.country_id, address, ns, version=version)
        else:
            logger.warning("UBL: missing country on partner %s", partner.name) @ api.model

    # @api.model
    # def _ubl_get_party_identification(self, commercial_partner):
    #     """This method is designed to be inherited in localisation modules
    #     Should return a dict with key=SchemeName, value=Identifier"""
    #     return {}
    #
    # @api.model
    # def _ubl_add_party_identification(
    #     self, commercial_partner, parent_node, ns, version="2.1"
    # ):
    #     id_dict = self._ubl_get_party_identification(commercial_partner)
    #     if id_dict:
    #         party_identification = etree.SubElement(
    #             parent_node, ns["cac"] + "PartyIdentification"
    #         )
    #         for scheme_name, party_id_text in id_dict.items():
    #             party_identification_id = etree.SubElement(
    #                 party_identification, ns["cbc"] + "ID", schemeName=scheme_name
    #             )
    #             party_identification_id.text = party_id_text
    #     return

    @api.model
    def _ubl_add_party(
            self, partner, company, node_name, parent_node, ns, version="2.1"
    ):
        commercial_partner = partner.commercial_partner_id
        party = etree.SubElement(parent_node, ns["cac"] + node_name)
        party_name = etree.SubElement(party, ns["cac"] + "PartyName")
        name = etree.SubElement(party_name, ns["cbc"] + "Name")
        name.text = commercial_partner.name
        # if partner.lang:
        #     self._ubl_add_language(partner.lang, party, ns, version=version)
        self._ubl_add_address(
            commercial_partner, "PostalAddress", party, ns, version=version
        )
        self._ubl_add_party_tax_scheme(commercial_partner, party, ns, version=version)
        if company or partner:
            self._ubl_add_party_legal_entity(
                commercial_partner, party, ns, version="2.1"
            )
        self._ubl_add_contact(partner, party, ns, version=version)

    @api.model
    def _ubl_add_supplier_party(
            self, partner, company, node_name, parent_node, ns, version="2.1"
    ):
        """The company argument has been added to properly handle the
        'ref' field.
        In Odoo, we only have one ref field, in which we are supposed
        to enter the reference that our company gives to its
        customers/suppliers. We unfortunately don't have a native field to
        enter the reference that our suppliers/customers give to us.
        So, to set the fields CustomerAssignedAccountID and
        SupplierAssignedAccountID, I need to know if the partner for
        which we want to build the party block is our company or a
        regular partner:
        1) if it is a regular partner, call the method that way:
            self._ubl_add_supplier_party(partner, False, ...)
        2) if it is our company, call the method that way:
            self._ubl_add_supplier_party(False, company, ...)
        """
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
        self._ubl_add_party(
            partner, company, "Party", supplier_party_root, ns, version=version
        )

    def generate_invoice_ubl_xml_etree(self, version="2.1"):
        self.ensure_one()
        nsmap, ns = self._ubl_get_nsmap_namespace("Invoice-2", version=version)
        xml_root = etree.Element("Invoice", nsmap=nsmap)
        self._ubl_add_header(xml_root, ns, version=version)
        self._ubl_add_order_reference(xml_root, ns, version=version)
        # :: NOT REQUIRED ::
        # self._ubl_add_contract_document_reference(xml_root, ns, version=version)
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
        for iline in self.invoice_line_ids:
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

    @api.model
    def _peppol_document_name_4type(self, plural=False):
        if plural:
            return _("Invoices")
        return _("Invoice")

    def action_send_via_peppol(self):
        self.ensure_one()
        Queue = self.env['peppol.queue.out']
        self.check_peppol_identifier()
        queue_ref = Queue._add_to_queue(self)
        self.write({'outgoing_inv_doc_ref': queue_ref.id})

        return {
            'name': self.sudo().env.ref('account_peppol_sg.peppol_queue_out_action').name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'peppol.queue.out',
        }

    def _peppol_action_manual_send(self):
        for documents in self:
            document_count = len(self.filtered(lambda l: l.state == 'posted'))
            action = self.sudo().env.ref('account_peppol_sg.action_peppol_manual_send_wizard').read()[0] if document_count >= 1 else self.sudo().env.ref('account_peppol_sg.action_peppol_warning_wizard').read()[0]
            document_name_plural = documents._peppol_document_name_4type(plural=True if len(documents) > 1 else False)
            wiz_name = _("Send %s via PEPPOL") % document_name_plural if document_count >= 1 else _("Warning:")
            message = _("Send %s %s to PEPPOL.") % (document_count, document_name_plural) if document_count >= 1 else _("Only 'Posted' Invoices can be sent to Peppol.")
        action.update({
            'name': wiz_name,
            'context': {
                'default_message': message,
                'active_ids': self.ids,
            }
        })
        return action

    # date 14-05-2021 auther :goru vamsi
    def check_peppol_identifier(self):
        """
            This method is used to Check whether Storecove can deliver an invoice for a list of ids.
        """
        if not (self.partner_id.peppol_identifier and self.partner_id.peppol_scheme):
            raise UserError(
                _('The Peppol Identifier and Scheme is not set for the Customer %s.') % self.partner_id.name)

        access_point = self.env['peppol.access.point.sg'].search([('company_id', '=', self.company_id.id)])
        if not access_point:
            raise UserError(_("'Access Point' configuration is not defined for the Company %s.")
                            % self.company_id.name)

        end_point = access_point.endpoint
        api_key = access_point.authorization_key

        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(api_key),
            "Content-Type": "application/json"
        }
        data =  {
            "scheme": self.partner_id.peppol_scheme,
            "identifier": self.partner_id.peppol_identifier
        }

        try:
            req = requests.post("%s/discovery/receives" % end_point,
                                json=data,
                                headers=headers,
                                timeout=TIMEOUT)
        except requests.exceptions.Timeout:
            raise UserError(
                _('%s \nDiscover Network Participant API failed. A timeout occured while trying to reach the Storecove Api.') % self.name)
        except requests.exceptions.HTTPError as http_err:
            raise UserError(
                _('%s \nDiscover Network Participant API failed. HTTP error occurred while trying to reach the Storecove Api.') % self.name)
        except Exception as e:
            raise UserError(
                _('%s \nDiscover Network Participant API failed. The Storecove Api is not reachable, please try again later.') % self.name)
        if req.status_code == 200:
            response = req.json()
            if response['code'] == 'nok':
                raise UserError(_("Cannot deliver the invoice %s to the recipient %s. \nDetails: The result code of the Discover Network Participant request is 'nok'") % (self.name, self.partner_id.name))
            else:
                return True
            return True
        elif req.status_code == 401:
            raise UserError(_('%s \n401 Unauthorized') % self.name)
        elif req.status_code == 403:
            raise UserError(_('%s \nForbidden') % self.name)
        elif req.status_code == 422:
            raise UserError(_('%s \nUnprocessable Entity') % self.name)
        else:
            raise UserError(_('%s \nUndefined Error Occured') % self.name)
