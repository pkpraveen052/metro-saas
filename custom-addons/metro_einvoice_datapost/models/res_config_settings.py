# -*- coding: utf-8 -*-
from odoo import fields, models, api
from ast import literal_eval


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    embed_pdf_in_ubl_xml_invoice = fields.Boolean(
        related="company_id.embed_pdf_in_ubl_xml_invoice", readonly=False
    )
    embed_pdf_in_ubl_xml_order = fields.Boolean(
        related="company_id.embed_pdf_in_ubl_xml_order", readonly=False
    )
    endpoint = fields.Char(string="BaseURL")
    api_version = fields.Char(string="API Version")
    api_timeout = fields.Integer(string="API Timeout")
    peppol_endpoint = fields.Char(string="API End Point")
    peppol_apikey = fields.Char(string="Bearer Token")
    electronic_address_scheme = fields.Char(string='Scheme Numerical Code', digits=4)
    electronic_address_scheme_identifier = fields.Char(string='Scheme Identifier')
    peppol_directory_search = fields.Selection([('global', 'Global'), ('sg', 'Singapore Directory')],
                                               string="Peppol Directory Search")
    grp_name_ids = fields.Many2many('res.groups', string='Incoming Invoices')
    business_register_template_id = fields.Many2one('mail.template', 'Email Template',
        domain="[('model', '=', 'res.company')]",
        config_parameter='metro_einvoice_datapost.default_peppol_resister_business_mail',
        default=lambda self: self.env.ref('metro_einvoice_datapost.peppol_business_user_registration', False))
    peppol_document_type = fields.Selection([('PINT','PINT'),('BIS','BIS')], string='Document Type')
    token_url = fields.Char(string="Token URL")
    convert_to_purchase_invoice_bill = fields.Selection(
        [('PO', 'PO'), ('Direct', 'Direct')],
        string='Convert to Purchase Invoice/Bill',
        related="company_id.convert_to_purchase_invoice_bill",
        readonly=False
    )
    is_peppol = fields.Selection([('0', '0'), ('1', '1')], string="IS Peppol")
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        purchase_admin = self.env.ref('purchase.group_purchase_manager').id
        account_admin = self.env.ref('account.group_account_manager').id
        endpoint = params.get_param('endpoint', default='https://peppol.datapost.com.sg/services/rest/peppol')
        token_url = params.get_param('token_url', default='https://peppoltest.datapost.com.sg')
        api_version = params.get_param('api_version', default='v10')
        api_timeout = params.get_param('api_timeout', default='20')
        peppol_endpoint = params.get_param('peppol_endpoint', default='https://api.peppoldirectory.sg/')
        peppol_apikey = params.get_param('peppol_apikey', default='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJnZ3ctZGlyZWN0b3J5IiwianRpIjoiZmFjMzI3YzAtNmFhYS00ZGUzLWI4NGMtNTQwNTNhMDNiMTNmIiwiYXVkIjoiZ2d3LWRpcmVjdG9yeS11c2VyIiwic3ViIjoibGlhbUBtZXRyb2dyb3VwLnNvbHV0aW9ucyIsImV4cCI6MTkzOTI4MzQ3NCwidHlwIjoiQVBJX0FDQ0VTU19UT0tFTiIsInJvbCI6WyJST0xFX0FQSSIsIlJPTEVfVVNFUiJdfQ.I7hKjUn9stMW8-7zgV0wqjowuRzUZrWtbxbKZRT_FI_5SSTb1juWqJ8tAt_3ZGi8T2qYWwFm2jNoUCFn0Ji9ZQ')
        electronic_address_scheme = params.get_param('electronic_address_scheme', default="0195")
        electronic_address_scheme_identifier = params.get_param('electronic_address_scheme_identifier',
                                                                default="SG:UEN")
        peppol_directory_search = params.get_param('peppol_directory_search', default=False)
        grp_name_ids = params.get_param('incoming_doc_email_grp_name_ids', default=False)
        business_register_template_id = params.get_param('peppol_resister_business_mail', default=self.env.ref('metro_einvoice_datapost.peppol_business_user_registration').id)
        peppol_document_type = params.get_param('peppol_document_type', default=False)
        is_peppol = params.get_param('is_peppol', default=False)

        res.update(
            endpoint=endpoint,
            token_url=token_url,
            api_version=api_version,
            api_timeout=api_timeout,
            peppol_endpoint=peppol_endpoint,
            peppol_apikey=peppol_apikey,
            electronic_address_scheme=electronic_address_scheme,
            electronic_address_scheme_identifier=electronic_address_scheme_identifier,
            peppol_directory_search=peppol_directory_search,
            grp_name_ids=[(6, 0, [purchase_admin, account_admin])] if not grp_name_ids else [
                (6, 0, literal_eval(grp_name_ids))],
            peppol_document_type=peppol_document_type,
            is_peppol=is_peppol
            # business_register_template_id=business_register_template_id
        )
        return res

    @api.model
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("token_url", self.token_url)
        self.env['ir.config_parameter'].sudo().set_param("endpoint", self.endpoint)
        self.env['ir.config_parameter'].sudo().set_param("api_version", self.api_version)
        self.env['ir.config_parameter'].sudo().set_param("api_timeout", self.api_timeout)
        self.env['ir.config_parameter'].sudo().set_param("peppol_endpoint", self.peppol_endpoint)
        self.env['ir.config_parameter'].sudo().set_param("peppol_apikey", self.peppol_apikey)
        self.env['ir.config_parameter'].sudo().set_param("electronic_address_scheme", self.electronic_address_scheme)
        self.env['ir.config_parameter'].sudo().set_param("electronic_address_scheme_identifier",
                                                         self.electronic_address_scheme_identifier)
        self.env['ir.config_parameter'].sudo().set_param("peppol_directory_search", self.peppol_directory_search)
        self.env['ir.config_parameter'].sudo().set_param("incoming_doc_email_grp_name_ids", self.grp_name_ids.ids)
        # self.env['ir.config_parameter'].sudo().set_param("peppol_resister_business_mail", self.business_register_template_id.id)
        self.env['ir.config_parameter'].sudo().set_param("peppol_document_type", self.peppol_document_type)
        self.env['ir.config_parameter'].sudo().set_param("is_peppol", self.is_peppol)
