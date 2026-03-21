from odoo import models,fields,api,_

class SecurityPerson(models.Model):
    _name = "security.person"
    _description = "Security Person"

    name = fields.Char(string="Name",required=True)
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)