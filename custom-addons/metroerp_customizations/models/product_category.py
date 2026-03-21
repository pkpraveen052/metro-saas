from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductCategory(models.Model):
    _inherit = "product.category"
    #_check_company_auto = True

    company_id = fields.Many2one(comodel_name="res.company", string="Company")

    @api.model
    def default_get(self, fields):
        defaults = super(ProductCategory, self).default_get(fields)
        # Access the current company
        current_company = self.env.company.id
        # Set the current company as the default company in the product category
        defaults['company_id'] = current_company
        return defaults

    @api.constrains("company_id")
    def check_current_company(self):
        context = dict(self._context or {})
        if not context.get('from_company_create'):
            for record in self:
                if (record.company_id and record.company_id.id != record.env.company.id):
                    raise UserError(_("The product category's company must be same as current company."))

