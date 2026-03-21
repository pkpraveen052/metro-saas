from odoo import fields, models
from datetime import date


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    def create_create_sequence_date_range(self):
        for rec in self:
            current_year = date.today().year
            previous_year = current_year - 1
            years = [previous_year, current_year]
            for year in years:
                start_date = date(year, 1, 1)
                end_date = date(year, 12, 31)

                # Check if already exists
                existing = self.env['ir.sequence.date_range'].search([
                    ('sequence_id', '=', rec.id),
                    ('date_from', '=', start_date),
                    ('date_to', '=', end_date)
                ], limit=1)

                if not existing:
                    self.env['ir.sequence.date_range'].create({
                        'sequence_id': rec.id,
                        'date_from': start_date,
                        'date_to': end_date,
                        'number_next': 1,
                    })