from odoo import models,fields,api,_


class ResPartnerInherit(models.Model):
    _inherit = "res.partner"

    singpass_id = fields.Char(string="Singpass ID")
    is_foreigner = fields.Boolean(string="Is Foreigner (Without Singapss)")
    tax_ref_iras = fields.Char("Tax Ref. No")