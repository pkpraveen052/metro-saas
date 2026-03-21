# -*- coding: utf-8 -*-
from odoo import api, models, fields, _

class IncomingFailedLogs(models.Model):
    _name = "incoming.failed.logs"
    _description = "Incoming Cron Failed Logs"
    _order = "create_date desc"

    status_code = fields.Char(string="Status Code", default='None')
    response_body = fields.Text(string="Response Body")
    error_body = fields.Text(string="Error Body")
    traceback_body = fields.Text(string="Traceback Body")
    doc_type = fields.Selection([
        ('invoices', 'Invoices'),
        ('credit-notes', 'Credit Notes'),
        ('orders', 'Orders'),
        ('invoice-responses','Invoice Responses')], string='Type')

