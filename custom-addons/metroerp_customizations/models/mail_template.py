from odoo import _, api, fields, models, tools

class InheritMailTemplate(models.Model):
    _inherit = "mail.template"

    company_id = fields.Many2one("res.company", string="Company")


    