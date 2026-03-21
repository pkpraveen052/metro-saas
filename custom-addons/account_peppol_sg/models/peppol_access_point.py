# -*- coding: utf-8 -*-
import base64
import logging

from odoo import api, fields, models, _

logger = logging.getLogger(__name__)


class PeppolAccessPointSG(models.Model):
    _name = "peppol.access.point.sg"
    _description = "Access Point Configuration"
    _inherit = "mail.thread"
    _rec_name = "company_id"

    authorization_key = fields.Char(string='API Key', required=True)
    endpoint = fields.Char(string='BaseURL', required=True)
    note = fields.Text(string='Note')
    company_id = fields.Many2one('res.company', string='Company', required=True)
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        (
            'company_id',
            'unique(company_id)',
            "Company must be unique!.",
        ),
    ]

    @api.model
    def default_get(self, fields):
        res = super(PeppolAccessPointSG, self).default_get(fields)
        res['endpoint'] = self.env['ir.config_parameter'].sudo().get_param('endpoint') or False
        return res
