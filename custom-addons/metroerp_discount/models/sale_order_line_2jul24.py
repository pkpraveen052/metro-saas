# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount_type = fields.Selection([('fixed', '$'), ('percent', '%')], string="Disc. Type",
                                     default='percent')
    discount_total = fields.Monetary(
        compute="_compute_discount_amount", string="Discount Total", store=True
    )
    # price_total_no_discount = fields.Monetary(
    #     compute="_compute_discount_amount", string="Total Without Discount", store=True
    # )

    @api.depends("discount", "price_total", "product_uom_qty")
    def _compute_discount_amount(self):
        """
        This method calculates the Total amount with and without discount.
        :param self: Sale Order
        """
        #lines_discount = self.filtered(lambda a: a.discount)

        # Order lines with discount
        for line in self:
            discount_total = 0
            if line.discount_type == 'fixed' and line.discount:
                new_discount = (line.discount / (line.product_uom_qty * line.price_unit)) * 100
                line_discount_price_unit = line.price_unit * (1 - (new_discount / 100.0))
                subtotal = line.product_uom_qty * line_discount_price_unit
                discount_total = (line.product_uom_qty * line.price_unit) - subtotal
                # price_unit_wo_discount = price_unit * quantity - discount
                # quantity = 1.0
            elif line.discount:
                line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
                subtotal = line.product_uom_qty * line_discount_price_unit
                discount_total = (line.product_uom_qty * line.price_unit) - subtotal
            line.update(
                {
                    "discount_total": discount_total,
                    #"price_total_no_discount": price_total_no_discount,
                }
            )

        # Lines without a discount and those that are not order lines
        # are excluded
        # (self - lines_discount).update(
        #     {
        #         "discount_total": 0.0,
        #         "price_total_no_discount": 0.0,
        #     }
        # )

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'discount_type')
    def _compute_amount(self):
        """
        This method computes the amount of the sale order line based on the taxes applied and discount applied based on
        the discount type i.e fixed or percentage.
        params : self
        """
        for line in self:
            line_discount_price_unit, subtotal = 0.0, 0.0
            if line.discount_type == 'percent':
                line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
                subtotal = line.product_uom_qty * line_discount_price_unit
            elif line.discount_type == 'fixed':
                new_discount = (line.discount / (line.product_uom_qty * line.price_unit)) * 100
                line_discount_price_unit = line.price_unit * (1 - (new_discount / 100.0))
                subtotal = line.product_uom_qty * line_discount_price_unit

            if line.tax_id:
                taxes = line.tax_id.compute_all(line_discount_price_unit, line.order_id.currency_id,
                                                                                   line.product_uom_qty,
                                                                                   product=line.product_id,
                                                                                   partner=line.order_id.partner_shipping_id)
                line.update({
                    'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                })

            else:
                line['price_total'] = line['price_subtotal'] = subtotal

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        res.update({"discount_type": self.discount_type})
        return res


class SaleOrder(models.Model):
    _inherit = "sale.order"

    discount_total = fields.Monetary(
        compute="_compute_discount_total",
        string="Discount Total",
        currency_field="currency_id",
        store=True,
    )
    # price_subtotal_no_discount = fields.Monetary(
    #     compute="_compute_discount_total",
    #     string="Subtotal Without Discount",
    #     currency_field="currency_id",
    #     store=True,
    # )
    # price_total_no_discount = fields.Monetary(
    #     compute="_compute_discount_total",
    #     string="Total Without Discount",
    #     currency_field="currency_id",
    #     store=True,
    # )


    @api.depends("order_line.discount_total", "order_line.product_uom_qty")
    def _compute_discount_total(self):
        """
        This method calculates the Total amount with and without discount.
        :param self: Sale Order
        """
        for order in self:
            discount_total = sum(order.order_line.mapped("discount_total"))
            # price_subtotal_no_discount = sum(
            #     order.order_line.mapped("price_subtotal_no_discount")
            # )
            # price_total_no_discount = sum(
            #     order.order_line.mapped("price_total_no_discount")
            # )
            order.update(
                {
                    "discount_total": discount_total,
                    # "price_subtotal_no_discount": price_subtotal_no_discount,
                    #"price_total_no_discount": price_total_no_discount,
                }
            )

