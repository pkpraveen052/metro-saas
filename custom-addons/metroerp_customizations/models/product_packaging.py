from odoo import models,fields,_,api


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    @api.model
    def default_get(self, fields):
        rec = super(ProductPackaging, self).default_get(fields)
        rec['company_id'] = self.env.company.id
        return rec