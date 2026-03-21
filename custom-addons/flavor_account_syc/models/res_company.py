# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class ResCompany(models.Model):
    _inherit = "res.company"

    flavor_apikey = fields.Char(string="API Key", size=16, readonly=True)
    flavor_apisecret = fields.Char(string="API Secret", size=32, readonly=True)
    enable_flavor_sync = fields.Boolean(string="Enable Flavor Sync")