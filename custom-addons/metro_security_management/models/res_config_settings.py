from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    use_visitor_tc = fields.Boolean(string='Visitor Terms & Conditions', related='company_id.use_visitor_tc', readonly=False)
    visitor_tc = fields.Text(related='company_id.visitor_tc', readonly=False)