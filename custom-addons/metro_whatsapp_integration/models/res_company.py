from odoo import models,fields,api,_

class ResCompany(models.Model):
    _inherit = 'res.company'

    use_assistro = fields.Boolean(string="Use Assistro",default=False)

    @api.model
    def create(self, vals):
        company = super(ResCompany, self).create(vals)
        self.env['assistro.whatsapp.template'].sudo().search([])._create_temp_records()
        return company
    

    def create_whatsapp_templates(self):
        """Creates whatsapp templates for all existing companies."""
        self.env['assistro.whatsapp.template'].sudo()._create_temp_records()