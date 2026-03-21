# -*- coding: utf-8 -*-
from odoo import fields, models, api
from ast import literal_eval


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    embed_pdf_in_ubl_xml_invoice = fields.Boolean(
        related="company_id.embed_pdf_in_ubl_xml_invoice", readonly=False
    )
    endpoint = fields.Char(string="API End Point")
    apikey = fields.Char(string="Bearer Token")
    peppol_endpoint = fields.Char(string="API End Point")
    peppol_apikey = fields.Char(string="Bearer Token")
    electronic_address_scheme = fields.Char(string='Scheme Numerical Code', digits=4)
    electronic_address_scheme_identifier = fields.Char(string='Scheme Identifier')
    peppol_directory_search = fields.Selection([('global', 'Global'), ('sg', 'Singapore Directory')],
                                               string="Peppol Directory Search")
    grp_name_ids = fields.Many2many('res.groups', string='Incoming Invoices')
    invoice_type = fields.Selection([('UBL', 'UBL'), ('JSON', 'JSON')],
                                    string="Invoice Type")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        purchase_admin = self.env.ref('purchase.group_purchase_manager').id
        account_admin = self.env.ref('account.group_account_manager').id
        endpoint = params.get_param('endpoint', default='https://api.storecove.com/api/v2/')
        apikey = params.get_param('apikey', default=False)
        peppol_endpoint = params.get_param('peppol_endpoint', default='https://api.peppoldirectory.sg/')
        peppol_apikey = params.get_param('peppol_apikey', default=False)
        electronic_address_scheme = params.get_param('electronic_address_scheme', default="0195")
        electronic_address_scheme_identifier = params.get_param('electronic_address_scheme_identifier', default="SG:UEN")
        peppol_directory_search = params.get_param('peppol_directory_search', default=False)
        grp_name_ids = params.get_param('peppol_notification_grp_ids', default=False)
        invoice_type = params.get_param('settings_invoice_type', default='UBL')
        res.update(
            endpoint=endpoint,
            apikey=apikey,
            peppol_endpoint=peppol_endpoint,
            peppol_apikey=peppol_apikey,
            electronic_address_scheme=electronic_address_scheme,
            electronic_address_scheme_identifier=electronic_address_scheme_identifier,
            peppol_directory_search=peppol_directory_search,
            grp_name_ids=[(6, 0, [purchase_admin, account_admin])] if not grp_name_ids else [
                (6, 0, literal_eval(grp_name_ids))],
            invoice_type=invoice_type,
        )
        return res

    @api.model
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("endpoint", self.endpoint)
        self.env['ir.config_parameter'].sudo().set_param("apikey", self.apikey)
        self.env['ir.config_parameter'].sudo().set_param("peppol_endpoint", self.peppol_endpoint)
        self.env['ir.config_parameter'].sudo().set_param("peppol_apikey", self.peppol_apikey)
        self.env['ir.config_parameter'].sudo().set_param("electronic_address_scheme", self.electronic_address_scheme)
        self.env['ir.config_parameter'].sudo().set_param("electronic_address_scheme_identifier", self.electronic_address_scheme_identifier)
        self.env['ir.config_parameter'].sudo().set_param("peppol_directory_search", self.peppol_directory_search)
        self.env['ir.config_parameter'].sudo().set_param("peppol_notification_grp_ids", self.grp_name_ids.ids)
        self.env['ir.config_parameter'].sudo().set_param("settings_invoice_type", self.invoice_type)
