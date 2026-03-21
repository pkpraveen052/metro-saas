from odoo import models,fields,api,_

class VisitorType(models.Model):
    _name = "visitor.type"
    _description = "Visitor Type"

    name = fields.Char(string="Name")
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)