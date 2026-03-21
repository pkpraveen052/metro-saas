# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo import tools
from . import peppol_queue_out
from . import peppol_log_sg
import logging

logger = logging.getLogger(__name__)


class PeppolInvoiceReport(models.Model):
    _name = 'peppol.invoice.report'
    _auto = False
    _description = "Peppol Document Analysis Report"
    partner_id = fields.Many2one('res.partner')
    date = fields.Datetime(string="Date")
    type = fields.Selection(selection=[('incoming', 'Incoming'), ('outgoing', 'Outgoing')], string='Invoice Type')
    invname = fields.Char(string="Name")
    status = fields.Selection(
        peppol_queue_out.SELECTION_PEPPOL_QUEUE_OUT_STATE + peppol_log_sg.SELECTION_PEPPOL_LOG_SG_STATE,
        string="Status")
    # status = fields.Char(string="Status")
    partner_name = fields.Char(string="Partner Name")
    company_id = fields.Many2one('res.company', string="Company")

    # @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'peppol_invoice_report')
        # fectching the data nased on account move model
        # self._cr.execute("""
        #     CREATE OR REPLACE VIEW peppol_invoice_report AS (
        #
        #         SELECT row_number() OVER () AS id, line.invname, line.partner_id,
        #         line.date, line.type ,line.status ,line.company FROM (
        #
        #             SELECT
        #             am.name as invname,
        #             am.partner_id ,
        #             pqo.create_date as date,
        #             'outgoing' as type,
        #             pqo.state as status,
        #             pqo.company_id as Company
        #             FROM peppol_queue_out pqo
        #             LEFT JOIN account_move am ON (am.id = pqo.invoice_id)
        #
        #             UNION ALL
        #
        #             SELECT am.name as invoice_no,
        #             am.partner_id ,
        #             pls.create_date as date,
        #             'incoming' as type,
        #             pls.subtype as status,
        #             pls.company_id as Company
        #             FROM peppol_log_sg as pls
        #             LEFT JOIN account_move am ON (am.id = CAST(pls.invoice_no AS INT))
        #
        #         ) line
        #
        #     )""")
        self._cr.execute("""
            CREATE OR REPLACE VIEW peppol_invoice_report AS (

                SELECT row_number() OVER () AS id, line.invname, line.partner_name,
                line.date, line.type ,line.status ,line.company_id FROM (

                    SELECT
                    rp.name as invname,
                    rp.name as partner_name,
                    pqo.create_date as date,
                    'outgoing' as type,
                    pqo.state as status,
                    pqo.company_id as company_id
                    FROM peppol_queue_out pqo
                    LEFT JOIN res_partner rp ON (rp.id = pqo.partner_id)

                    UNION ALL

                    SELECT invoice_no as invname,
                    sender_party_name as partner_name,
                    create_date as date,
                    'incoming' as type,
                    subtype as status,
                    company_id as company_id
                    FROM peppol_log_sg as pls

                ) line

            )""")
