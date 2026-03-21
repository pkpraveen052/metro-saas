# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests
import json
import logging
import re
import random
from odoo.addons.base.models.ir_mail_server import MailDeliveryException

class ResCompany(models.Model):
    _inherit = 'res.company'

    def get_peppol_scheme(self):
        peppol_scheme = self.env['ir.config_parameter'].sudo().get_param('electronic_address_scheme', False)
        return peppol_scheme

    embed_pdf_in_ubl_xml_invoice = fields.Boolean(
        string="Embed PDF in UBL XML Invoice",
        help="If active, the standalone UBL Invoice XML file will include the "
             "PDF of the invoice in base64 under the node "
             "'AdditionalDocumentReference'. For example, to be compliant with the "
             "e-fff standard used in Belgium, you should activate this option.",
         default=True
    )
    embed_pdf_in_ubl_xml_order = fields.Boolean(
        string="Embed PDF in UBL XML Order",
        help="If active, the standalone UBL Order XML file will include the "
             "PDF of the invoice in base64 under the node "
             "'AdditionalDocumentReference'. For example, to be compliant with the "
             "e-fff standard used in Belgium, you should activate this option.",
         default=True
    )
    peppol_identifier = fields.Char(string='Peppol Identifer', size=64, copy=False)
    peppol_scheme = fields.Char(string='Peppol Scheme', size=64, default=get_peppol_scheme, copy=False)
    peppol_superscheme = fields.Char(string='Peppol Superscheme', default='iso6523-actorid-upis', copy=False)
    register_email_sent = fields.Boolean('Register Email Sent')
    peppol_document_type = fields.Selection([('PINT','PINT'),('BIS','BIS')], string='Document Type', default='PINT')
    convert_to_purchase_invoice_bill = fields.Selection([('PO','PO'),('Direct','Direct')], default='Direct', string='Convert to Purchase Invoice/Bill')


    @api.model
    def create(self, vals):
        """overridden for updating the peppol Identifier with UEN  while creating record"""
        if vals.get("l10n_sg_unique_entity_number"):
            vals['peppol_identifier'] = "SGUEN" + vals.get("l10n_sg_unique_entity_number")
        return super(ResCompany, self).create(vals)

    @api.onchange('peppol_identifier')
    def peppol_identifier_onchange(self):
        """ this method to show the update peppol identifier button by setting boolean field"""
        if self.peppol_identifier:
            self.peppol_identifier = self.peppol_identifier.upper()

    def write(self, values):
        """overridden for updating  the peppol Identifier and UEN changes"""
        if values.get("l10n_sg_unique_entity_number"):
            values['peppol_identifier'] = "SGUEN" + values.get("l10n_sg_unique_entity_number")
        return super(ResCompany, self).write(values)

    def register_in_peppol(self):
        """ This will send an Email to the recipent. """
        mail_server = self.env['ir.mail_server'].search([], limit=1, order="sequence")
        if not mail_server:
            raise UserError("Outgoing Mail Server is not configured.")
        else:
            try:
                smtp_session = self.env['ir.mail_server'].connect(mail_server_id=mail_server.id)
            except Exception as exc:
                raise MailDeliveryException(_('Unable to connect to SMTP Server'), exc)
        template_id = self.env['ir.config_parameter'].sudo().get_param('metro_einvoice_datapost.default_peppol_resister_business_mail', default=self.env.ref('metro_einvoice_datapost.peppol_business_user_registration').id)
        template_obj = self.env['mail.template'].browse(int(template_id))
        template_obj.send_mail(self.id, force_send=False)
        flag = self.write({'register_email_sent': True})
        if flag:
            action = self.sudo().env.ref('metro_einvoice_datapost.action_peppol_warning_wizard').read()[0]
            action.update({
                'name': 'Performed Action Succeeded',
                'context': {
                    'default_message': 'Mail sent successfully!',
                }
            })
            return action
               
