from odoo import models,fields,api,_

class ResCompany(models.Model):
    _inherit = 'res.company'

    market_place_order_notify_ids = fields.Many2many("res.users",string="Market Place Order Notify")