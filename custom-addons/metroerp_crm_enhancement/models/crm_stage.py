from odoo import models,fields,api,_

class CRMStage(models.Model):
    _inherit = "crm.stage"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        index=True,
        help="Specific company that uses this stage. "
        "Other companies will not be able to see or use this stage.",
        default=lambda self: self.env.company.id,
    )