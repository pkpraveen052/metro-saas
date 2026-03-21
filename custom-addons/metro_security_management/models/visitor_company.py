from odoo import models,fields,api,_

class VisitorCompany(models.Model):
    _name = "visitor.company"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Visitor Company"

    name = fields.Char(string="Name",tracking=True)
    phone = fields.Char(string="Phone",tracking=True)
    address = fields.Text(string="Address",tracking=True)
    vehicle_ids = fields.Many2many("visitor.vehicle", string="Vehicles")
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)