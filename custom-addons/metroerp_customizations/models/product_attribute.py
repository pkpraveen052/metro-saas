from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.onchange('company_id')
    def company_id_onchange(self):
        if (self.company_id.id != self.env.company.id) and self.company_id:
            raise ValidationError("You can only set the company '%s' for this Attribute." % self.env.company.name)

