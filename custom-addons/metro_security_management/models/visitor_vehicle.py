from odoo import models,fields,api,_

class VisitorVehicle(models.Model):
    _name = "visitor.vehicle"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Visitor Vehicle"

    name = fields.Char(string="Name",tracking=True)
    phone = fields.Char(string="Phone",tracking=True)
    vehicle_number = fields.Char(string="Vehicle Number",tracking=True)
    visitor_company_ids = fields.Many2many("visitor.company", string="Companies")
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)
    vehicle_image = fields.Binary(string="Vehicle Image")
