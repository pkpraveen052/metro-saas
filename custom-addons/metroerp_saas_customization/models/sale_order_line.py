from odoo import models, api,_,fields
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create(self, vals):
        order = super().create(vals)
        try:
            order._update_brs_sale()
        except Exception:
            pass
        return order

    def write(self, vals):
        res = super().write(vals)
        try:
            self._update_brs_sale()
        except Exception:
            pass
        return res

    def _update_brs_sale(self):
        """Ensure BRS deposit line is added/updated/removed on sale order."""
        if self.env.context.get('skip_brs_update'):
            return

        for order in self:
            company = order.company_id
            brs_product = company.brs_deposit_product_id

            if not brs_product:
                continue

            # deposit trigger products except main BRS product
            deposit_lines = order.order_line.filtered(
                lambda l: l.product_id
                and l.product_id.is_brs_deposit
                and l.product_id.id != brs_product.id
            )

            # compute total amount
            total_amount = sum(
                (l.product_id.brs_deposit_amount or 0.0) *
                (l.product_uom_qty or 0.0)
                for l in deposit_lines
            )

            # existing BRS deposit line
            existing_brs = order.order_line.filtered(
                lambda l: l.product_id.id == brs_product.id
            )

            # CASE 1 — No deposit products → remove BRS line
            if abs(total_amount) < 0.0001:
                if existing_brs:
                    try:
                        existing_brs.with_context(skip_brs_update=True).unlink()
                    except Exception:
                        pass
                continue

            # CASE 2 — Update existing deposit line
            if existing_brs:
                need_update = False
                for line in existing_brs:
                    if abs((line.price_unit or 0.0) - total_amount) > 0.0001:
                        need_update = True
                        break

                if need_update:
                    try:
                        existing_brs.with_context(skip_brs_update=True).write({
                            'product_uom_qty': 1.0,
                            'price_unit': total_amount,
                            'tax_id': [(5, 0, 0)],
                            'name': brs_product.name or "BRS Deposit",
                        })
                    except Exception:
                        pass

            else:
                # CASE 3 — Create new BRS deposit line
                try:
                    order.with_context(skip_brs_update=True).write({
                        'order_line': [(0, 0, {
                            'product_id': brs_product.id,
                            'name': brs_product.name or "BRS Deposit",
                            'product_uom_qty': 1.0,
                            'price_unit': total_amount,
                            'tax_id': [(5, 0, 0)],
                        })]
                    })
                except Exception:
                    pass





class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, vals_list):

        company = self.env.company
        brs_product = company.brs_deposit_product_id

        for vals in vals_list:
            if not isinstance(vals, dict):
                continue

            product_id = vals.get("product_id")
            if not product_id or not brs_product:
                continue

            if product_id == brs_product.id:
                vals["tax_id"] = [(5, 0, 0)]   # clear all taxes

        return super().create(vals_list)

    def write(self, vals):

        company = self.env.company
        brs_product = company.brs_deposit_product_id

        if brs_product and "tax_id" in vals:
            for line in self:
                if line.product_id.id == brs_product.id:
                    # User is trying to set a tax — forbidden
                    vals["tax_id"] = [(5, 0, 0)]

        return super().write(vals)
    

