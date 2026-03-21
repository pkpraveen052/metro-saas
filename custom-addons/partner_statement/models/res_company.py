from odoo import models,fields,api,_

class ResCompany(models.Model):
    _inherit = 'res.company'

    show_poweredby_report_statements = fields.Boolean(string="Show Powered by Logo")