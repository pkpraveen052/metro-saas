from odoo import models,fields,api,_

class AccountChartTemplateInherit(models.Model):
    _inherit = "account.chart.template"

    iras_template_id = fields.Many2one("iras.default.accounts.mapping",string="Iras Template")