# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_compare, date_utils, email_split, email_re
from odoo.tools.misc import formatLang, format_date, get_lang

from datetime import date, timedelta
from collections import defaultdict
from itertools import zip_longest
from hashlib import sha256
from json import dumps

import ast
import json
import re
import warnings

#forbidden fields
INTEGRITY_HASH_MOVE_FIELDS = ('date', 'journal_id', 'company_id')
INTEGRITY_HASH_LINE_FIELDS = ('debit', 'credit', 'account_id', 'partner_id')

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    discount_type = fields.Selection([('fixed', '$'), ('percent', '%')], string="Disc. Type", default='percent')
    price_unit_tmp = fields.Float('Price Unit Tmp')

    discount_total = fields.Monetary(
        compute="_compute_discount_amount", string="Discount Total", store=True
    )
    # price_total_no_discount = fields.Monetary(
    #     compute="_compute_discount_amount", string="Total Without Discount", store=True
    # )

    @api.depends("discount", "price_total")
    def _compute_discount_amount(self):
        """
        This method calculates the Total amount with and without discount.
        :param self: Account Move Line
        """
        invoice_lines_discount = self.filtered(
            lambda a: a.discount and not a.exclude_from_invoice_tab
        )

        # Invoice lines with discount
        for line in invoice_lines_discount:
            if line.discount_type == 'fixed' and line.quantity and line.price_unit:
                new_discount = (line.discount / (line.quantity * line.price_unit)) * 100
                line_discount_price_unit = line.price_unit * (1 - (new_discount / 100.0))
                subtotal = line.quantity * line_discount_price_unit
                discount_total = (line.quantity * line.price_unit) - subtotal
                # price_unit_wo_discount = price_unit * quantity - discount
                # quantity = 1.0
            else:
                line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
                subtotal = line.quantity * line_discount_price_unit
                discount_total = (line.quantity * line.price_unit) - subtotal
            line.update(
                {
                    "discount_total": discount_total,
                    #"price_total_no_discount": price_total_no_discount,
                }
            )

        # Lines without a discount and those that are not invoice lines
        # are excluded
        (self - invoice_lines_discount).update(
            {
                "discount_total": 0.0,
                #"price_total_no_discount": 0.0,
            }
        )

    @api.onchange('quantity', 'discount', 'discount_type', 'price_unit', 'tax_ids')
    def _onchange_price_subtotal(self):
        return super(AccountMoveLine, self)._onchange_price_subtotal()

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes,
                                            move_type):
        print("\n OVERIDDEN _get_price_total_and_subtotal_model() >>>>>")
        print("self._context ==",self._context)
        res = {}
        line_discount_price_unit, subtotal = 0.0, 0.0
        # Compute 'price_subtotal'.
        discount_type = ''
        if self._context and self._context.get('wk_vals_list', []):
            for vals in self._context.get('wk_vals_list', []):
                if price_unit == vals.get('price_unit', 0.0) and quantity == vals.get('quantity',
                                                                                      0.0) and discount == vals.get(
                        'discount', 0.0) and product.id == vals.get('product_id', False) and partner.id == vals.get(
                        'partner_id', False):
                    discount_type = vals.get('discount_type', '')
        discount_type = self.discount_type or discount_type
        if discount_type == 'fixed' and quantity and price_unit:
            new_discount = (discount / (quantity * price_unit)) * 100
            line_discount_price_unit = price_unit * (1 - (new_discount / 100.0))
            subtotal = quantity * line_discount_price_unit
            #price_unit_wo_discount = price_unit * quantity - discount
            #quantity = 1.0
        else:
            line_discount_price_unit = price_unit * (1 - (discount / 100.0))
            subtotal = quantity * line_discount_price_unit

        # Compute 'price_total'.
        #if price_unit == 0:
            #self.tax_ids = False
        if taxes:
            taxes_res = taxes._origin.with_context(force_sign=1).compute_all(line_discount_price_unit,
                                                                             quantity=quantity, currency=currency,
                                                                             product=product, partner=partner,
                                                                             is_refund=move_type in (
                                                                             'out_refund', 'in_refund'))
            print("taxes_res ==",taxes_res)
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        # In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        print("Returning..... res ==",res)
        return res

    @api.model
    def _get_fields_onchange_balance_model(self, quantity, discount, amount_currency, move_type, currency, taxes, price_subtotal, force_computation=False):
        ''' This method is used to recompute the values of 'quantity', 'discount', 'price_unit' due to a change made
        in some accounting fields such as 'balance'.

        This method is a bit complex as we need to handle some special cases.
        For example, setting a positive balance with a 100% discount.

        :param quantity:        The current quantity.
        :param discount:        The current discount.
        :param amount_currency: The new balance in line's currency.
        :param move_type:       The type of the move.
        :param currency:        The currency.
        :param taxes:           The applied taxes.
        :param price_subtotal:  The price_subtotal.
        :return:                A dictionary containing 'quantity', 'discount', 'price_unit'.
        '''
        print("\n IMPPPPPPPPPPPPPP           OVERIDDEN _get_fields_onchange_balance_model() >>>>>")
        print("self._context ==",self._context)
        if move_type in self.move_id.get_outbound_types():
            sign = 1
        elif move_type in self.move_id.get_inbound_types():
            sign = -1
        else:
            sign = 1
        amount_currency *= sign

        # Avoid rounding issue when dealing with price included taxes. For example, when the price_unit is 2300.0 and
        # a 5.5% price included tax is applied on it, a balance of 2300.0 / 1.055 = 2180.094 ~ 2180.09 is computed.
        # However, when triggering the inverse, 2180.09 + (2180.09 * 0.055) = 2180.09 + 119.90 = 2299.99 is computed.
        # To avoid that, set the price_subtotal at the balance if the difference between them looks like a rounding
        # issue.
        if not force_computation and currency.is_zero(amount_currency - price_subtotal):
            print("Returning...... {}")
            return {}

        taxes = taxes.flatten_taxes_hierarchy()
        if taxes and any(tax.price_include for tax in taxes):
            # Inverse taxes. E.g:
            #
            # Price Unit    | Taxes         | Originator Tax    |Price Subtotal     | Price Total
            # -----------------------------------------------------------------------------------
            # 110           | 10% incl, 5%  |                   | 100               | 115
            # 10            |               | 10% incl          | 10                | 10
            # 5             |               | 5%                | 5                 | 5
            #
            # When setting the balance to -200, the expected result is:
            #
            # Price Unit    | Taxes         | Originator Tax    |Price Subtotal     | Price Total
            # -----------------------------------------------------------------------------------
            # 220           | 10% incl, 5%  |                   | 200               | 230
            # 20            |               | 10% incl          | 20                | 20
            # 10            |               | 5%                | 10                | 10
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(amount_currency, currency=currency, handle_price_include=False)
            for tax_res in taxes_res['taxes']:
                tax = self.env['account.tax'].browse(tax_res['id'])
                if tax.price_include:
                    amount_currency += tax_res['amount']

        discount_type = ''
        if self._context and self._context.get('wk_vals_list', []):
            for vals in self._context.get('wk_vals_list', []):
                if quantity == vals.get('quantity', 0.0) and discount == vals.get('discount',0.0):
                    discount_type = vals.get('discount_type', '')
        discount_type = self.discount_type or discount_type
        if discount_type == 'fixed':
            if amount_currency:
                vals = {
                    'quantity': quantity or 1.0,
                    'price_unit': (amount_currency + discount) / (quantity or 1.0),
                }
            else:
                vals = {}
        else:
            discount_factor = 1 - (discount / 100.0)
            if amount_currency and discount_factor:
                # discount != 100%
                print("# discount != 100% >>")
                print("amount_currency =", amount_currency, ", discount_factor =", discount_factor, ", quantity =", quantity)
                vals = {
                    'quantity': quantity or 1.0,
                    'price_unit': amount_currency / discount_factor / (quantity or 1.0),
                }
            elif amount_currency and not discount_factor:
                # discount == 100%
                print("# discount == 100% >>")
                print("amount_currency =",amount_currency, ", discount_factor =", ", quantity =",quantity)
                vals = {
                    'quantity': quantity or 1.0,
                    'discount': 0.0,
                    'price_unit': amount_currency / (quantity or 1.0),
                }
            elif not discount_factor:
                # balance of line is 0, but discount  == 100% so we display the normal unit_price
                print("# balance of line is 0, but discount  == 100% so we display the normal unit_price >>")
                vals = {}
            else:
                # balance is 0, so unit price is 0 as well
                print("# balance is 0, so unit price is 0 as well >>")
                vals = {'price_unit': 0.0}
            print("Returning..... vals ==",vals)
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        context = self._context.copy()
        context.update({'wk_vals_list': vals_list})
        res = super(AccountMoveLine, self.with_context(context)).create(vals_list)
        return res

class AccountMove(models.Model):
    _inherit = "account.move"

    discount_total = fields.Monetary(
        compute="_compute_discount_total",
        string="Discount Total",
        currency_field="currency_id",
        store=True,
    )
    # price_total_no_discount = fields.Monetary(
    #     compute="_compute_discount_total",
    #     string="Total Without Discount",
    #     currency_field="currency_id",
    #     store=True,
    # )

    @api.depends(
        "invoice_line_ids.discount_total"
    )
    def _compute_discount_total(self):
        """
        This method calculates the Total amount with and without discount.
        :param self: Account Move
        """
        invoices_discount = self.filtered(lambda a: a.is_invoice())

        # Invoices with discount
        for invoice in invoices_discount:
            discount_total = sum(invoice.invoice_line_ids.mapped("discount_total"))
            invoice.update(
                {
                    "discount_total": discount_total
                }
            )

        # Account moves that are not invoices are excluded
        (self - invoices_discount).update(
            {
                "discount_total": 0.0,
                #"price_total_no_discount": 0.0,
            }
        )

    def _recompute_tax_lines(self, recompute_tax_base_amount=False, tax_rep_lines_to_recompute=None):
        """ Compute the dynamic tax lines of the journal entry.

        :param recompute_tax_base_amount: Flag forcing only the recomputation of the `tax_base_amount` field.
        """
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _serialize_tax_grouping_key(grouping_dict):
            ''' Serialize the dictionary values to be used in the taxes_map.
            :param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
            :return: A string representing the values.
            '''
            return '-'.join(str(v) for v in grouping_dict.values())

        def _compute_base_line_taxes(base_line):
            ''' Compute taxes amounts both in company currency / foreign currency as the ratio between
            amount_currency & balance could not be the same as the expected currency rate.
            The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
            :param base_line:   The account.move.line owning the taxes.
            :return:            The result of the compute_all method.
            '''
            move = base_line.move_id

            if move.is_invoice(include_receipts=True):
                handle_price_include = True
                sign = -1 if move.is_inbound() else 1
                quantity = base_line.quantity
                is_refund = move.move_type in ('out_refund', 'in_refund')

                # Commented by krutarth to fix the issue of tax calculation and exchange currency.
                # if base_line.currency_id:
                #     if base_line.discount_type and base_line.discount_type == 'fixed':
                #         price_unit_foreign_curr = sign * (base_line.price_unit - (base_line.discount / (base_line.quantity or 1.0)))
                #     else:
                #         price_unit_foreign_curr = sign  base_line.price_unit  (1 - (base_line.discount / 100.0))
                #     price_unit_wo_discount = base_line.currency_id._convert(price_unit_foreign_curr, move.company_id.currency_id, move.company_id, move.date)
                #     print("If Currency ============== ",price_unit_wo_discount)
                # else:
                # price_unit_foreign_curr = 0.0
                if base_line.discount_type and base_line.discount_type == 'fixed':
                    price_unit_wo_discount = sign * (base_line.price_unit - (base_line.discount / (base_line.quantity or 1.0)))
                else:
                    price_unit_wo_discount = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))

            else:
                handle_price_include = False
                quantity = 1.0
                tax_type = base_line.tax_ids[0].type_tax_use if base_line.tax_ids else None
                is_refund = (tax_type == 'sale' and base_line.debit) or (tax_type == 'purchase' and base_line.credit)
                price_unit_wo_discount = base_line.amount_currency

            balance_taxes_res = base_line.tax_ids._origin.with_context(force_sign=move._get_tax_force_sign()).compute_all(
                price_unit_wo_discount,
                currency=base_line.currency_id,
                quantity=quantity,
                product=base_line.product_id,
                partner=base_line.partner_id,
                is_refund=is_refund,
                handle_price_include=handle_price_include,
            )

            if move.move_type == 'entry':
                repartition_field = is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids'
                repartition_tags = base_line.tax_ids.flatten_taxes_hierarchy().mapped(repartition_field).filtered(lambda x: x.repartition_type == 'base').tag_ids
                tags_need_inversion = self._tax_tags_need_inversion(move, is_refund, tax_type)
                if tags_need_inversion:
                    balance_taxes_res['base_tags'] = base_line._revert_signed_tags(repartition_tags).ids
                    for tax_res in balance_taxes_res['taxes']:
                        tax_res['tag_ids'] = base_line._revert_signed_tags(self.env['account.account.tag'].browse(tax_res['tag_ids'])).ids

            return balance_taxes_res

        taxes_map = {}

        # ==== Add tax lines ====
        to_remove = self.env['account.move.line']
        for line in self.line_ids.filtered('tax_repartition_line_id'):
            grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
            grouping_key = _serialize_tax_grouping_key(grouping_dict)
            if grouping_key in taxes_map:
                # A line with the same key does already exist, we only need one
                # to modify it; we have to drop this one.
                to_remove += line
            else:
                taxes_map[grouping_key] = {
                    'tax_line': line,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                }
        if not recompute_tax_base_amount:
            self.line_ids -= to_remove

        # ==== Mount base lines ====
        for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
            # Don't call compute_all if there is no tax.
            if not line.tax_ids:
                if not recompute_tax_base_amount:
                    line.tax_tag_ids = [(5, 0, 0)]
                continue

            compute_all_vals = _compute_base_line_taxes(line)

            # Assign tags on base line
            if not recompute_tax_base_amount:
                line.tax_tag_ids = compute_all_vals['base_tags'] or [(5, 0, 0)]

            tax_exigible = True
            for tax_vals in compute_all_vals['taxes']:
                grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
                grouping_key = _serialize_tax_grouping_key(grouping_dict)

                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

                if tax.tax_exigibility == 'on_payment':
                    tax_exigible = False

                taxes_map_entry = taxes_map.setdefault(grouping_key, {
                    'tax_line': None,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                })
                taxes_map_entry['amount'] += tax_vals['amount']
                taxes_map_entry['tax_base_amount'] += self._get_base_amount_to_display(tax_vals['base'], tax_repartition_line, tax_vals['group'])
                taxes_map_entry['grouping_dict'] = grouping_dict
            if not recompute_tax_base_amount:
                line.tax_exigible = tax_exigible

        # ==== Pre-process taxes_map ====
        taxes_map = self._preprocess_taxes_map(taxes_map)

        # ==== Process taxes_map ====
        for taxes_map_entry in taxes_map.values():
            # The tax line is no longer used in any base lines, drop it.
            if taxes_map_entry['tax_line'] and not taxes_map_entry['grouping_dict']:
                if not recompute_tax_base_amount:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue

            currency = self.env['res.currency'].browse(taxes_map_entry['grouping_dict']['currency_id'])

            # Don't create tax lines with zero balance.
            if currency.is_zero(taxes_map_entry['amount']):
                if taxes_map_entry['tax_line'] and not recompute_tax_base_amount:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue

            # tax_base_amount field is expressed using the company currency.
            tax_base_amount = currency._convert(taxes_map_entry['tax_base_amount'], self.company_currency_id, self.company_id, self.date or fields.Date.context_today(self))

            # Recompute only the tax_base_amount.
            if recompute_tax_base_amount:
                if taxes_map_entry['tax_line']:
                    taxes_map_entry['tax_line'].tax_base_amount = tax_base_amount
                continue

            balance = currency._convert(
                taxes_map_entry['amount'],
                self.company_currency_id,
                self.company_id,
                self.date or fields.Date.context_today(self),
            )
            amount_currency = currency.round(taxes_map_entry['amount'])
            sign = -1 if self.is_inbound() else 1
            to_write_on_line = {
                'amount_currency': amount_currency,
                'currency_id': taxes_map_entry['grouping_dict']['currency_id'],
                'debit': balance > 0.0 and balance or 0.0,
                'credit': balance < 0.0 and -balance or 0.0,
                'tax_base_amount': tax_base_amount,
                'price_total': sign * amount_currency,
                'price_subtotal': sign * amount_currency,
            }

            if taxes_map_entry['tax_line']:
                # Update an existing tax line.
                if tax_rep_lines_to_recompute and taxes_map_entry['tax_line'].tax_repartition_line_id not in tax_rep_lines_to_recompute:
                    continue

                taxes_map_entry['tax_line'].update(to_write_on_line)
            else:
                # Create a new tax line.
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)

                if tax_rep_lines_to_recompute and tax_repartition_line not in tax_rep_lines_to_recompute:
                    continue

                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                taxes_map_entry['tax_line'] = create_method({
                    **to_write_on_line,
                    'name': tax.name,
                    'move_id': self.id,
                    'company_id': self.company_id.id,
                    'company_currency_id': self.company_currency_id.id,
                    'tax_base_amount': tax_base_amount,
                    'exclude_from_invoice_tab': True,
                    'tax_exigible': tax.tax_exigibility == 'on_invoice',
                    **taxes_map_entry['grouping_dict'],
                })

            if in_draft_mode:
                taxes_map_entry['tax_line'].update(taxes_map_entry['tax_line']._get_fields_onchange_balance(force_computation=True))
