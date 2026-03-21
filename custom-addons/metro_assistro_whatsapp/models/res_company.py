from odoo import models,fields,api,_

class ResCompany(models.Model):
    _inherit = 'res.company'

    use_assistro = fields.Boolean(string="Use Assistro",default=True)

    # @api.model
    # def create(self, vals):
    #     company = super(ResCompany, self).create(vals)
    #     self.env['assistro.whatsapp.template'].sudo().search([])._create_temp_records()
    #     return company