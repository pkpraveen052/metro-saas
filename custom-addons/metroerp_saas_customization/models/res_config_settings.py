from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    brs_deposit_amount = fields.Float(
        string="BCRS Deposit Amount",
        related='company_id.brs_deposit_amount',readonly=False,
        help="Default deposit amount for BCRS."
    )

    brs_deposit_product_id = fields.Many2one(
        'product.product',
        string="BCRS Deposit Product",
        related='company_id.brs_deposit_product_id',readonly=False,
        help="Product used for BCRS deposits."
    )

