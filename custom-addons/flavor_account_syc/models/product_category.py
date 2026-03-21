from odoo import _, api, fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    company_id = fields.Many2one(comodel_name="res.company", string="Company")