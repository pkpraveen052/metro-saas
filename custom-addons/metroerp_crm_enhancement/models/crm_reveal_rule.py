from odoo import models,fields,api,_

class CRMRevealRule(models.Model):
    _inherit = "crm.reveal.rule"

    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)