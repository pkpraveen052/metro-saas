# -*- coding: utf-8 -*-
from odoo import api, models, fields, _

class InvoiceOcrLogs(models.Model):
    _name = "invoice.ocr.logs"
    _description = "Invoice Ocr Logs"
    _order = "create_date desc"


    token_id = fields.Char(string="Token Used")
    json_response = fields.Text(string="Response Body")
    message = fields.Text(string="Message")
    company_id = fields.Many2one(comodel_name='res.company', string='Company')



class AccountMove(models.Model):
    _inherit = 'account.move'

    is_ocr_created = fields.Boolean("Created via OCR", default=False)