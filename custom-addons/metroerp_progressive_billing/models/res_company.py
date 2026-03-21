from odoo import models,fields,api,_

class ResCompany(models.Model):
    _inherit = 'res.company'

    use_assistro = fields.Boolean(string="Use Assistro",default=True)

  