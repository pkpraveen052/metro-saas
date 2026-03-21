# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    discount_type = fields.Selection([('fixed', '$'), ('percent', '%')], string="Disc. Type",
                                     default='percent')
    discount_amount = fields.Float(string='Disc.', digits='Discount', default=0.0)

    discount_total = fields.Monetary(
        compute="_compute_discount_amount", string="Discount Total", store=True
    )
    # price_total_no_discount = fields.Monetary(
    #     compute="_compute_discount_amount", string="Total Without Discount", store=True
    # )

    @api.depends("discount_amount", "price_total", "product_qty")
    def _compute_discount_amount(self):
        """
        This method calculates the Total amount with and without discount.
        :param self: Purchase Order Line
        """
        #lines_discount = self.filtered(lambda a: a.discount_amount)

        # Order lines with discount
        for line in self:
            discount_total = 0
            if line.discount_type == 'fixed' and line.product_qty and line.price_unit:
                new_discount = (line.discount_amount / (line.product_qty * line.price_unit)) * 100
                line_discount_price_unit = line.price_unit * (1 - (new_discount / 100.0))
                subtotal = line.product_qty * line_discount_price_unit
                discount_total = (line.product_qty * line.price_unit) - subtotal
                # price_unit_wo_discount = price_unit * quantity - discount
                # quantity = 1.0
            elif line.discount_amount:
                line_discount_price_unit = line.price_unit * (1 - (line.discount_amount / 100.0))
                subtotal = line.product_qty * line_discount_price_unit
                discount_total = (line.product_qty * line.price_unit) - subtotal
            line.update(
                {
                    "discount_total": discount_total,
                    # "price_total_no_discount": price_total_no_discount,
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

    @api.depends('product_qty', 'price_unit', 'taxes_id', 'discount_type', 'discount_amount')
    def _compute_amount(self):
        """
        This method computes the amount of the purchase order line based on the taxes applied and discount
        applied based on the discount type i.e fixed or percentage.
        params : self
        """
        for line in self:
            line_discount_price_unit, subtotal = 0.0, 0.0
            if line.discount_type == 'percent' and line.product_qty:
                if line.price_unit:
                    line_discount_price_unit = line.price_unit * (1 - (line.discount_amount / 100.0))
                    subtotal = line.product_qty * line_discount_price_unit
                else:
                    subtotal = line.product_qty * line.price_unit
            elif line.discount_type == 'fixed' and line.product_qty:
                if line.price_unit:
                    new_discount = (line.discount_amount / (line.product_qty * line.price_unit)) * 100
                    line_discount_price_unit = line.price_unit * (1 - (new_discount / 100.0))
                    subtotal = line.product_qty * line_discount_price_unit
                else:
                    subtotal = line.product_qty * line.price_unit
            if line.taxes_id:
                print('\n\n\n\nline.taxes_id', line.taxes_id)
                taxes = line.taxes_id.compute_all(line_discount_price_unit, line.order_id.currency_id,
                                                                                line.product_qty,
                                                                                product=line.product_id,
                                                                                partner=line.order_id.partner_id)
                line.update({
                    'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                })


            taxes = line.taxes_id.compute_all(line_discount_price_unit, line.order_id.currency_id,
                                            line.product_qty,
                                            product=line.product_id,
                                            partner=line.order_id.partner_id)

            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': subtotal,
                'price_subtotal': subtotal,
            })



    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move)
        res.update({'discount_type': self.discount_type, 'discount': self.discount_amount})
        return res

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

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


    @api.depends("order_line.discount_total", "order_line.product_qty")
    def _compute_discount_total(self):
        """
        This method calculates the Total amount with and without discount.
        :param self: Purchase Order
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

