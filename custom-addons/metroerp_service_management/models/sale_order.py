from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    service_id = fields.Many2one('service.management', string='Service Management')