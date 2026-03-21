from odoo import api, fields, models

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    active = fields.Boolean(related="product_id.active")

   