from odoo import models,fields,api,_

class ResCompanyInherited(models.Model):
    _inherit="res.company"

    use_visitor_tc = fields.Boolean(string='Visitor Terms & Conditions', default=True)
    visitor_tc = fields.Text(translate=True)