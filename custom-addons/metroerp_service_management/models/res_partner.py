# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _



class Res_Partner(models.Model):
    _inherit = 'res.partner'

    service_request_ids = fields.One2many('service.management', 'partner_id', 'Services Request')