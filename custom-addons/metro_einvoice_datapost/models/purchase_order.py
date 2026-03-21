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

logger = logging.getLogger(__name__)

TIMEOUT = 20

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model
    def default_get(self, fields):
        res = super(PurchaseOrder, self).default_get(fields)
        ctx = self._context or {}
        if ctx.get('active_model') == 'peppol.queue.in' and ctx.get('active_id'):
            peppol_in_record = self.env['peppol.queue.in'].browse(self._context['active_id'])
            partner = self.env['res.partner'].search(['|',('peppol_identifier', '=', peppol_in_record.extracted_senderid.split(":")[1]),
                ('peppol_identifier', 'ilike', peppol_in_record.extracted_senderid.split(":")[1])], limit=1)
            if partner:
                res['partner_id'] = partner.id
            order_lines = []
            for invoice_line in peppol_in_record.invoice_line_ids:
                product = self.env['product.product'].search(['|',('name', '=', invoice_line.name), ('name', 'ilike', invoice_line.name)], limit=1)
                order_line_values = {
                    'product_id': product.id if product else False,
                    'name': invoice_line.name,
                    'product_qty': invoice_line.quantity,
                    'price_unit': invoice_line.price_amount,
                    'date_planned': invoice_line.create_date,
                    'price_subtotal': invoice_line.amount_excluding_tax,
                    'product_uom': product.uom_id.id if product and product.uom_id else False,
                }
                order_lines.append((0, 0, order_line_values))
                
            res['order_line'] = order_lines
            res['amount_tax'] = peppol_in_record.taxed_amt if peppol_in_record else 0.0
            res['amount_total'] = peppol_in_record.amt_including_tax if peppol_in_record else 0.0

            res['notes'] = peppol_in_record.note

        return res

    peppol_log_count = fields.Integer(string="Purchase Order Count", compute="_compute_peppol_log_count")
    outgoing_order_doc_ref = fields.Many2one('order.queue.out', string="Peppol Outgoing Document Ref", copy=False)
    outgoing_order_change_doc_ref = fields.Many2one('order.change.queue.out', string="Peppol Outgoing Document Change Ref", copy=False)
    outgoing_order_cancel_doc_ref = fields.Many2one('order.cancel.queue.out', string="Peppol Outgoing Document Cancel Ref", copy=False)
    outgoing_order_balance_doc_ref = fields.Many2one('order.balance.queue.out', string="Peppol Outgoing Document Balance Ref", copy=False)
    order_note = fields.Char('Order Note')

    @api.model
    def create(self, vals):
        ctx = self._context
        print(ctx)
        po_obj =  super(PurchaseOrder, self).create(vals)
        if ctx.get('active_model') == 'peppol.queue.in' and ctx.get('active_id'):
            queue_obj = self.env['peppol.queue.in'].browse(self._context['active_id'])
            queue_obj = self.env['peppol.queue.in'].browse(ctx['active_id'])
            if not po_obj.partner_id.peppol_identifier:
                raise ValidationError("Peppol Identifier for Vendor %s is not defined." % (po_obj.partner_id.name))
            vendor_peppol_id = queue_obj.extracted_senderid.split(":")[1]
            if po_obj.partner_id.peppol_identifier.lower() != vendor_peppol_id.lower():
                raise ValidationError("Vendor's Peppol identifier does not match. Mapping cannot be allowed.")
            # if po_obj.amount_total != queue_obj.amt_including_tax: #TODO
            #     raise ValidationError("Vendor's Total Amount does not match. Mapping cannot be allowed.")
            queue_obj.write({
                'po_id': po_obj.id,
                'message': "Purchase Order mapped successfully!",
                'state': 'success'})
        return po_obj

    def map_to_incoming_invoice(self):        
        self.ensure_one()
        ctx = self._context or {}
        if ctx.get('active_model') == 'peppol.queue.in':
            queue_obj = self.env['peppol.queue.in'].browse(ctx['active_id'])
            if not self.partner_id.peppol_identifier:
                raise ValidationError("Peppol Identifier for Vendor %s is not defined." % (self.partner_id.name))
            vendor_peppol_id = queue_obj.extracted_senderid.split(":")[1]
            if self.partner_id.peppol_identifier.lower() != vendor_peppol_id.lower():
                raise ValidationError("Vendor's Peppol identifier does not match. Mapping cannot be allowed.")
            if self.amount_total != queue_obj.amt_including_tax:
                raise ValidationError("Vendor's Total Amount does not match. Mapping cannot be allowed.")
            queue_obj.write({
                'po_id': self.id,
                'state': 'success',
                'message': 'Purchase Order mapped Successfully!',
            })
            return {
                'type': 'ir.actions.act_url',
                'url': "/web#id=" + str(queue_obj.id) + "&action=" + str(self.env.ref(
                    'metro_einvoice_datapost.action_pepppol_log_sg_view').id) + "&model=peppol.queue.in&view_type=form&cids=&menu_id=" + str(
                    self.env.ref('metro_einvoice_datapost.menu_sub_peppol_log').id)
            }

    def _compute_peppol_log_count(self):
        self.peppol_log_count = len(self.env['peppol.queue.in'].search([('po_id', '=', self.id)]))

    def action_view_peppol_log(self):
        """It gives a list view of Incoming Invoice Documents which have same purchase order number."""
        action = {
            'name': _('Incoming Invoice Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'peppol.queue.in',
            'target': 'current',
            'view_mode': 'tree,form'
        }
        order_ids = self.env['peppol.queue.in'].search([('po_id', '=', self.id)]).ids
        action['domain'] = [('id', 'in', order_ids)]
        return action

    def action_send_via_peppol(self):
        self.ensure_one()
        Queue = self.env['order.queue.out']
        queue_ref = Queue._add_to_queue(self)
        self.write({'outgoing_order_doc_ref': queue_ref.id})

        return {
            'name': self.sudo().env.ref('metro_einvoice_datapost.order_queue_out_action').name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'order.queue.out',
            'domain': [('id','=',queue_ref.id)]
        }

    def generate_ubl_xml_string_bkp(self, version="2.1"):
        self.ensure_one()
        assert self.state == "purchase"
        logger.debug("Starting to generate UBL XML Order file")
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
        assert self.state == "purchase"
        xml_string = self.generate_ubl_xml_string()
        filename = "UBL-Order-2.1.xml"
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


    def generate_ubl_xml_string(self, queue_obj=False):
        print("\ngenerate_ubl_xml_string ===",self)
        issue_date = datetime.now()
        print('\n\n\nissue_date>>>>>>>>>>>>>>>>>>>.', issue_date)
        if queue_obj:
            queue_obj.issue_date = issue_date

        cur_name = self.currency_id.name
        prec = self.currency_id.decimal_places
        doc_type_nsmap = {
            'initial': {
                'namespace': "urn:oasis:names:specification:ubl:schema:xsd:Order-2",
                'root_tag': "Order",
                'customization_id': "urn:fdc:peppol.eu:poacc:trns:order:3",
                'profile_id': "urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3",
            },
            'balance': {
                'namespace': "urn:oasis:names:specification:ubl:schema:xsd:Order-2",
                'root_tag': "Order",
                'customization_id': "urn:fdc:imda.gov.sg:trns:order_balance:1",
                'profile_id': "urn:fdc:imda.gov.sg:bis:order_balance:1",
            },
            'variation': {
                'namespace': "urn:oasis:names:specification:ubl:schema:xsd:OrderChange-2",
                'root_tag': "OrderChange",
                'customization_id': "urn:fdc:peppol.eu:poacc:trns:order_change:3",
                'profile_id': "urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3",
            },
            'cancel': {
                'namespace': "urn:oasis:names:specification:ubl:schema:xsd:OrderCancellation-2",
                'root_tag': "OrderCancellation",
                'customization_id': "urn:fdc:peppol.eu:poacc:trns:order_cancellation:3",
                'profile_id': "urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3",
            },
        }
        doc_type = queue_obj.document_type  # initial, balance, variation, cancel
        print('\n\n\n>>>>doc_typemainnn', doc_type)
        config = doc_type_nsmap.get(doc_type)
        print('\n\n\n>>>>doc_typemainnn', config)


        nsmap = {
            None: config['namespace'],
            'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            'xs': "http://www.w3.org/2001/XMLSchema"
        }

        # root = etree.Element(
        #     "{urn:oasis:names:specification:ubl:schema:xsd:Order-2}Order",
        #     nsmap=nsmap
        # )
        root = etree.Element(
            "{{{}}}{}".format(config['namespace'], config['root_tag']),
            nsmap=nsmap
        )

        ns = {
            "cac": "{urn:oasis:names:specification:ubl:schema:xsd:"
                   "CommonAggregateComponents-2}",
            "cbc": "{urn:oasis:names:specification:ubl:schema:xsd:"
                   "CommonBasicComponents-2}"
        }

        customization_id = etree.Element(ns['cbc'] + "CustomizationID")
        customization_id.text = config['customization_id']
        root.append(customization_id)
        profile_id = etree.Element(ns['cbc'] + "ProfileID")
        profile_id.text = config['profile_id']
        root.append(profile_id)

        document_id = etree.Element(ns['cbc'] + "ID")
        document_id.text = queue_obj.name
        root.append(document_id)

        issue_date_node = etree.Element(ns['cbc'] + "IssueDate")
        issue_date_node.text = str(issue_date.date())
        root.append(issue_date_node)
        issue_time_node = etree.Element(ns['cbc'] + "IssueTime")
        issue_time_node.text = issue_date.strftime('%H:%M:%S')
        root.append(issue_time_node)

        # order type code
        if doc_type == 'initial':
            order_type_code = etree.Element(ns['cbc'] + "OrderTypeCode")
            order_type_code.text = "220"
            root.append(order_type_code)
        if doc_type == 'balance':
            order_type_code = etree.Element(ns['cbc'] + "OrderTypeCode")
            order_type_code.text = "348"
            root.append(order_type_code)
        # sequence number id
        if doc_type == 'variation':
            seq_id = etree.SubElement(root, ns["cbc"] + "SequenceNumberID")
            seq_id.text = str(self.id)
            root.append(seq_id)
        # note
        if self.order_note and doc_type in ['variation', 'balance']:
            note = etree.SubElement(root, ns["cbc"] + "Note")
            note.text = self.order_note
            root.append(note)
        if self.order_note and doc_type == 'cancel':
            note = etree.SubElement(root, ns["cbc"] + "Note")
            note.text = str(self.notes)
            cancel_note = etree.SubElement(root, ns["cbc"] + "CancellationNote")
            cancel_note.text = self.order_note
            root.append(note)
        if self.notes and doc_type == 'initial':
            note = etree.Element(ns['cbc'] + "Note")
            note.text = str(self.notes)
            root.append(note)

        if self.order_note and doc_type in ['variation', 'balance', 'initial']:
            curr_code = etree.Element(ns['cbc'] + "DocumentCurrencyCode")
            curr_code.text = self.currency_id.name
            root.append(curr_code)

        if self.user_id and doc_type in ['balance', 'initial', 'variation']:
            cust_ref = etree.Element(ns['cbc'] + "CustomerReference")
            cust_ref.text = self.user_id.name
            root.append(cust_ref)

        # ------------ ValidityPeriod -------------
        if doc_type in ['variation', 'initial']:
            validity_period = etree.Element(ns['cac'] + "ValidityPeriod")
            validity_end_period = etree.SubElement(
                    validity_period, ns["cbc"] + "EndDate"
                )
            validity_end_period.text = str(self.date_planned.date())
            root.append(validity_period)

        # ------------ OrderReference -------------
        if doc_type in ['variation', 'cancel']:
            order_ref = etree.SubElement(root, ns["cac"] + "OrderReference")
            order_ref_id = etree.SubElement(order_ref, ns["cbc"] + "ID")
            order_ref_id.text = self.name
            root.append(order_ref)
        if doc_type in ['balance']:
            order_ref = etree.SubElement(root, ns["cac"] + "OrderDocumentReference")
            order_ref_id = etree.SubElement(order_ref, ns["cbc"] + "ID")
            order_ref_id.text = self.name
            issue_date_node = etree.SubElement(order_ref, ns['cbc'] + "IssueDate")
            issue_date_node.text = str(issue_date.date())
            root.append(order_ref)

        # ----------- AdditionalDocumentReference -----------------
        if self.company_id.embed_pdf_in_ubl_xml_order and doc_type in ['initial']:
            filename = "Order-" + self.name + ".pdf"
            docu_reference = etree.Element(
                ns["cac"] + "AdditionalDocumentReference"
            )
            docu_reference_id = etree.Element(ns["cbc"] + "ID")
            docu_reference_id.text = filename.split(".")[0]
            docu_reference.append(docu_reference_id)

            documen_type = etree.Element(ns["cbc"] + "DocumentType")
            documen_type.text = 'Order Document'
            docu_reference.append(documen_type)

            attach_node = etree.Element(ns["cac"] + "Attachment")
            binary_node = etree.Element(
                ns["cbc"] + "EmbeddedDocumentBinaryObject",
                mimeCode="application/pdf",
                filename=filename,
            )

            att_ctx = dict()
            att_ctx["no_embedded_ubl_xml"] = True
            att_ctx["force_report_rendering"] = True
            pdf_inv = (
                self.with_context(att_ctx).env.ref("purchase.action_report_purchase_order")._render_qweb_pdf(self.ids)[0]
            )
            binary_node.text = base64.b64encode(pdf_inv)

            attach_node.append(binary_node)
            docu_reference.append(attach_node)
            root.append(docu_reference)

        # ---- BuyerCustomerParty -------------------
        buyer_customer_party = etree.Element(ns["cac"] + "BuyerCustomerParty")

        buyer_company_partner = self.company_id.partner_id

        party_node = etree.Element(ns["cac"] + "Party")

        endpoint = etree.Element(ns["cbc"] + "EndpointID", schemeID=buyer_company_partner.peppol_scheme or '')
        endpoint.text = buyer_company_partner.peppol_identifier
        party_node.append(endpoint)

        if doc_type != 'balance':
            party_identification = etree.Element(ns["cac"] + "PartyIdentification")
            party_identification_id = etree.Element(ns["cbc"] + "ID", schemeID=buyer_company_partner.peppol_scheme or '')
            party_identification_id.text = buyer_company_partner.peppol_identifier
            party_identification.append(party_identification_id)
            party_node.append(party_identification)
        if doc_type != 'balance':
            party_name = etree.Element(ns["cac"] + "PartyName")
            party_name_child = etree.Element(ns["cbc"] + "Name")
            party_name_child.text = buyer_company_partner.name
            party_name.append(party_name_child)
            party_node.append(party_name)
        # postal address of buyer
        if doc_type != 'balance':
            postal_address = etree.Element(ns["cac"] + "PostalAddress")

            if buyer_company_partner.street:
                streetname = etree.SubElement(postal_address, ns["cbc"] + "StreetName")
                streetname.text = buyer_company_partner.street

            if buyer_company_partner.street2:
                addstreetname = etree.SubElement(postal_address, ns["cbc"] + "AdditionalStreetName")
                addstreetname.text = buyer_company_partner.street2

            if buyer_company_partner.city:
                city = etree.SubElement(postal_address, ns["cbc"] + "CityName")
                city.text = buyer_company_partner.city
            if buyer_company_partner.zip:
                zip_code = etree.SubElement(postal_address, ns["cbc"] + "PostalZone")
                zip_code.text = buyer_company_partner.zip
            if buyer_company_partner.state_id:
                state = etree.SubElement(postal_address, ns["cbc"] + "CountrySubentity")
                state.text = buyer_company_partner.state_id.name

            country = etree.SubElement(postal_address, ns["cac"] + "Country")
            country_identification_code = etree.SubElement(country, ns["cbc"] + "IdentificationCode")
            country_identification_code.text = 'SG'

            party_node.append(postal_address)

        party_legal_entity = etree.Element(ns["cac"] + "PartyLegalEntity")

        entity_registration_name = etree.Element(ns["cbc"] + "RegistrationName")
        entity_registration_name.text = buyer_company_partner.name
        party_legal_entity.append(entity_registration_name)
        if self.company_id.company_registry:
            entity_registration_company_id = etree.Element(ns["cbc"] + "CompanyID", schemeID=buyer_company_partner.peppol_scheme or '')
            entity_registration_company_id.text = self.company_id.company_registry
            party_legal_entity.append(entity_registration_company_id)
        # TODO: cac:PartyLegalEntity > cbc:RegistrationAddress
        party_node.append(party_legal_entity)

        if buyer_company_partner.child_ids:
            contact_obj = buyer_company_partner.child_ids.filtered(lambda x:x.type == 'contact')
            if contact_obj:
                contact_obj = contact_obj[0]
                party_contact = etree.Element(ns["cac"] + "Contact")
                contact_name = etree.Element(ns["cbc"] + "Name")
                contact_name.text = contact_obj.name
                party_contact.append(contact_name)
                if contact_obj.phone or contact_obj.mobile:
                    sender_party_contact_telephone = contact_obj.phone or contact_obj.mobile
                    contact_phone = etree.Element(ns["cbc"] + "Telephone")
                    contact_phone.text = sender_party_contact_telephone
                    party_contact.append(contact_phone)
                if contact_obj.email:
                    sender_party_contact_email = contact_obj.email
                    contact_email = etree.Element(ns["cbc"] + "ElectronicMail")
                    contact_email.text = sender_party_contact_email
                    party_contact.append(contact_email)

                party_node.append(party_contact)
        
        buyer_customer_party.append(party_node)

        # ---- SellerSupplierParty -------------
        seller_supplier_party = etree.Element(ns["cac"] + "SellerSupplierParty")

        seller_partner = self.partner_id

        party_node = etree.Element(ns["cac"] + "Party")

        endpoint = etree.Element(ns["cbc"] + "EndpointID", schemeID=seller_partner.peppol_scheme or '')
        endpoint.text = seller_partner.peppol_identifier
        party_node.append(endpoint)

        party_identification = etree.Element(ns["cac"] + "PartyIdentification")
        party_identification_id = etree.Element(ns["cbc"] + "ID", schemeID=seller_partner.peppol_scheme or '')
        party_identification_id.text = seller_partner.peppol_identifier
        party_identification.append(party_identification_id)
        party_node.append(party_identification)
        if doc_type != 'balance':
            party_name = etree.Element(ns["cac"] + "PartyName")
            party_name_child = etree.Element(ns["cbc"] + "Name")
            party_name_child.text = seller_partner.name
            party_name.append(party_name_child)
            party_node.append(party_name)

        if doc_type != 'balance':
            postal_address = etree.Element(ns["cac"] + "PostalAddress")

            if seller_partner.street:
                streetname = etree.SubElement(postal_address, ns["cbc"] + "StreetName")
                streetname.text = seller_partner.street

            if seller_partner.street2:
                addstreetname = etree.SubElement(postal_address, ns["cbc"] + "AdditionalStreetName")
                addstreetname.text = seller_partner.street2

            if seller_partner.city:
                city = etree.SubElement(postal_address, ns["cbc"] + "CityName")
                city.text = seller_partner.city
            if seller_partner.zip:
                zip_code = etree.SubElement(postal_address, ns["cbc"] + "PostalZone")
                zip_code.text = seller_partner.zip
            if seller_partner.state_id:
                state = etree.SubElement(postal_address, ns["cbc"] + "CountrySubentity")
                state.text = seller_partner.state_id.name

            country = etree.SubElement(postal_address, ns["cac"] + "Country")
            country_identification_code = etree.SubElement(country, ns["cbc"] + "IdentificationCode")
            country_identification_code.text = 'SG'

            party_node.append(postal_address)

        party_legal_entity = etree.Element(ns["cac"] + "PartyLegalEntity")

        entity_registration_name = etree.Element(ns["cbc"] + "RegistrationName")
        entity_registration_name.text = seller_partner.name
        party_legal_entity.append(entity_registration_name)

        party_node.append(party_legal_entity)

        seller_supplier_party.append(party_node)

        root.append(buyer_customer_party)
        root.append(seller_supplier_party)
        print('\n\n\n\ndoc_type', doc_type)

        # ================================
        # DELIVERY BLOCK
        # ================================
        if doc_type in ['initial', 'balance', 'variation']:
            if doc_type in ['initial', 'variation']:
                delivery = etree.SubElement(root, ns["cac"] + "Delivery")

                # Location Address
                del_loc = etree.SubElement(delivery, ns["cac"] + "DeliveryLocation")
                address = etree.SubElement(del_loc, ns["cac"] + "Address")

                for field_name, tag in [
                    ("street", "StreetName"),
                    ("street2", "AdditionalStreetName"),
                    ("city", "CityName"),
                    ("zip", "PostalZone"),
                ]:
                    value = getattr(self.partner_id, field_name, False)
                    if value:
                        node = etree.SubElement(address, ns["cbc"] + tag)
                        node.text = value

                # Country
                if self.partner_id.country_id:
                    addr_country = etree.SubElement(address, ns["cac"] + "Country")
                    ccode = etree.SubElement(addr_country, ns["cbc"] + "IdentificationCode")
                    ccode.text = self.partner_id.country_id.code or "SG"

                # Requested Delivery Period
                dlv_period = etree.SubElement(delivery, ns["cac"] + "RequestedDeliveryPeriod")
                sd = etree.SubElement(dlv_period, ns["cbc"] + "StartDate")
                ed = etree.SubElement(dlv_period, ns["cbc"] + "EndDate")
                sd.text = str(self.date_order.date())
                ed.text = str(self.date_planned.date())

                # Delivery Party
                del_party = etree.SubElement(delivery, ns["cac"] + "DeliveryParty")
                pname = etree.SubElement(del_party, ns["cac"] + "PartyName")
                pname_child = etree.SubElement(pname, ns["cbc"] + "Name")
                pname_child.text = self.partner_id.name
                # PaymentTerms
                if self.payment_term_id and doc_type in ['balance', 'initial', 'variation']:
                    payment_terms = etree.Element(ns['cac'] + "PaymentTerms")
                    payment_terms_notes = etree.SubElement(
                            payment_terms, ns["cbc"] + "Note"
                        )
                    payment_terms_notes.text = self.payment_term_id.name
                    root.append(payment_terms)

            #----cac:TaxTotal
            if doc_type != 'balance':
                tax_total = etree.Element(ns["cac"] + "TaxTotal")
                tax_amount = etree.SubElement(tax_total, ns["cbc"] + "TaxAmount", currencyID=cur_name)
                tax_amount.text = "%0.*f" % (prec, self.amount_tax)
                root.append(tax_total)

            #----cac:AnticipatedMonetaryTotal
            anticipated_total = etree.Element(ns["cac"] + "AnticipatedMonetaryTotal")
            line_ext_amount = etree.SubElement(anticipated_total, ns["cbc"] + "LineExtensionAmount", currencyID=cur_name)
            line_ext_amount.text = "%0.*f" % (prec, self.amount_untaxed)

            if doc_type != 'balance':
                line_tax_exclu_amount = etree.SubElement(anticipated_total, ns["cbc"] + "TaxExclusiveAmount", currencyID=cur_name)
                line_tax_exclu_amount.text = "%0.*f" % (prec, self.amount_untaxed)

                line_tax_exclu_amount = etree.SubElement(anticipated_total, ns["cbc"] + "TaxInclusiveAmount", currencyID=cur_name)
                line_tax_exclu_amount.text = "%0.*f" % (prec, self.amount_total)
            if doc_type == 'balance':
                payable_amount = etree.SubElement(anticipated_total, ns["cbc"] + "PayableAmount", currencyID=cur_name)
                payable_amount.text = "%0.*f" % (prec, self.amount_untaxed)
            else:
                payable_amount = etree.SubElement(anticipated_total, ns["cbc"] + "PayableAmount", currencyID=cur_name)
                payable_amount.text = "%0.*f" % (prec, self.amount_total)

            if self.partner_ref and doc_type == 'initial':
                partner_ref = etree.Element(ns['cbc'] + "SalesOrderID")
                partner_ref.text = self.partner_ref
                root.append(partner_ref)



            root.append(anticipated_total)

            #---cac:OrderLine
            dpo = self.env["decimal.precision"]
            qty_precision = dpo.precision_get("Product Unit of Measure")
            price_precision = dpo.precision_get("Product Price")
            prec = dpo.precision_get("Account")
            line_number = 0
            for iline in self.order_line:
                line_number += 1
                order_line = etree.Element(ns["cac"] + "OrderLine")
                # order line note
                if iline.name:
                    line_note = etree.SubElement(order_line, ns["cbc"] + "Note")
                    line_note.text = iline.name
                line_root = etree.SubElement(order_line, ns["cac"] + "LineItem")

                line_id = etree.SubElement(line_root, ns["cbc"] + "ID")
                line_id.text = str(line_number)
                uom_unece_code = False

                if doc_type == 'variation':
                    quantity = etree.SubElement(line_root, ns["cbc"] + "LineStatusCode")
                    quantity.text = "3"

                if iline.product_uom.unece_code:
                    uom_unece_code = iline.product_uom.unece_code
                    quantity = etree.SubElement(
                        line_root, ns["cbc"] + "Quantity", unitCode=uom_unece_code
                    )
                else:
                    quantity = etree.SubElement(line_root, ns["cbc"] + "Quantity")
                qty = iline.product_qty
                quantity.text = "%0.*f" % (qty_precision, qty)

                line_amount = etree.SubElement(
                    line_root, ns["cbc"] + "LineExtensionAmount", currencyID=cur_name
                )
                line_amount.text = "%0.*f" % (prec, iline.price_subtotal)

                price_node = etree.SubElement(line_root, ns["cac"] + "Price")
                price_amount = etree.SubElement(
                    price_node, ns["cbc"] + "PriceAmount", currencyID=cur_name
                )
                if doc_type != 'balance':
                    if iline.product_uom.unece_code:
                        base_quantity = etree.SubElement(
                            price_node, ns["cbc"] + "BaseQuantity", unitCode=uom_unece_code
                        )
                    else:
                        base_quantity = etree.SubElement(
                            price_node, ns["cbc"] + "BaseQuantity", unitCode="C62"
                        )
                    base_quantity.text = "1"

                price_unit = 0.0
                if not float_is_zero(qty, precision_digits=qty_precision):
                    price_unit = float_round(
                        iline.price_subtotal / float(qty), precision_digits=price_precision
                    )
                price_amount.text = "%0.*f" % (price_precision, price_unit)

                item = etree.SubElement(line_root, ns["cac"] + "Item")
                seller_code = iline.product_id.default_code

                if iline.name and doc_type != 'balance':
                    description = etree.SubElement(item, ns["cbc"] + "Description")
                    description.text = iline.name or iline.product_id.name
                name_node = etree.SubElement(item, ns["cbc"] + "Name")
                name_node.text = iline.product_id.name

                if seller_code:
                    seller_identification = etree.SubElement(
                        item, ns["cac"] + "SellersItemIdentification"
                    )
                    seller_identification_id = etree.SubElement(
                        seller_identification, ns["cbc"] + "ID"
                    )
                    seller_identification_id.text = seller_code

                if iline.product_id.barcode:
                    std_identification = etree.SubElement(
                        item, ns["cac"] + "StandardItemIdentification"
                    )
                    std_identification_id = etree.SubElement(
                        std_identification,
                        ns["cbc"] + "ID",
                        schemeID="0195",
                    )
                    std_identification_id.text = iline.product_id.barcode

                tax = iline.taxes_id
                if doc_type != 'balance':
                    classified_tax_category = etree.SubElement(
                        item, ns["cac"] + "ClassifiedTaxCategory"
                    )
                    classified_tax_id = etree.SubElement(
                        classified_tax_category,
                        ns["cbc"] + "ID",
                    )
                    print(tax)
                    if not tax.unece_categ_id:
                        raise ValidationError(_("Missing UNECE Tax Category on tax '%s'" % tax.name))
                    classified_tax_id.text = tax.unece_categ_id.code


                    if tax.amount_type == "percent" and not float_is_zero(tax.amount, precision_digits=prec + 3):
                        classified_tax_percent = etree.SubElement(
                            classified_tax_category,
                            ns["cbc"] + "Percent",
                        )
                        classified_tax_percent.text = str(float_round(tax.amount, precision_digits=2))
                    else:
                        classified_tax_percent = etree.SubElement(
                            classified_tax_category,
                            ns["cbc"] + "Percent",
                        )
                        classified_tax_percent.text = "0.00"
                    tax_scheme = etree.SubElement(
                        classified_tax_category, ns["cac"] + "TaxScheme"
                    )
                    tax_scheme_id = etree.SubElement(
                        tax_scheme, ns["cbc"] + "ID"
                    )
                    tax_scheme_id.text = "GST"

                root.append(order_line)
        
        xml_tree = etree.ElementTree(root)

        xml_string = etree.tostring(
            xml_tree, pretty_print=True, encoding="utf-8", xml_declaration=True
        )
        print("xml_string ===",xml_string)
        print("xml_string.decode('utf-8') == ",xml_string.decode('utf-8'))

        # with open("application_response.xml", "wb") as xml_file:
        #     xml_file.write(xml_string)

        return xml_string

    def action_send_cancel_ord_via_peppol(self):
        print('\n\nself', self)
        self.ensure_one()
        return {
            'name': _('Order Note'),
            'type': 'ir.actions.act_window',
            'res_model': 'order.reason.note.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'purchase.order',
                'active_id': self.id,
                'res_model': 'order.cancel.queue.out',
                'action_id': 'metro_einvoice_datapost.order_cancel_queue_out_action',
            },
        }
        # Queue = self.env['order.cancel.queue.out']
        # queue_ref = Queue._add_to_queue(self)
        # self.write({'outgoing_order_cancel_doc_ref': queue_ref.id})
        #
        # return {
        #     'name': self.sudo().env.ref('metro_einvoice_datapost.order_cancel_queue_out_action').name,
        #     'type': 'ir.actions.act_window',
        #     'view_mode': 'tree,form',
        #     'view_type': 'form',
        #     'res_model': 'order.cancel.queue.out',
        #     'domain': [('id', '=', queue_ref.id)]
        # }

    def action_send_orders(self):
        print('\n\nself', self)
        self.ensure_one()
        return {
            'name': _('Order Note'),
            'type': 'ir.actions.act_window',
            'res_model': 'order.reason.note.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'purchase.order',
                'active_id': self.id,
            },
        }
        # Queue = self.env['order.cancel.queue.out']
        # queue_ref = Queue._add_to_queue(self)
        # self.write({'outgoing_order_cancel_doc_ref': queue_ref.id})
        #
        # return {
        #     'name': self.sudo().env.ref('metro_einvoice_datapost.order_cancel_queue_out_action').name,
        #     'type': 'ir.actions.act_window',
        #     'view_mode': 'tree,form',
        #     'view_type': 'form',
        #     'res_model': 'order.cancel.queue.out',
        #     'domain': [('id', '=', queue_ref.id)]
        # }

    # Generate order cancel ubl xml string
    def generate_ord_cancel_ubl_xml_string(self, queue_obj=False):
        print("\ngenerate_ubl_xml_string ===", self)
        issue_date = datetime.now()
        if queue_obj:
            queue_obj.issue_date = issue_date

        cur_name = self.currency_id.name
        prec = self.currency_id.decimal_places

        nsmap = {
            None: "urn:oasis:names:specification:ubl:schema:xsd:OrderCancellation-2",
            'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            'xs': "http://www.w3.org/2001/XMLSchema"
        }

        root = etree.Element(
            "{urn:oasis:names:specification:ubl:schema:xsd:OrderCancellation-2}OrderCancellation",
            nsmap=nsmap
        )

        ns = {
            "cac": "{urn:oasis:names:specification:ubl:schema:xsd:"
                   "CommonAggregateComponents-2}",
            "cbc": "{urn:oasis:names:specification:ubl:schema:xsd:"
                   "CommonBasicComponents-2}"
        }

        customization_id = etree.Element(ns['cbc'] + "CustomizationID")
        customization_id.text = "urn:fdc:peppol.eu:poacc:trns:order_cancellation:3"
        profile_id = etree.Element(ns['cbc'] + "ProfileID")
        profile_id.text = "urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3"

        # cancel record name
        document_id = etree.Element(ns['cbc'] + "ID")
        document_id.text = self.name

        issue_date_node = etree.Element(ns['cbc'] + "IssueDate")
        issue_date_node.text = str(issue_date.date())
        issue_time_node = etree.Element(ns['cbc'] + "IssueTime")
        issue_time_node.text = issue_date.strftime('%H:%M:%S')
        # cancel reason
        cancel_note = etree.Element(ns['cbc'] + "CancellationNote")
        cancel_note.text = self.notes



        order_reference = etree.Element(ns['cac'] + "OrderReference")
        order_reference_id = etree.SubElement(
            order_reference, ns["cbc"] + "ID"
        )
        order_reference_id.text = self.name

        # ---- cac:BuyerCustomerParty
        buyer_customer_party = etree.Element(ns["cac"] + "BuyerCustomerParty")

        buyer_company_partner = self.company_id.partner_id

        party_node = etree.Element(ns["cac"] + "Party")

        endpoint = etree.Element(ns["cbc"] + "EndpointID", schemeID=buyer_company_partner.peppol_scheme or '')
        endpoint.text = buyer_company_partner.peppol_identifier

        party_node.append(endpoint)

        party_identification = etree.Element(ns["cac"] + "PartyIdentification")
        party_identification_id = etree.Element(ns["cbc"] + "ID", schemeID=buyer_company_partner.peppol_scheme or '')
        party_identification_id.text = buyer_company_partner.peppol_identifier
        party_identification.append(party_identification_id)

        party_node.append(party_identification)



        party_legal_entity = etree.Element(ns["cac"] + "PartyLegalEntity")

        entity_registration_name = etree.Element(ns["cbc"] + "RegistrationName")
        entity_registration_name.text = buyer_company_partner.name
        party_legal_entity.append(entity_registration_name)

        party_node.append(party_legal_entity)

        buyer_customer_party.append(party_node)

        # ---- cac:SellerSupplierParty
        seller_supplier_party = etree.Element(ns["cac"] + "SellerSupplierParty")

        seller_partner = self.partner_id

        party_node = etree.Element(ns["cac"] + "Party")

        endpoint = etree.Element(ns["cbc"] + "EndpointID", schemeID=seller_partner.peppol_scheme or '')
        endpoint.text = seller_partner.peppol_identifier
        party_node.append(endpoint)

        party_identification = etree.Element(ns["cac"] + "PartyIdentification")
        party_identification_id = etree.Element(ns["cbc"] + "ID", schemeID=seller_partner.peppol_scheme or '')
        party_identification_id.text = seller_partner.peppol_identifier
        party_identification.append(party_identification_id)

        party_node.append(party_identification)

        party_name = etree.Element(ns["cac"] + "PartyName")
        party_name_child = etree.Element(ns["cbc"] + "Name")
        party_name_child.text = seller_partner.name
        party_name.append(party_name_child)

        party_node.append(party_name)

        postal_address = etree.Element(ns["cac"] + "PostalAddress")

        country = etree.SubElement(postal_address, ns["cac"] + "Country")
        country_identification_code = etree.SubElement(country, ns["cbc"] + "IdentificationCode")
        country_identification_code.text = 'SG'

        party_node.append(postal_address)

        party_legal_entity = etree.Element(ns["cac"] + "PartyLegalEntity")

        entity_registration_name = etree.Element(ns["cbc"] + "RegistrationName")
        entity_registration_name.text = seller_partner.name
        party_legal_entity.append(entity_registration_name)

        party_node.append(party_legal_entity)

        seller_supplier_party.append(party_node)


        # ----------x------------
        # Append all elements to the root
        root.append(customization_id)
        root.append(profile_id)
        root.append(document_id)
        root.append(issue_date_node)
        root.append(cancel_note)
        root.append(order_reference)
        root.append(buyer_customer_party)
        root.append(seller_supplier_party)

        xml_tree = etree.ElementTree(root)

        xml_string = etree.tostring(
            xml_tree, pretty_print=True, encoding="utf-8", xml_declaration=True
        )
        print("xml_string ===", xml_string)
        print("xml_string.decode('utf-8') == ", xml_string.decode('utf-8'))

        # with open("application_response.xml", "wb") as xml_file:
        #     xml_file.write(xml_string)

        return xml_string

    def action_send_change_ord_via_peppol(self):
        print('\n\nself', self)
        self.ensure_one()
        return {
            'name': _('Order Note'),
            'type': 'ir.actions.act_window',
            'res_model': 'order.reason.note.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'purchase.order',
                'active_id': self.id,
                'res_model': 'order.change.queue.out',
                'action_id': 'metro_einvoice_datapost.order_change_queue_out_action',
            },
        }
        # Queue = self.env['order.change.queue.out']
        # queue_ref = Queue._add_to_queue(self)
        # self.write({'outgoing_order_change_doc_ref': queue_ref.id})
        #
        # return {
        #     'name': self.sudo().env.ref('metro_einvoice_datapost.order_change_queue_out_action').name,
        #     'type': 'ir.actions.act_window',
        #     'view_mode': 'tree,form',
        #     'view_type': 'form',
        #     'res_model': 'order.change.queue.out',
        #     'domain': [('id', '=', queue_ref.id)]
        # }

    def generate_ord_change_ubl_xml_string(self, queue_obj=False):
        """
        Generate PEPPOL OrderChange XML (UBL 2.1)
        """

        nsmap = {
            None: "urn:oasis:names:specification:ubl:schema:xsd:OrderChange-2",
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            "xs": "http://www.w3.org/2001/XMLSchema",
        }

        ns = {
            "cbc": "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}",
            "cac": "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}",
        }

        # =============================
        # ROOT <OrderChange>
        # =============================
        root = etree.Element(
            "{urn:oasis:names:specification:ubl:schema:xsd:OrderChange-2}OrderChange",
            nsmap=nsmap
        )

        # ------------ BASIC HEADER ---------------
        cust_id = etree.SubElement(root, ns["cbc"] + "CustomizationID")
        cust_id.text = "urn:fdc:peppol.eu:poacc:trns:order_change:3"

        profile_id = etree.SubElement(root, ns["cbc"] + "ProfileID")
        profile_id.text = "urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3"

        doc_id = etree.SubElement(root, ns["cbc"] + "ID")
        doc_id.text = "Change-" + self.name

        issue_date = etree.SubElement(root, ns["cbc"] + "IssueDate")
        issue_date.text = str(fields.Date.today())

        seq_id = etree.SubElement(root, ns["cbc"] + "SequenceNumberID")
        seq_id.text = str(self.id)

        if self.notes:
            note = etree.SubElement(root, ns["cbc"] + "Note")
            note.text = self.notes

        curr_code = etree.SubElement(root, ns["cbc"] + "DocumentCurrencyCode")
        curr_code.text = self.currency_id.name

        # ------------ ValidityPeriod -------------
        validity = etree.SubElement(root, ns["cac"] + "ValidityPeriod")
        end_date = etree.SubElement(validity, ns["cbc"] + "EndDate")
        end_date.text = str(self.date_planned.date())

        # ------------ OrderReference -------------
        order_ref = etree.SubElement(root, ns["cac"] + "OrderReference")
        order_ref_id = etree.SubElement(order_ref, ns["cbc"] + "ID")
        order_ref_id.text = self.name  # original order ID

        # =====================================================
        # BUYER CUSTOMER PARTY  (Use your own company as buyer)
        # =====================================================
        buyer = etree.SubElement(root, ns["cac"] + "BuyerCustomerParty")
        party = etree.SubElement(buyer, ns["cac"] + "Party")

        company_partner = self.company_id.partner_id

        endpoint = etree.SubElement(party, ns["cbc"] + "EndpointID", schemeID=company_partner.peppol_scheme or "")
        endpoint.text = company_partner.peppol_identifier

        party_ident = etree.SubElement(party, ns["cac"] + "PartyIdentification")
        party_ident_id = etree.SubElement(party_ident, ns["cbc"] + "ID", schemeID=company_partner.peppol_scheme or "")
        party_ident_id.text = company_partner.peppol_identifier

        party_name = etree.SubElement(party, ns["cac"] + "PartyName")
        name_child = etree.SubElement(party_name, ns["cbc"] + "Name")
        name_child.text = company_partner.name

        legal_entity = etree.SubElement(party, ns["cac"] + "PartyLegalEntity")
        reg_name = etree.SubElement(legal_entity, ns["cbc"] + "RegistrationName")
        reg_name.text = company_partner.name

        comp_id = etree.SubElement(legal_entity, ns["cbc"] + "CompanyID", schemeID=company_partner.peppol_scheme or "")
        comp_id.text = self.company_id.company_registry or ""
        # Registration Address
        reg_address = etree.SubElement(legal_entity, ns["cac"] + "RegistrationAddress")
        # City Name
        if company_partner.city:
         city_name = etree.SubElement(reg_address, ns["cbc"] + "CityName")
         city_name.text = company_partner.city
        # Country Block
        if company_partner.country_id:
            country = etree.SubElement(reg_address, ns["cac"] + "Country")
            ident_code = etree.SubElement(country, ns["cbc"] + "IdentificationCode")
            ident_code.text = company_partner.country_id.code or ""

        # Contact
        if company_partner.child_ids:
            contact = company_partner.child_ids.filtered(lambda x: x.type == 'contact')
            if contact:
                contact = contact[0]
                con = etree.SubElement(party, ns["cac"] + "Contact")
                name = etree.SubElement(con, ns["cbc"] + "Name")
                name.text = contact.name
                if contact.phone or contact.mobile:
                    sender_party_contact_telephone = contact.phone or contact.mobile
                    contact_phone = etree.Element(ns["cbc"] + "Telephone")
                    contact_phone.text = sender_party_contact_telephone
                if contact.email:
                    sender_party_contact_email = contact.email
                    contact_email = etree.Element(ns["cbc"] + "ElectronicMail")
                    contact_email.text = sender_party_contact_email

        # ================================
        # SELLER SUPPLIER PARTY
        # ================================
        seller = etree.SubElement(root, ns["cac"] + "SellerSupplierParty")
        party = etree.SubElement(seller, ns["cac"] + "Party")
        partner = self.partner_id

        endpoint = etree.SubElement(party, ns["cbc"] + "EndpointID", schemeID=partner.peppol_scheme or "")
        endpoint.text = partner.peppol_identifier

        party_ident = etree.SubElement(party, ns["cac"] + "PartyIdentification")
        party_ident_id = etree.SubElement(party_ident, ns["cbc"] + "ID")
        party_ident_id.text = partner.peppol_identifier

        # Address
        postal = etree.SubElement(party, ns["cac"] + "PostalAddress")
        if partner.street:
            st = etree.SubElement(postal, ns["cbc"] + "StreetName")
            st.text = partner.street
        if partner.street2:
            st2 = etree.SubElement(postal, ns["cbc"] + "AdditionalStreetName")
            st2.text = partner.street2
        if partner.city:
            city = etree.SubElement(postal, ns["cbc"] + "CityName")
            city.text = partner.city

        country = etree.SubElement(postal, ns["cac"] + "Country")
        cid = etree.SubElement(country, ns["cbc"] + "IdentificationCode")
        cid.text = partner.country_id.code or "SG"

        legal = etree.SubElement(party, ns["cac"] + "PartyLegalEntity")
        reg = etree.SubElement(legal, ns["cbc"] + "RegistrationName")
        reg.text = partner.name

        # ================================
        # DELIVERY BLOCK
        # ================================
        delivery = etree.SubElement(root, ns["cac"] + "Delivery")

        # Location Address
        del_loc = etree.SubElement(delivery, ns["cac"] + "DeliveryLocation")
        address = etree.SubElement(del_loc, ns["cac"] + "Address")

        for field_name, tag in [
            ("street", "StreetName"),
            ("street2", "AdditionalStreetName"),
            ("city", "CityName"),
            ("zip", "PostalZone"),
        ]:
            value = getattr(self.partner_id, field_name, False)
            if value:
                node = etree.SubElement(address, ns["cbc"] + tag)
                node.text = value

        # Country
        if self.partner_id.country_id:
            addr_country = etree.SubElement(address, ns["cac"] + "Country")
            ccode = etree.SubElement(addr_country, ns["cbc"] + "IdentificationCode")
            ccode.text = self.partner_id.country_id.code or "SG"

        # Requested Delivery Period
        dlv_period = etree.SubElement(delivery, ns["cac"] + "RequestedDeliveryPeriod")
        sd = etree.SubElement(dlv_period, ns["cbc"] + "StartDate")
        ed = etree.SubElement(dlv_period, ns["cbc"] + "EndDate")
        sd.text = str(self.date_order.date())
        ed.text = str(self.date_planned.date())

        # Delivery Party
        del_party = etree.SubElement(delivery, ns["cac"] + "DeliveryParty")
        pname = etree.SubElement(del_party, ns["cac"] + "PartyName")
        pname_child = etree.SubElement(pname, ns["cbc"] + "Name")
        pname_child.text = self.partner_id.name

        # ================================
        # TAX TOTAL + MONETARY TOTAL
        # ================================
        tax_total = etree.SubElement(root, ns["cac"] + "TaxTotal")
        tax_amount = etree.SubElement(tax_total, ns["cbc"] + "TaxAmount", currencyID=self.currency_id.name)
        tax_amount.text = str(self.amount_tax)

        total = etree.SubElement(root, ns["cac"] + "AnticipatedMonetaryTotal")
        for tag, val in [
            ("LineExtensionAmount", self.amount_untaxed),
            ("TaxExclusiveAmount", self.amount_untaxed),
            ("TaxInclusiveAmount", self.amount_total),
            ("PayableAmount", self.amount_total),
        ]:
            node = etree.SubElement(total, ns["cbc"] + tag, currencyID=self.currency_id.name)
            node.text = str(val)

        # ================================
        # ORDER LINES WITH STATUS CODE
        # ================================
        dpo = self.env["decimal.precision"]
        qty_precision = dpo.precision_get("Product Unit of Measure")
        price_precision = dpo.precision_get("Product Price")
        prec = dpo.precision_get("Account")
        line_number = 0
        for line in self.order_line:
            line_number += 1
            oline = etree.SubElement(root, ns["cac"] + "OrderLine")
            lineitem = etree.SubElement(oline, ns["cac"] + "LineItem")

            lid = etree.SubElement(lineitem, ns["cbc"] + "ID")
            lid.text = str(line_number)

            status = etree.SubElement(lineitem, ns["cbc"] + "LineStatusCode")
            status.text = "3"  # 3 = Changed

            qty = etree.SubElement(lineitem, ns["cbc"] + "Quantity", unitCode=line.product_uom.unece_code or "C62")
            qty.text = str(line.product_qty)

            ext_amount = etree.SubElement(lineitem, ns["cbc"] + "LineExtensionAmount", currencyID=self.currency_id.name)
            ext_amount.text = str(line.price_subtotal)

            # Price
            price = etree.SubElement(lineitem, ns["cac"] + "Price")
            pa = etree.SubElement(price, ns["cbc"] + "PriceAmount", currencyID=self.currency_id.name)
            # pa.text = str(line.price_unit)
            qty = line.product_qty
            price_unit = 0.0
            if not float_is_zero(qty, precision_digits=qty_precision):
                price_unit = float_round(
                    line.price_subtotal / float(qty), precision_digits=price_precision
                )
            pa.text = "%0.*f" % (price_precision, price_unit)

            # Item
            item = etree.SubElement(lineitem, ns["cac"] + "Item")
            nm = etree.SubElement(item, ns["cbc"] + "Name")
            nm.text = line.product_id.name

            # Tax category
            tax = line.taxes_id
            taxcat = etree.SubElement(item, ns["cac"] + "ClassifiedTaxCategory")
            tid = etree.SubElement(taxcat, ns["cbc"] + "ID")
            tid.text = tax.unece_categ_id.code or ""

            pct = etree.SubElement(taxcat, ns["cbc"] + "Percent")
            pct.text = str(tax.amount)

            scheme = etree.SubElement(taxcat, ns["cac"] + "TaxScheme")
            sid = etree.SubElement(scheme, ns["cbc"] + "ID")
            sid.text = "VAT"

        # FINAL XML STRING
        xml_string = etree.tostring(root, pretty_print=True, encoding="utf-8", xml_declaration=True)
        return xml_string

    def action_send_balance_ord_via_peppol(self):
        print('\n\nself', self)
        self.ensure_one()
        return {
            'name': _('Order Note'),
            'type': 'ir.actions.act_window',
            'res_model': 'order.reason.note.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'purchase.order',
                'active_id': self.id,
                'res_model': 'order.balance.queue.out',
                'action_id': 'metro_einvoice_datapost.order_balance_queue_out_action',
            },
        }
        # Queue = self.env['order.balance.queue.out']
        # queue_ref = Queue._add_to_queue(self)
        # self.write({'outgoing_order_balance_doc_ref': queue_ref.id})
        #
        # return {
        #     'name': self.sudo().env.ref('metro_einvoice_datapost.order_balance_queue_out_action').name,
        #     'type': 'ir.actions.act_window',
        #     'view_mode': 'tree,form',
        #     'view_type': 'form',
        #     'res_model': 'order.balance.queue.out',
        #     'domain': [('id', '=', queue_ref.id)]
        # }

    def generate_ord_balance_ubl_xml_string(self, queue_obj=False):
        nsmap = {
            None: "urn:oasis:names:specification:ubl:schema:xsd:Order-2",
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        }

        ns = {
            "cbc": "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}",
            "cac": "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}",
        }

        # =========================================================
        # ROOT <Order>
        # =========================================================
        root = etree.Element(
            "{urn:oasis:names:specification:ubl:schema:xsd:Order-2}Order",
            nsmap=nsmap
        )

        # BASIC HEADER
        cust_id = etree.SubElement(root, ns["cbc"] + "CustomizationID")
        cust_id.text = "urn:fdc:imda.gov.sg:trns:order_balance:1"

        profile_id = etree.SubElement(root, ns["cbc"] + "ProfileID")
        profile_id.text = "urn:fdc:imda.gov.sg:bis:order_balance:1"

        doc_id = etree.SubElement(root, ns["cbc"] + "ID")
        doc_id.text = self.name

        issue_date = etree.SubElement(root, ns["cbc"] + "IssueDate")
        issue_date.text = str(fields.Date.today())

        issue_time = etree.SubElement(root, ns["cbc"] + "IssueTime")
        issue_time.text = fields.Datetime.now().strftime("%H:%M:%S")

        order_type = etree.SubElement(root, ns["cbc"] + "OrderTypeCode")
        order_type.text = "348"  # Fixed for order balance

        note = etree.SubElement(root, ns["cbc"] + "Note")
        note.text = self.notes or ""

        currency = etree.SubElement(root, ns["cbc"] + "DocumentCurrencyCode")
        currency.text = self.currency_id.name

        if self.user_id:
            cust_ref = etree.SubElement(root, ns["cbc"] + "CustomerReference")
            cust_ref.text = self.user_id.name

        # Order Document Reference (link to original PO)
        doc_ref = etree.SubElement(root, ns["cac"] + "OrderDocumentReference")
        rid = etree.SubElement(doc_ref, ns["cbc"] + "ID")
        rid.text = self.name
        rd = etree.SubElement(doc_ref, ns["cbc"] + "IssueDate")
        rd.text = str(self.date_order.date())

        # =========================================================
        # BUYER PARTY
        # =========================================================
        buyer = etree.SubElement(root, ns["cac"] + "BuyerCustomerParty")
        party = etree.SubElement(buyer, ns["cac"] + "Party")
        buyer_company_partner = self.company_id.partner_id
        endpoint = etree.SubElement(
            party,
            ns["cbc"] + "EndpointID",
            schemeID=buyer_company_partner.peppol_scheme or ""
        )
        endpoint.text = buyer_company_partner.peppol_identifier or ""

        ple = etree.SubElement(party, ns["cac"] + "PartyLegalEntity")
        rn = etree.SubElement(ple, ns["cbc"] + "RegistrationName")
        rn.text = buyer_company_partner.name or ""

        if self.company_id.company_registry:
            cid = etree.SubElement(ple, ns["cbc"] + "CompanyID")
            cid.text = self.company_id.company_registry or ""
        if buyer_company_partner.child_ids:
            contact = buyer_company_partner.child_ids.filtered(lambda x: x.type == 'contact')
            if contact:
                contact = contact[0]
                con = etree.SubElement(party, ns["cac"] + "Contact")
                cn = etree.SubElement(con, ns["cbc"] + "Name")
                cn.text = contact.name
                if contact.phone or contact.mobile:
                    sender_party_contact_telephone = contact.phone or contact.mobile
                    contact_phone = etree.Element(ns["cbc"] + "Telephone")
                    contact_phone.text = sender_party_contact_telephone
                if contact.email:
                    sender_party_contact_email = contact.email
                    contact_email = etree.Element(ns["cbc"] + "ElectronicMail")
                    contact_email.text = sender_party_contact_email

        # =========================================================
        # SELLER PARTY
        # =========================================================
        seller = etree.SubElement(root, ns["cac"] + "SellerSupplierParty")
        party2 = etree.SubElement(seller, ns["cac"] + "Party")
        partner = self.partner_id
        endpoint2 = etree.SubElement(
            party2,
            ns["cbc"] + "EndpointID",
            schemeID=partner.peppol_scheme or ""
        )
        endpoint2.text = partner.peppol_identifier or ""

        ple2 = etree.SubElement(party2, ns["cac"] + "PartyLegalEntity")
        rn2 = etree.SubElement(ple2, ns["cbc"] + "RegistrationName")
        rn2.text = partner.name

        if partner.l10n_sg_unique_entity_number:
            cid2 = etree.SubElement(ple2, ns["cbc"] + "CompanyID")
            cid2.text = partner.l10n_sg_unique_entity_number

        con = etree.SubElement(party2, ns["cac"] + "Contact")
        cn = etree.SubElement(con, ns["cbc"] + "Name")
        cn.text = partner.name
        if partner.phone or partner.mobile:
            seller_party_contact_telephone = partner.phone or partner.mobile
            contact_phone = etree.Element(ns["cbc"] + "Telephone")
            contact_phone.text = seller_party_contact_telephone
        if partner.email:
            seller_party_contact_email = partner.email
            contact_email = etree.Element(ns["cbc"] + "ElectronicMail")
            contact_email.text = seller_party_contact_email

        # =========================================================
        # PAYMENT TERMS
        # =========================================================
        pt = etree.SubElement(root, ns["cac"] + "PaymentTerms")
        note = etree.SubElement(pt, ns["cbc"] + "Note")
        note.text = self.notes

        # =========================================================
        # TOTALS
        # =========================================================
        total = etree.SubElement(root, ns["cac"] + "AnticipatedMonetaryTotal")

        lea = etree.SubElement(total, ns["cbc"] + "LineExtensionAmount", currencyID=self.currency_id.name)
        lea.text = str(self.amount_untaxed)

        pa = etree.SubElement(total, ns["cbc"] + "PayableAmount", currencyID=self.currency_id.name)
        pa.text = str(self.amount_total)

        # =========================================================
        # ORDER LINES
        # =========================================================
        line_number = 0
        for line in self.order_line:
            line_number += 1

            oline = etree.SubElement(root, ns["cac"] + "OrderLine")

            ln = etree.SubElement(oline, ns["cbc"] + "Note")
            ln.text = line.name or ""

            li = etree.SubElement(oline, ns["cac"] + "LineItem")

            idtag = etree.SubElement(li, ns["cbc"] + "ID")
            idtag.text = str(line_number)

            qty = etree.SubElement(li, ns["cbc"] + "Quantity", unitCode=line.product_uom.unece_code or "EA")
            qty.text = str(line.product_uom_qty)

            dpo = self.env["decimal.precision"]
            qty_precision = dpo.precision_get("Product Unit of Measure")
            price_precision = dpo.precision_get("Product Price")
            prec = dpo.precision_get("Account")
            # line_amount = etree.SubElement(line_root, ns["cbc"] + "LineExtensionAmount", currencyID=cur_name
            # )
            # line_amount.text = "%0.*f" % (prec, iline.price_subtotal)

            ext = etree.SubElement(li, ns["cbc"] + "LineExtensionAmount", currencyID=self.currency_id.name)
            ext.text = "%0.*f" % (prec, line.price_subtotal)

            price = etree.SubElement(li, ns["cac"] + "Price")
            price_unit = 0.0
            qty = line.product_qty
            if not float_is_zero(qty, precision_digits=qty_precision):
                price_unit = float_round(
                    line.price_subtotal / float(qty), precision_digits=price_precision
                )
            # price_amount.text = "%0.*f" % (price_precision, price_unit)

            pa = etree.SubElement(price, ns["cbc"] + "PriceAmount", currencyID=self.currency_id.name)
            pa.text = "%0.*f" % (price_precision, price_unit)

            item = etree.SubElement(li, ns["cac"] + "Item")
            nm = etree.SubElement(item, ns["cbc"] + "Name")
            nm.text = line.product_id.name

        # =========================================================
        # FINAL XML
        # =========================================================
        xml_string = etree.tostring(root, pretty_print=True, encoding="utf-8", xml_declaration=True)
        return xml_string





