from odoo import api, fields, models
import re

class AccountMove(models.Model):
    _inherit = 'account.move'

    exchange_rate = fields.Float(
        string='Currency Rate',
        compute='_compute_currency_rate_display',
        digits=(12, 6),
        store=False
    )

    # @api.depends('currency_id', 'invoice_date', 'company_id')
    # def _compute_currency_rate_display(self):
    #     for move in self:
    #         if (
    #             move.currency_id
    #             and move.company_id
    #             and move.invoice_date
    #             and move.currency_id != move.company_id.currency_id
    #         ):
    #             move.exchange_rate = move.currency_id._get_conversion_rate(
    #                 move.currency_id,
    #                 move.company_id.currency_id,
    #                 move.company_id,
    #                 move.invoice_date,
    #             )
    #         else:
    #             move.exchange_rate = 1.0

    @api.depends('currency_id', 'invoice_date', 'company_id')
    def _compute_currency_rate_display(self):
        for move in self:
            if (
                move.currency_id
                and move.company_id
                and move.invoice_date
                and move.currency_id != move.company_id.currency_id
            ):
                rate = move.currency_id._get_conversion_rate(
                    move.currency_id,
                    move.company_id.currency_id,
                    move.company_id,
                    move.invoice_date,
                )
                # Invert the rate to match res.currency.rate (EUR rate)
                move.exchange_rate = rate and (1 / rate) or 0.0
            else:
                move.exchange_rate = 1.0




    def get_total_tax_per_account(self):
        """
        Returns a dictionary of tax name and total tax amount in company currency.
        Only considers journal items where account is a tax account and uses the credit value.
        """
        self.ensure_one()
        tax_totals = {}
        company_currency = self.company_id.currency_id

        for line in self.line_ids:
            if line.tax_line_id:
                tax_name = line.tax_line_id.name  # Use tax name
                amount = line.credit               
                if tax_name in tax_totals:
                    tax_totals[tax_name] += amount
                else:
                    tax_totals[tax_name] = amount

        return tax_totals


    is_company_currency = fields.Boolean(
        compute='_compute_is_company_currency',
        store=False
    )

    @api.depends('currency_id', 'company_id')
    def _compute_is_company_currency(self):
        for move in self:
            move.is_company_currency = (move.currency_id == move.company_id.currency_id)
