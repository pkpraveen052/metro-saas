from odoo import models,fields,api,_

class VisitorCategory(models.Model):
    _name = "visitor.category"
    _description = "Visitor Category"

    name = fields.Char(string="Name")
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)