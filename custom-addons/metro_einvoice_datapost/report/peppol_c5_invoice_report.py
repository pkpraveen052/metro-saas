# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo import tools
from ..models import peppol_queue_out
from ..models import peppol_queue_in
import logging

logger = logging.getLogger(__name__)


class PeppolC5InvoiceReport(models.Model):
    _name = 'peppol.c5.invoice.report'
    _auto = False
    _description = "GST InvoiceNow Analysis Report"

    # partner_id = fields.Many2one('res.partner')
    date = fields.Datetime(string="Date")
    type = fields.Selection(selection=[('incoming', 'Incoming'), ('outgoing', 'Outgoing')], string='Type')
    doc_name = fields.Char(string="Doc No")
    status = fields.Selection(
        peppol_queue_out.SELECTION_PEPPOL_QUEUE_OUT_STATE,
        string="State")
    partner_id = fields.Many2one('res.partner', string="Partner Name")
    company_id = fields.Many2one('res.company', string="Company")
    iras_transmission_id = fields.Char(string="IRAS Transmission ID")
    iras_acknowledgement_id = fields.Char(string="IRAS Acknowledgement ID")
    iras_status = fields.Char(string="IRAS Status")
    created_by = fields.Many2one('res.users', string="Created By")
    source = fields.Char(string="Source")
    sender_id = fields.Char(string="Sender ID")
    receiver_id = fields.Char(string="Receiver ID")
    peppol_document_type = fields.Selection([('PINT','PINT'), ('BIS', 'BIS')], string="Peppol Document Type")
    client_ref = fields.Char('Client Ref')
    server_receipt = fields.Char('Server Receipt')
    invoice_type = fields.Selection(selection=[
        ('out_invoice', 'Invoice'),
        ('out_refund', 'Credit Note'),
        ('in_invoice', 'Vendor Bill'),
        ('in_refund', 'Vendor Credit Note'),
    ], string='Invoice Type') 

    def init(self):
        """Initialize the SQL view with UNION ALL, filtered by current user's company_id."""
        tools.drop_view_if_exists(self.env.cr, self._table)

        # company_id = self.env.company.id

        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () as id,
                    a.create_date as date,
                    'outgoing' as type,
                    a.name as doc_name,
                    a.state as status,
                    a.partner_id as partner_id,
                    a.company_id as company_id,
                    a.iras_transmission_id as iras_transmission_id,
                    a.iras_acknowledgement_id as iras_acknowledgement_id,
                    a.iras_status as iras_status,
                    a.create_uid as created_by,
                    a.extracted_senderid as sender_id,
                    a.extracted_receiverid as receiver_id,
                    'Queue Out' as source,
                    a.peppol_document_type as peppol_document_type,
                    a.invoice_type as invoice_type,
                    a.server_receipt as server_receipt,
                    a.client_ref as client_ref
                FROM peppol_queue_out a

                UNION ALL

                SELECT
                    row_number() OVER () + (SELECT COUNT(*) FROM peppol_queue_out) as id,
                    b.create_date as date,
                    'outgoing' as type,
                    b.name as doc_name,
                    b.state as status,
                    b.partner_id as partner_id,
                    b.company_id as company_id,
                    b.extracted_transmissionid as iras_transmission_id,
                    b.extracted_acknowledgementid as iras_acknowledgement_id,
                    b.iras_status as iras_status,
                    b.create_uid as created_by,
                    b.extracted_senderid as sender_id,
                    b.extracted_receiverid as receiver_id,
                    'Queue C5 Out' as source,
                    b.peppol_document_type as peppol_document_type,
                    b.invoice_type as invoice_type,
                    b.server_receipt as server_receipt,
                    b.client_ref as client_ref
                FROM peppol_queue_c5_out b
            )
        """)