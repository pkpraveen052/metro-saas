from odoo import models,fields,api,_

class CRMLostReason(models.Model):
    _inherit = "crm.lost.reason"

    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)