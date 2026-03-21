# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockMoveLive(models.Model):
    _inherit = 'stock.move.line'

    partner_id = fields.Many2one(string='Customer/Vendor', related='picking_id.partner_id', store=True)
