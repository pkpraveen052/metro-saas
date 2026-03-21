from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

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

   
    def _update_brs(self):
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
                    existing_brs.with_context(ctx).unlink()
                continue

            if existing_brs:
                existing_brs.with_context(ctx).write({
                    'quantity': 1.0,
                    'price_unit': total_amount,
                    'tax_ids': [(5, 0, 0)],
                    'name': brs_product.name or "BRS Deposit",
                })
            else:
                move.with_context(ctx).write({
                    'invoice_line_ids': [(0, 0, {
                        'product_id': brs_product.id,
                        'name': brs_product.name or "BRS Deposit",
                        'quantity': 1.0,
                        'price_unit': total_amount,
                        'tax_ids': [(5, 0, 0)],
                    })]
                })

            # SAFE recompute only
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



