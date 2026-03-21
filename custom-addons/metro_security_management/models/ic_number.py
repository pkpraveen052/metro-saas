from odoo import models,fields,api,_

class ICNumber(models.Model):
    _name = "ic.number"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Visitor Info"
    _rec_name = "ic_number"

    name = fields.Char(string="Name",tracking=True)
    ic_number = fields.Char(string='IC Number',tracking=True)
    phone = fields.Char(string="Phone",tracking=True)
    email = fields.Char(string="Email",tracking=True)
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)
    active = fields.Boolean(string="Active",default=True)
    image_1920 = fields.Image(string="Image")