# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gemini_api_key = fields.Char(
        string="Google Gemini API Key"
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        gemini_api_key = params.get_param('gemini_api_key',
                                                 default=False)
        res.update(gemini_api_key=gemini_api_key)
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            "gemini_api_key",
            self.gemini_api_key)


# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     ocr_total_mismatch = fields.Boolean(string="Ocr Total Mismatch", default=False)
#
#     @api.onchange('ocr_total_mismatch')
#     def _onchange_ocr_warning(self):
#         if self.ocr_total_mismatch:
#             return {
#                 'warning': {
#                     'title': "OCR Imported",
#                     'message': "This bill was created using OCR. Please verify the extracted values carefully.",
#                 }
#             }