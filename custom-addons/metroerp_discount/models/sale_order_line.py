# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from functools import partial
from odoo.tools.misc import formatLang, get_lang


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
            if line.discount_type == 'fixed' and line.discount and line.product_uom_qty and line.price_unit:
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
            elif line.discount_type == 'fixed' and line.product_uom_qty and line.price_unit:
                new_discount = (line.discount / (line.product_uom_qty * line.price_unit)) * 100
                line_discount_price_unit = line.price_unit * (1 - (new_discount / 100.0))
                subtotal = line.product_uom_qty * line_discount_price_unit

            taxes = line.tax_id.compute_all(line_discount_price_unit, line.order_id.currency_id,
                                                                               line.product_uom_qty,
                                                                               product=line.product_id,
                                                                               partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

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


    def _amount_by_group(self):
        """ Method overidden to add the logic of discount type 'fixed' and calculate the groupwise taxes. """
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            fmt = partial(formatLang, self.with_context(lang=order.partner_id.lang).env, currency_obj=currency)
            res = {}
            for line in order.order_line:
                # Custom code starts
                if line.discount_type == 'fixed':
                    new_discount = (line.discount / (line.product_uom_qty * line.price_unit)) * 100
                    price_reduce = line.price_unit * (1 - (new_discount / 100.0))
                else:
                # ends
                    price_reduce = line.price_unit * (1.0 - line.discount / 100.0)
                taxes = line.tax_id.compute_all(price_reduce, quantity=line.product_uom_qty, product=line.product_id, partner=order.partner_shipping_id)['taxes']
                for tax in line.tax_id:
                    group = tax.tax_group_id
                    res.setdefault(group, {'amount': 0.0, 'base': 0.0})
                    for t in taxes:
                        if t['id'] == tax.id or t['id'] in tax.children_tax_ids.ids:
                            res[group]['amount'] += t['amount']
                            res[group]['base'] += t['base']
            res = sorted(res.items(), key=lambda l: l[0].sequence)

            # round amount and prevent -0.00
            for group_data in res:
                group_data[1]['amount'] = currency.round(group_data[1]['amount']) + 0.0
                group_data[1]['base'] = currency.round(group_data[1]['base']) + 0.0

            order.amount_by_group = [(
                l[0].name, l[1]['amount'], l[1]['base'],
                fmt(l[1]['amount']), fmt(l[1]['base']),
                len(res),
            ) for l in res]
