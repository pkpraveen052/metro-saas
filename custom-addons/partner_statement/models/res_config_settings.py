from odoo import models,fields,api,_

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    show_poweredby_report_statements = fields.Boolean("Show Powered by Logo", related="company_id.show_poweredby_report_statements", readonly=False)
