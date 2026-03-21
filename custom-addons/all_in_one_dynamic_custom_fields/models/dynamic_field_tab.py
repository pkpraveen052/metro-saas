from odoo import fields,models

class DynamicFieldTab(models.Model):
    _name = 'dynamic.field.tab'
    _description = 'Dynamic Field Tab'

    name = fields.Char(string='Tab Name', required=True)
    tab_string = fields.Char(string='Tab String', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    model_id = fields.Many2one('ir.model', string='Model')
