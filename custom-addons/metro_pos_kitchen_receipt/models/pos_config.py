from odoo import models,fields,api,_

class PosConfig(models.Model):
    _inherit = 'pos.config'

    enable_kitchen_receipt = fields.Boolean(string="Enable Kitchen Receipt", default=False)