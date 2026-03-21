from odoo import fields, models, api
from ast import literal_eval

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    corppass_auth_endpoint = fields.Char(string="CorpPassAuth End Point")
    corppass_token_endpoint = fields.Char(string="CorpPassToken End Point")
    searchgst_registered_endpoint = fields.Char(string="Search GST Registered End Point")
    gstreturns_f5f8_endpoint = fields.Char(string="GST Returns F5 &F8 End Point")
    gstreturns_f7_endpoint = fields.Char(string="GST Returns F7 End Point")
    iras_apikey = fields.Char(string="IRAS API Key")
    iras_apisecret = fields.Char(string="IRAS API Secret")
    corppass_callback_url = fields.Char(string='CorpPass Callback URL')
    tax_agent = fields.Boolean('IRAS Tax Agent')
    target_moves = fields.Selection([('posted', "All Posted Entries"), ('all', "All Entries")], related="company_id.target_moves", string='Target moves',readonly=False)
    target_moves_f7 = fields.Selection([('posted', "All Posted Entries"), ('all', "All Entries")], related="company_id.target_moves_f7",string='Target moves',readonly=False)
    cit_prefill_endpoint = fields.Char(string="CIT Pre-Fill End Point")
    cit_conversion_endpoint = fields.Char(string="CIT Conversion End Point")
    cs_submission_endpoint = fields.Char(string="Form C-S End Point")
    uenType = fields.Selection([('6', 'ROC'), ('35', 'UENO'), ('8', 'ASGD'), ('10', 'ITR')], related="company_id.uenType",string="UEN Type",readonly=False)    
    target_moves_formcs = fields.Selection(
        [('posted', "All Posted Entries"), ('all', "All Entries")],related="company_id.target_moves_formcs",string='Target moves',readonly=False)
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()

        corppass_auth_endpoint = params.get_param('corppass_auth_endpoint', default='https://apiservices.iras.gov.sg/iras/prod/Authentication/CorpPassAuth')
        corppass_token_endpoint = params.get_param('corppass_token_endpoint', default='https://apiservices.iras.gov.sg/iras/prod/Authentication/CorpPassToken')
        searchgst_registered_endpoint = params.get_param('searchgst_registered_endpoint', default='https://apiservices.iras.gov.sg/iras/prod/GSTListing/SearchGSTRegistered')
        gstreturns_f5f8_endpoint = params.get_param('gstreturns_f5f8_endpoint', default='https://apiservices.iras.gov.sg/iras/prod/gst/submitF5F8ReturnCorpPass')
        gstreturns_f7_endpoint = params.get_param('gstreturns_f7_endpoint', default='https://apiservices.iras.gov.sg/iras/prod/gst/submitF7ReturnCorpPass')
        iras_apikey = params.get_param('iras_apikey', default='986d8c0514987952a31ce5472c945898')
        iras_apisecret = params.get_param('iras_apisecret', default='f00d5d959ea96f976d720853f25b5c1b')
        corppass_callback_url = params.get_param('corppass_callback_url', default='https://metrogroup.solutions/iras/corppass')
        tax_agent = params.get_param('tax_agent', default=False)
        cit_prefill_endpoint = params.get_param('cit_prefill_endpoint', default='https://apiservices.iras.gov.sg/iras/prod/ct/svcprefillformcs')
        cit_conversion_endpoint = params.get_param('cit_conversion_endpoint', default='https://apiservices.iras.gov.sg/iras/prod/ct/convertformcs')
        cs_submission_endpoint = params.get_param('cs_submission_endpoint', default='https://apiservices.iras.gov.sg/iras/prod/ct/submitformcs')

        res.update(
            corppass_auth_endpoint=corppass_auth_endpoint,
            corppass_token_endpoint=corppass_token_endpoint,
            searchgst_registered_endpoint=searchgst_registered_endpoint,
            gstreturns_f5f8_endpoint=gstreturns_f5f8_endpoint,
            gstreturns_f7_endpoint=gstreturns_f7_endpoint,
            iras_apisecret=iras_apisecret,
            iras_apikey=iras_apikey,
            corppass_callback_url=corppass_callback_url,
            tax_agent=tax_agent,
            cit_prefill_endpoint=cit_prefill_endpoint,
            cit_conversion_endpoint=cit_conversion_endpoint,
            cs_submission_endpoint=cs_submission_endpoint)
        return res

    @api.model
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("corppass_auth_endpoint", self.corppass_auth_endpoint)
        self.env['ir.config_parameter'].sudo().set_param("corppass_token_endpoint", self.corppass_token_endpoint)
        self.env['ir.config_parameter'].sudo().set_param("searchgst_registered_endpoint", self.searchgst_registered_endpoint)
        self.env['ir.config_parameter'].sudo().set_param("gstreturns_f5f8_endpoint", self.gstreturns_f5f8_endpoint)
        self.env['ir.config_parameter'].sudo().set_param("gstreturns_f7_endpoint", self.gstreturns_f7_endpoint)
        self.env['ir.config_parameter'].sudo().set_param("iras_apikey", self.iras_apikey)
        self.env['ir.config_parameter'].sudo().set_param("iras_apisecret", self.iras_apisecret)
        self.env['ir.config_parameter'].sudo().set_param("corppass_callback_url", self.corppass_callback_url)
        self.env['ir.config_parameter'].sudo().set_param("tax_agent", self.tax_agent)
        self.env['ir.config_parameter'].sudo().set_param("cit_prefill_endpoint", self.cit_prefill_endpoint)
        self.env['ir.config_parameter'].sudo().set_param("cit_conversion_endpoint", self.cit_conversion_endpoint)
        self.env['ir.config_parameter'].sudo().set_param("cs_submission_endpoint", self.cs_submission_endpoint)


    
    def install_chart_of_account(self):
        result = super(ResConfigSettings, self).install_chart_of_account()
        self.company_id.map_iras_fields_to_accounts()
        return result