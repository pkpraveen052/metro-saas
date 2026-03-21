from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    service_id = fields.Many2one('service.management', string='Service Management')