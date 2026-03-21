from odoo import fields, models, api, _

class WhatsappLog(models.Model):
    _name = "whatsapp.log"
    _description = "Whatsapp Logs"
    _order = "create_date desc"

    name = fields.Char(string="Log Name", required=True)
    status = fields.Selection([('success', 'Success'),('fail', 'Fail')], string="Status", required=True)
    status_code = fields.Integer(string="Status Code")
    json_data = fields.Text(string="JSON Data")
    message = fields.Text(string="Error Message")
    company_id = fields.Many2one("res.company",string="Company Name")