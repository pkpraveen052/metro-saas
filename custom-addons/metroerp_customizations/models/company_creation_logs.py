from odoo import api, fields, models, _

class CompanyCreationLog(models.Model):
    _name = "company.creation.logs"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Company Creation Logs"
    _rec_name = "company_name"
    _order = "create_date desc"

    description = fields.Text(string="Description")
    error_from = fields.Char(string="Error From")
    company_name = fields.Char(string="Company Name")
    state = fields.Selection([('success','Success'),('error','Error')],string="State")


