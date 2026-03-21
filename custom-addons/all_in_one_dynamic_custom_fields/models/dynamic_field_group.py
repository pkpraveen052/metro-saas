from odoo import fields,models

class DynamicFieldGroup(models.Model):
    _name = 'dynamic.field.group'
    _description = 'Dynamic Field Group'

    name = fields.Char(string='Group Name', required=True)
    group_string = fields.Char(string='Group String', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    model_id = fields.Many2one('ir.model', string='Model')
    template_id = fields.Many2one('service.template', string='Service Template', required=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
