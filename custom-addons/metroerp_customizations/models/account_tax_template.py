from odoo import api, fields, models, _

class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    for_IRAS = fields.Boolean(string="For IRAS")
    iras_supplies_type = fields.Selection(
        [('standard', "Standard-rated Supplies"), ('zerorated', "Zerorated Supplies"), ('exempt', 'Exempt Supplies')],
        default='standard', string='IRAS Supplies Type')