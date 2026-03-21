from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ks_one_page_reports = fields.Boolean(related='company_id.ks_one_page_reports', readonly=False)
    ks_upload_image = fields.Image(related='company_id.ks_upload_image', readonly=False)
    ks_rotate_image = fields.Boolean(related='company_id.ks_rotate_image', readonly=False)
    ks_watermark_option = fields.Selection(related='company_id.ks_watermark_option', readonly=False)
    ks_rotate_angle = fields.Integer(related='company_id.ks_rotate_angle', readonly=False)
    ks_temp_font_size = fields.Integer(related='company_id.ks_temp_font_size', readonly=False)
    ks_font_color = fields.Char(related='company_id.ks_font_color', readonly=False)
    ks_mark_text = fields.Text(related='company_id.ks_mark_text', readonly=False)

    ks_report_header_tagline = fields.Text(related='company_id.report_header', readonly=False)
    ks_report_company_title = fields.Char(related="company_id.ks_report_company_title",readonly=False,string="Company Title")

    # common fields in all watermark
    ks_report_scale = fields.Selection(related='company_id.ks_report_scale', readonly=False)
    ks_report_transparency = fields.Float(related='company_id.ks_report_transparency', readonly=False)
    ks_emailcc_partner_id = fields.Many2many(comodel_name='res.partner', related='company_id.ks_emailcc_partner_id', readonly=False)
    plan_no = fields.Char(related="company_id.plan_no",readonly=False,string="Plan No.")
    care_of = fields.Char(related="company_id.care_of",readonly=False,string="c/o")

    @api.onchange('ks_temp_font_size')
    def ks_onchange_fontsize(self):
        if not 10 <= self.ks_temp_font_size <= 30:
            raise UserError('Font Size Must Be Between 10px to 30px')

    @api.onchange('ks_report_transparency')
    def ks_onchange_transparency(self):
        if not 0 <= self.ks_report_transparency <= 1:
            raise UserError('Transparency Must Be Between 0 to 1')