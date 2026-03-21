from odoo import models, fields


class ProductCategory(models.Model):
    _inherit = 'product.category'

    cogs_account_id = fields.Many2one(
        'account.account',
        string="COGS Account",
        domain="[('deprecated', '=', False)]",
        help="Select the Cost of Goods Sold (COGS) account."
    )
