from odoo import models,fields,api,_

class CRMRecurringplan(models.Model):
    _inherit = "crm.recurring.plan"

    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)