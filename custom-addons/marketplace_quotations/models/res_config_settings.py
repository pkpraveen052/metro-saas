from odoo import models,fields,api,_


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    market_place_order_notify_ids = fields.Many2many("res.users", related="company_id.market_place_order_notify_ids", string="Market Place Order Notify", readonly=False)
    auto_invoice = fields.Boolean(string="Auto Invoice",config_parameter='base_setup.auto_invoice')