# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class ResCompany(models.Model):
    _inherit = "res.company"

    carbonate_token = fields.Char(string="Token")
    enable_carbonate_sync = fields.Boolean(string="Enable Carbonate Sync")