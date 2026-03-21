from odoo import models,fields,api,_

class LeadMiningRequest(models.Model):
    _inherit = "crm.iap.lead.mining.request"

    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)