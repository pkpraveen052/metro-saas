from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('skip_brs_update'):
            return res

        for rec in self:
            try:
                rec._update_brs()
            except Exception:
                _logger.exception("Error running _update_brs() after write for move %s", rec.id)
        return res

    @api.model
    def create(self, vals):
        if self.env.context.get('skip_brs_update'):
            return super().create(vals)
        move = super().create(vals)

        # run update for created moves in normal context
        for rec in move:
            try:
                rec._update_brs()
            except Exception:
                _logger.exception("Error running _update_brs() after create for move %s", rec.id)
        return move

    @api.onchange('invoice_line_ids', 'invoice_line_ids.product_id', 'invoice_line_ids.quantity')
    def _onchange_update_brs(self):
        if self.env.context.get('skip_brs_update'):
            return
        self._update_brs(in_onchange=True)

    def _update_brs(self, in_onchange=False):
        if self.env.context.get('skip_brs_update'):
            return

        ALLOWED_TYPES = ('out_invoice', 'in_invoice', 'out_refund', 'in_refund')

        for move in self:
            if move.move_type not in ALLOWED_TYPES:
                continue

            if move.invoice_origin and 'POS' in move.invoice_origin:
                continue

            company = move.company_id
            brs_product = company.brs_deposit_product_id
            if not brs_product:
                continue
            if move.is_sale_document(include_receipts=True):
                brs_account = brs_product.property_account_income_id or brs_product.categ_id.property_account_income_categ_id
            else:
                brs_account = brs_product.property_account_expense_id or brs_product.categ_id.property_account_expense_categ_id

            deposit_lines = move.invoice_line_ids.filtered(
                lambda l: l.product_id and l.product_id.is_brs_deposit
                and l.product_id.id != brs_product.id
            )

            total_amount = sum(
                (l.product_id.brs_deposit_amount or 0.0) * (l.quantity or 0.0)
                for l in deposit_lines
            )

            existing_brs = move.invoice_line_ids.filtered(
                lambda l: l.product_id.id == brs_product.id
            )

            ctx = dict(self.env.context, skip_brs_update=True)

            if abs(total_amount) < 0.0001:
                if existing_brs:
                    if in_onchange:
                        move.invoice_line_ids -= existing_brs
                    else:
                        existing_brs.with_context(ctx).unlink()
                continue

            if existing_brs:
                brs_vals = {
                    'quantity': 1.0,
                    'price_unit': total_amount,
                    'tax_ids': [(5, 0, 0)],
                    'name': brs_product.name or "BRS Deposit",
                }

                if in_onchange:
                    existing_brs.update(brs_vals)
                else:
                    existing_brs.with_context(ctx).write(brs_vals)
            else:
                brs_vals = {
                    'product_id': brs_product.id,
                    'name': brs_product.name or "BRS Deposit",
                    'quantity': 1.0,
                    'price_unit': total_amount,
                    'tax_ids': [(5, 0, 0)],
                }
                if in_onchange:
                    move.update({'invoice_line_ids': [(0, 0, brs_vals)]})
                else:
                    move.with_context(ctx).write({'invoice_line_ids': [(0, 0, brs_vals)]})

            if in_onchange and hasattr(move, '_onchange_recompute_dynamic_lines'):
                move._onchange_recompute_dynamic_lines()
            else:
                # keep receivable/payable and tax lines in sync
                move.with_context(ctx)._recompute_dynamic_lines()



class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

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
                vals["tax_ids"] = [(5, 0, 0)]  # clear all taxes

        return super().create(vals_list)

    # def write(self, vals):
    #     company = self.env.company
    #     brs_product = company.brs_deposit_product_id

    #     if brs_product and "tax_ids" in vals:
    #         for line in self:
    #             if line.product_id.id == brs_product.id:
    #                 #Remove all taxes
    #                 vals["tax_ids"] = [(5, 0, 0)]

    #     return super().write(vals)

