from odoo import models,fields,api,_


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_manufacturing_lead = fields.Boolean(related='company_id.use_manufacturing_lead', string="Default Manufacturing Lead Time", readonly=False)
