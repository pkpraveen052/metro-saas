from odoo import api, fields, models

class ProductChangeType(models.TransientModel):
    _name = "product.change.type"
    _description = "Product Change Type"

    type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product')
    ], string="Product Type", required=True, default="consu")

    @api.model
    def default_get(self, fields_list):
        defaults = super(ProductChangeType, self).default_get(fields_list)
        active_id = self.env.context.get("active_id", False)
        active_model = self.env.context.get("active_model", False)
        if active_id and active_model == 'product.template':
            product = self.env["product.template"].browse(active_id)
            defaults["type"] = product.type
        elif active_id and active_model == 'product.product':
            product = self.env["product.product"].browse(active_id)
            defaults["type"] = product.product_tmpl_id.type
        return defaults

    def do_change(self):
        active_id = self.env.context.get("active_id", False)
        active_model = self.env.context.get("active_model", False)

        # Fetch the product template and variants
        if active_id and active_model == 'product.template':
            product = self.env["product.template"].browse(active_id)
        elif active_id and active_model == 'product.product':
            variants = self.env["product.product"].browse(active_id)
            product = variants.product_tmpl_id

        # Updating the `type` field in `product.template`
        query_dic = {"id": product.id, "type": self.type}
        query = "UPDATE product_template SET type = %(type)s WHERE id = %(id)s"
        self._cr.execute(query, query_dic)

        # We are not updating the `type` field for product variants
        # The `product_product` table does not have a `type` field; it inherits from `product_template`

        return True
