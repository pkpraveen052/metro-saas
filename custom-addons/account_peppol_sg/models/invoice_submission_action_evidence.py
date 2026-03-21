# -*- coding: utf-8 -*-
from odoo import api, models, fields, _


class InvoiceSubmissionActionEvidence(models.Model):
    _name = "invoice.submission.action.evidence"
    _description = "Invoice Submission Action Evidence"

    message_id = fields.Char("Message ID")
    receiving_accesspoint = fields.Char("Receiving Access Point")
    remote_mta_ip = fields.Char("Remote MTA IP")
    reporting_mta = fields.Char("Reporting MTA")
    smtp_response = fields.Text("SMTP Response")
    timestamp = fields.Char("Timestamp")
    transmission_id = fields.Char("Transmission ID")
    xml = fields.Text("XML")
    queue_id = fields.Many2one("Outgoing Document")
