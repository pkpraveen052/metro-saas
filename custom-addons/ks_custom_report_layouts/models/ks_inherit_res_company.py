from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import re

class KsResCompany(models.Model):
    _inherit = 'res.company'

    ks_one_page_reports = fields.Boolean('One Page Report')

    ks_emailcc_partner_id = fields.Many2many(comodel_name='res.partner', string='Email Partner',
                                             domain="[('parent_id','!=', False), ('type','=','contact'), ('email','!=', False)]")
    # Water Mark
    ks_upload_image = fields.Image("Upload Image", attachment=True, readonly=False,
                                   help="This field holds the image used for" + "the badge, limited to 256x256")
    ks_rotate_image = fields.Boolean(string='Rotate')
    ks_watermark_option = fields.Selection([('logo', 'Company Logo'), ('name', 'Company Name'), ('watermark_text', 'WaterMark Text'),
         ('backgroundimage', 'Background Image')], default='logo', string="Watermark Option")
    ks_rotate_angle = fields.Integer(string='Rotate Angle', default=10)
    ks_temp_font_size = fields.Integer(string='Font Size', default=20)
    ks_font_color = fields.Char(string="Font Color", default="rgba(0,0,0,1)")
    ks_mark_text = fields.Text(string="Watermark Text")
    # common fields in all watermark
    ks_report_scale = fields.Selection([('1', 'Auto'), ('5', '500 %'), ('2', '200 %'), ('0.5', '50 %')],string='Scale Water Mark', default='1')
    ks_report_transparency = fields.Float('Transparency',  default=0.2, readonly=False)
    ks_report_company_title = fields.Char(string="Company Title")

    uen_number = fields.Char(string="UEN",related="l10n_sg_unique_entity_number",readonly=True)
    alt_uen_number = fields.Char(string="Secondary UEN")
    mobile_number = fields.Char(string="Mobile Number")

    use_uen_number = fields.Boolean("Use UEN",default=True)
    use_alt_uen_number = fields.Boolean("Use Alt UEN")
    use_mobile_number = fields.Boolean("Use Mobile")
    country_code = fields.Char(related='country_id.code', store=True)
    plan_no = fields.Char("Plan No.")
    care_of = fields.Char("c/o")


    @api.constrains('mobile_number', 'uen_number', 'alt_uen_number')
    def _check_contact_fields(self):
        mobile_pattern = re.compile(r'^(\+65)?[0-9]{8}$')
        uen_pattern = re.compile(r'^[A-Za-z0-9]+$')

        for record in self:
            # Validate Mobile
            if record.mobile_number:
                mobile = (record.mobile_number or "").strip().replace(" ", "")
                if not mobile:
                    raise ValidationError("Mobile number is required when 'Mobile' is enabled.")
                if not mobile_pattern.fullmatch(mobile):
                    raise ValidationError("Invalid mobile number. It must be 8 digits or start with +65 followed by 8 digits. No spaces or special characters allowed.")

            # Validate UEN
            if record.uen_number:
                uen = (record.uen_number or "").strip()
                if not uen:
                    raise ValidationError("UEN number is required when 'UEN' is enabled.")
                if not uen_pattern.fullmatch(uen):
                    raise ValidationError("Invalid UEN number. Only alphanumeric characters allowed. No spaces or special characters.")

            # Validate Alt UEN
            if record.alt_uen_number:
                alt_uen = (record.alt_uen_number or "").strip()
                if not alt_uen:
                    raise ValidationError("Secondary UEN number is required when 'Alt UEN' is enabled.")
                if not uen_pattern.fullmatch(alt_uen):
                    raise ValidationError("Invalid Secondary UEN number. Only alphanumeric characters allowed. No spaces or special characters.")

    @api.onchange('use_uen_number', 'use_alt_uen_number', 'use_mobile_number')
    def _onchange_use_only_one(self):
        for rec in self:
            if rec.use_uen_number:
                rec.use_alt_uen_number = False
                rec.use_mobile_number = False
            elif rec.use_alt_uen_number:
                rec.use_uen_number = False
                rec.use_mobile_number = False
            elif rec.use_mobile_number:
                rec.use_uen_number = False
                rec.use_alt_uen_number = False

    @api.onchange('ks_watermark_option')
    def ks_onchange_watermark_option(self):
        if self.ks_watermark_option == 'backgroundimage':
            self.ks_upload_image = 0
        if self.ks_watermark_option in ['name', 'watermark_text']:
            self.ks_rotate_image = ""
            self.ks_rotate_angle = ""
            self.ks_temp_font_size = ""
            self.ks_font_color = ""
            self.ks_mark_text = ""

    @api.constrains('ks_one_page_reports')
    def _custom_paper_format(self):
        paper_format = self.env.ref('ks_custom_report_layouts.ks_odoo_custom_report_paperformat')
        sale_report_id = self.env.ref('sale.action_report_saleorder')
        if self.ks_one_page_reports:
            if paper_format and sale_report_id:
                sale_action_report = self.env['ir.actions.report'].sudo().browse(sale_report_id[0].id)
                if sale_action_report:
                    sale_action_report.sudo().write({
                        'paperformat_id': paper_format,
                    })
        else:
            if sale_report_id:
                other_paper_format = self.env['report.paperformat'].sudo().\
                    search([('id', 'not in', paper_format.ids)], limit=1)
                sale_action_report = self.env['ir.actions.report'].sudo().browse(sale_report_id[0].id)
                if sale_action_report:
                    sale_action_report.sudo().write({
                        'paperformat_id': other_paper_format,
                    })

    @api.model
    def create(self, vals):
        company = super(KsResCompany, self).create(vals)
        self.env['ks.report.configuration'].sudo().search([]).ks_create_records()
        return company

    
    def create_doc_layout(self):
        """Creates document layout records for all existing companies."""
        self.env['ks.report.configuration'].sudo().ks_create_records()
