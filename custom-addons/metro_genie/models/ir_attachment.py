from odoo import models, fields, api


class AttachmentFile(models.Model):
    _inherit = 'ir.attachment'

    is_export = fields.Boolean(string="Export", default=False)
    group_ids = fields.Many2many('res.groups', string='Allowed Groups')
