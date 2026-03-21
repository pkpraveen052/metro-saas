# -*- coding: utf-8 -*-

import base64
import mimetypes
from lxml import etree
import lxml
from bs4 import BeautifulSoup

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.image import image_data_uri
try:
    import sass as libsass
except ImportError:
    libsass = None

DEFAULT_PRIMARY = '#000000'
DEFAULT_SECONDARY = '#000000'


class KsReportConfiguration(models.Model):
    _name = 'ks.report.configuration'
    _description = 'Report Configuration'

    @api.model
    def _default_h1_font(self):
        return "https://fonts.googleapis.com/css2?family=Roboto:wght@100&amp;display=swap"

    @api.model
    def _default_body_font(self):
        return "https://fonts.googleapis.com/css2?family=Roboto:wght@100&amp;display=swap"

    @api.model
    def _default_p_font(self):
        return "https://fonts.googleapis.com/css2?family=Roboto:wght@100&amp;display=swap"

    @api.model
    def _default_th_font(self):
        return "https://fonts.googleapis.com/css2?family=Roboto:wght@100&amp;display=swap"

    @api.model
    def _default_labels_font(self):
        return "https://fonts.googleapis.com/css2?family=Roboto:wght@100&amp;display=swap"

    name = fields.Char(string="Report Title")
    ks_is_custom_layout = fields.Boolean("Custom Layout", default=True)
    ks_extra_content_type = fields.Selection([('custom_content', 'Custom Content'), ('pdf', 'Upload PDF'), ('pdf_content','PDF & Custom Content')],
                                             string='Extra Content Type', required=True, default='custom_content')
    ks_upload_extra_content_pdf = fields.Binary(string='Upload PDF', attachment=True)
    ks_upload_pdf_name = fields.Char(translate=True)
    ks_model_id = fields.Many2one('ir.model', string='Model',
                                  help="Select Model For Report Selection.")
    ks_report_id = fields.Many2one('ir.actions.report', string='Report Name')
    ks_template_id = fields.Many2one("ir.ui.view", "Template")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    sale_report_style_id = fields.Many2one(
        'ks.sale.styles',
        string='Report Style',
    )
    ks_extra_content = fields.Html(string="Extra Content")
    ks_record_status = fields.Selection([
        ('sale_order', 'Sale'),
        ('purchase_order', 'Purchase'),
        ('RFQ', 'RFQ'),
        ('Invoice', 'Invoices'),
        ('Bill', 'Bills'),
        ('payment', 'Payments'),
        ('picking', 'Picking Slip'),
        ('delivery', 'delivery Notes'),
        ('progressive_quotation', 'Progressive Quotation'),
        ('progressive_invoice', 'Progressive Invoice'),
    ], string='Report Model')
    # Header Configuration
    ks_h1_font_color = fields.Char("Heading Text Color")
    ks_h1_font_size = fields.Integer("Heading Text Size (In px)", default=22, required=True, help="Font Size Between 10px to 30px")
    ks_heading_bold = fields.Boolean("Heading in Bold")
    ks_show_tagline = fields.Boolean(string='Show Tagline', default=True)
    ks_show_logo = fields.Boolean(string='Show Logo', default=True)
    ks_company_name_color = fields.Char("Company Name Color", )
    ks_company_font_size = fields.Integer("Company Name Font Size", default=22, required=True, help="Font Size Between 10px to 30px")
    ks_company_name_bold = fields.Boolean("Display Company Name in Bold")
    ks_total_value_color = fields.Char("Total Value Color", )
    ks_total_value_font_size = fields.Integer("Total Value Font Size", default=20, required=True, help="Font Size Between 10px to 30px")
    ks_show_company = fields.Boolean(string='Show Title', default=True)
    ks_company_logo_font_size = fields.Integer("Company Logo Size", required=True, default=50, help="Font Size Between 30px to 120px",)
    ks_company_logo_visibility = fields.Boolean(default=True)
    ks_company_logo = fields.Binary(related="company_id.logo",string="Company Logo")
    ks_show_taxes = fields.Boolean(string="Show Taxes",default=True)
    show_price = fields.Boolean(string="Show Price",default=True)
    show_quantity = fields.Boolean(string="Show Quantity",default=True)
    ks_discount = fields.Boolean(string="Show Discount")
    ks_display_company = fields.Boolean(string="Show Company Name",default=True)
    ks_address = fields.Boolean(string="Show Address",default=True)

    show_reg_no = fields.Boolean('Show Reg No',default=True)
    reg_no_type = fields.Selection([('gst','GST No'),('uen','UEN No')], string='Reg No Type', default='gst')
    phone = fields.Boolean(string="Show Phone",default=True)
    email = fields.Boolean(string="Show Email",default=True)

    # Table Configuration
    ks_table_head_text_color = fields.Char("Table Heading Text Color")
    ks_table_head_text_size = fields.Integer("Table Heading Text Size (In px)", default=16, required=True, help="Font Size Between 10px to 30px")
    ks_table_head_backgrnd_color = fields.Char("Table Heading Background Color")
    ks_table_odd_color = fields.Char("Table Odd Parity Color", )
    ks_table_even_color = fields.Char("Table Even Parity Color", )
    ks_product_image = fields.Boolean("Display Product Image", default=True, readonly=False)
    ks_product_desc = fields.Boolean("Display Product Description", default=True)
    ks_discount_total = fields.Boolean(string="Display Discount Total")
    display_internal_ref = fields.Boolean(string="Display Internal Reference No")

    # Total and Term's Configuration
    ks_amount_in_words = fields.Boolean("Display Amount in Words")
    ks_total_text_color = fields.Char("Total Text Color", )
    ks_total_bckgrnd_color = fields.Char("Total Background Color", )
    ks_total_text_size = fields.Integer("Total Text Size (In px)", default=16, required=True, help="Font Size Between 10px to 30px")

    ks_show_payment_method = fields.Boolean("Show Payment Method")
    ks_payment_history_text_color = fields.Char("Payment History Text Color")
    ks_payment_history_bckgrnd_color = fields.Char("Payment History Background Color")
    ks_payment_history_text_size = fields.Integer("Payment History Text Size (In px)", default=16,  required=True, help="Font Size Between 10px to 30px")

    # Footer Configuration
    ks_footnote = fields.Boolean("Display Foot Note", default=True)
    ks_footnote_text_color = fields.Char("Foot Note Text Color")
    ks_footnote_text_size = fields.Integer("Foot Note Text Size (In px)", default=16, required=True, help="Font Size Between 10px to 30px")
    is_custom_footer = fields.Boolean(string='Custom Footer')
    paynow_qr_code = fields.Boolean(string="PayNow QR Code")
    ks_footer = fields.Boolean(string="Display Footer Phone, Email and Website")

    # Water mark Configuration
    is_watermark = fields.Boolean(string='Is Watermark')
    ks_custom_water_mark_setting = fields.Boolean(string='Custom Water Mark')
    ks_upload_image = fields.Image("Upload Image", attachment=True, readonly=False, help="This field holds the image used for the badge, limited to 256x256")
    ks_rotate_image = fields.Boolean(string='Rotate', readonly=False)
    ks_watermark_option = fields.Selection(
        [('logo', 'Company Logo'), ('name', 'Company Name'), ('watermark_text', 'WaterMark Text'), ('backgroundimage', 'Background Image')],
        default='logo', string="Watermark " + "Option", readonly=False)
    ks_rotate_angle = fields.Integer(string='Rotate Angle', default=10, readonly=False)
    ks_temp_font_size = fields.Integer(string='Font Size', default=20, readonly=False, required=True, help="Font Size Between 10px to 30px")
    ks_font_color = fields.Char(string="Font Color", default="rgba(0,0,0,1)", readonly=False)
    ks_mark_text = fields.Text(string="Watermark Text", readonly=False)

    # common fields in all watermark
    ks_report_scale = fields.Selection([('1', 'Auto'), ('5', '500 %'), ('2', '200 %'), ('0.5', '50 %')],
                                            string="Scale Water-Mark ", default='1', readonly=False)
    ks_report_transparency = fields.Float('Transparency',  default=0.2, readonly=False,)
    ks_emailcc_partner_id = fields.Many2many(comodel_name='res.partner', string='Email Partner', readonly=False,
                                             domain="[('parent_id','!=', False), ('type','=','contact'), ('email','!=', False)]")

    ks_is_extra_content = fields.Boolean(string='Upload Extra Content')
    ks_report_footer = fields.Html(string='Report Footer', help="Small Content For Footer Notes", readonly=False, default=lambda s: _('Footer'))

    ks_show_signature = fields.Boolean(string='Show Signature')
    ks_signature = fields.Image('Signature', copy=False, attachment=True, readonly=False, help='Signature On Report.')
    ks_signed_by = fields.Char('Signed By', help='Name of the person that signed.', copy=False)
    ks_signed_on = fields.Date('Signed On', help='Date of the signature.', copy=False)

    ks_html_prv_changes = fields.Boolean("HTML preview changes", default=True)
    ks_preview = fields.Html(compute='_ks_compute_preview',
                             sanitize=False,
                             sanitize_tags=False,
                             sanitize_attributes=False,
                             sanitize_style=False,
                             sanitize_form=False,
                             strip_style=False,
                             strip_classes=False)
    customer_sign = fields.Boolean("Show Customer Sign")
    customer_sign_on_do = fields.Boolean("Show Customer Sign")
    show_style_label = fields.Boolean(string="Show Style Label In Report",compute="set_style_in_report")
    show_country = fields.Boolean(string="Show Country",default=True)
    show_comma = fields.Boolean(string="Add comma between Addresses")
    ks_show_space = fields.Boolean(string="Apply Space Between Table Row",default=False)
    hide_table_border = fields.Boolean(string="Hide border on Invoice table",default=False)
    image_attachment_ids = fields.Many2many("ir.attachment",string="Upload")
    display_currency_separately = fields.Boolean(string="Display Currency Separately",default=False)
    display_terms_next_page = fields.Boolean(string="Display T&C on Next Page",default=False)
    hide_product_label = fields.Boolean(string="Hide Product Label",default=False)
    display_qty_as_integer = fields.Boolean(string="Display Quantity as Integer",default=False)
    display_total_amount = fields.Boolean(string="Display Total Amount",default=True)
    show_so = fields.Boolean(string="Show SO",default=True)
    show_reference = fields.Boolean(string="Show Reference",default=True)
    display_currency_name = fields.Boolean(string="Display Currency Name",default=False)
    # show_report_header_left = fields.Boolean(string="Show Report Header Left",default=False)
    # show_report_header_center = fields.Boolean(string="Show Report Header Center",default=False)

    show_report_header_position = fields.Selection([
                                ('right', 'Right'),
                                ('left', 'Left'),
                                ('center', 'Center')],
                                string="Report Header Position",
                                default='right'
                            )
    is_name_split_required = fields.Boolean("Split name into two lines in reports",default=False)
    show_uen_no = fields.Boolean("Show UEN No",default=False)
    show_due_date = fields.Boolean("Show Due Date",default=True)
    show_payment_terms = fields.Boolean("Show Payment Terms",default=True)
    show_aging_analysis = fields.Boolean("Show Aging Analysis",default=False)
    aging_type = fields.Selection([('days','Days'),('months','Months')], string='Aging Type', default='days')
    show_address_table = fields.Boolean("Show Address Table",default=False)
    mct_report_style = fields.Boolean(string="Show MCT Report Style",compute="set_mct_report_style")
    lite_report_style = fields.Boolean(string="Show Lite Report Style",compute="set_lite_report_style")
    show_item = fields.Boolean(string="Show Item", default=True)
    show_uom = fields.Boolean(string="Show UOM", default=False)
    hide_uom = fields.Boolean(string="Hide UOM", default=False)
    use_static_qr = fields.Boolean("Use Static PayNow QR")
    static_qr_image = fields.Binary("Static QR Code Image")
    change_signature_position = fields.Boolean(string="Change Signature Position", default=False)
    show_decimal = fields.Boolean(string="Show Decimal", default=False)
    show_user_signature = fields.Boolean(string="Show User Signature",default=False)
    display_large_logo = fields.Boolean(string="Display Long Width Logo (Hide Tagline)",default=False)
    move_address_right = fields.Boolean(string="Move Invoice Address to Right",default=False)
    display_note_section = fields.Boolean(string="Display SO note & section",default=False)
    show_backorder = fields.Boolean(string="Show Backorders",default=True)
    increase_font_size = fields.Boolean(string="Increase Font Size",default=False)
    display_page_number = fields.Boolean(string="Display Page No",default=True)
    show_image = fields.Boolean(string="Show Image",default=False)
    show_remark = fields.Boolean(string="Show Remarks Instead of Terms & Conditions",default=False)
    show_delivery_date = fields.Boolean(string="Show Delivery Date",default=False)

    # @api.depends("sale_report_style_id")
    # def set_style_in_report(self):
    #     if self.sale_report_style_id:
    #         if self.sale_report_style_id and self.sale_report_style_id.name=="Minimalist" or self.sale_report_style_id.name=="MCT":
    #             self.show_style_label = True
    #         else:
    #             self.show_style_label = False

    @api.depends("sale_report_style_id")
    def set_style_in_report(self):
        for rec in self:
            if rec.sale_report_style_id and rec.sale_report_style_id.name in ("Minimalist", "MCT", "Lite"):
                rec.show_style_label = True
            else:
                rec.show_style_label = False
                

    @api.depends("sale_report_style_id")
    def set_mct_report_style(self):
        for rec in self:
            if rec.sale_report_style_id and rec.sale_report_style_id.name=="MCT":
                rec.mct_report_style = True
            else:
                rec.mct_report_style = False

    @api.depends("sale_report_style_id")
    def set_lite_report_style(self):
        for rec in self:
            if rec.sale_report_style_id and rec.sale_report_style_id.name=="Lite":
                rec.lite_report_style = True
            else:
                rec.lite_report_style = False






    def ks_button_reset_settings(self):

        self.ks_h1_font_size = self.ks_company_font_size = 22
        self.ks_company_logo_font_size = 50
        self.ks_total_value_font_size = 20
        self.ks_footnote_text_size = self.ks_payment_history_text_size = self.ks_temp_font_size = self.ks_total_text_size =\
            self.ks_table_head_text_size = 16
        self.ks_report_transparency = 0.2
        self.ks_watermark_option = 'logo'
        self.ks_report_scale = '1'
        self.ks_rotate_angle = 10
        self.ks_font_color = 'rgba(0,0,0,1)'

        self.ks_h1_font_color = self.ks_heading_bold = self.ks_company_name_color = self.ks_company_name_bold =\
            self.ks_total_value_color = self.ks_table_head_text_color = self.ks_table_head_backgrnd_color = \
            self.ks_table_odd_color = self.ks_table_even_color = self.ks_footnote_text_color = self.is_custom_footer = \
            self.ks_amount_in_words = self.ks_total_text_color = self.ks_total_bckgrnd_color = \
            self.ks_payment_history_text_color = self.ks_payment_history_bckgrnd_color = self.ks_show_payment_method = \
            self.is_watermark = self.ks_custom_water_mark_setting = self.ks_upload_image = self.ks_rotate_image =\
            self.ks_mark_text = self.ks_show_signature =\
            self.is_custom_footer = self.ks_report_footer = self.ks_is_extra_content = False
        self.ks_show_tagline = self.ks_show_logo = self.ks_show_company = self.ks_footnote = self.ks_product_image = self.ks_product_desc = True

    @api.onchange('ks_upload_extra_content_pdf')
    def _onchange_pdf(self):
        if self.ks_upload_extra_content_pdf:
            mimetype = mimetypes.guess_type(self.ks_upload_pdf_name)[0]
            if 'pdf' not in mimetype:
                raise UserError('File Format Allowed : Pdf')

    @api.onchange('ks_discount')
    def _onchange_show_discount(self):
        if self.ks_discount:
            self.ks_discount_total = True
        else:
            self.ks_discount_total = False

    @api.onchange('ks_h1_font_size', 'ks_company_font_size','ks_company_logo_font_size', 'ks_total_value_font_size', 'ks_table_head_text_size',
                  'ks_total_text_size', 'ks_payment_history_text_size', 'ks_footnote_text_size', 'ks_temp_font_size')
    def _onchange_font_sie(self):
        if not (10 <= self.ks_footnote_text_size <= 18):
            raise UserError('Font Size/Text For Footer Must Be Between 10px to 18px')
        if not (10 <= self.ks_h1_font_size <= 30 and 10 <= self.ks_company_font_size <= 30 and
                10 <= self.ks_total_value_font_size <= 30 and 10 <= self.ks_table_head_text_size <= 30
                and 10 <= self.ks_total_text_size <= 30 and 10 <= self.ks_payment_history_text_size <= 30
                and 10 <= self.ks_temp_font_size <= 30):
            raise UserError('Font Size/Text Must Be Between 10px to 30px')

        if self.sale_report_style_id.name == 'Contemporary' or self.sale_report_style_id.name == 'Clean' \
                or self.sale_report_style_id.name == 'Modern':
            if not (50 <= self.ks_company_logo_font_size <= 90):
                raise UserError('Logo Size Must Be Between 50px to 90px')

        if self.sale_report_style_id.name == 'Advanced':
            if not (50 <= self.ks_company_logo_font_size <= 90):
                raise UserError('Logo Size Must Be Between 50px to 90px')

        if self.sale_report_style_id.name == 'Exclusive' or self.sale_report_style_id.name == 'Elegant' \
                or self.sale_report_style_id.name == 'Retro' or self.sale_report_style_id.name == 'Classic'\
                or self.sale_report_style_id.name == 'Slim' or self.sale_report_style_id.name == 'Professional':
            if not (50 <= self.ks_company_logo_font_size <= 130):
                raise UserError('Logo Size Must Be Between 50px to 130px')
            
        if self.sale_report_style_id.name == 'Minimalist':
            pass
        if self.sale_report_style_id.name == 'MCT':
            pass
        


    @api.onchange('ks_report_transparency')
    def _onchange_transparency(self):
        if not 0 <= self.ks_report_transparency <= 1:
            raise UserError('Transparency Must Be Between 0 to 1')


    @api.depends('ks_h1_font_color', 'ks_h1_font_size', 'ks_heading_bold', 'ks_show_tagline', 'ks_show_logo', 'ks_show_company', 'ks_company_name_color',
                 'ks_company_font_size','ks_company_logo_font_size', 'ks_company_name_bold', 'ks_total_value_color', 'ks_total_value_font_size',
                 'ks_table_head_text_color', 'ks_table_head_text_size', 'ks_table_head_backgrnd_color',
                 'ks_table_odd_color', 'ks_table_even_color', 'ks_product_desc', 'ks_product_image',
                 'ks_footnote', 'ks_footnote_text_color', 'ks_footnote_text_size', 'is_custom_footer',
                 'ks_amount_in_words', 'ks_total_text_color', 'ks_total_bckgrnd_color', 'ks_total_text_size',
                 'ks_payment_history_text_color', 'ks_payment_history_text_size', 'ks_show_payment_method', 'ks_payment_history_bckgrnd_color',
                 'is_watermark', 'ks_custom_water_mark_setting', 'ks_upload_image', 'ks_rotate_image', 'ks_watermark_option',
                 'ks_rotate_angle', 'ks_temp_font_size', 'ks_font_color', 'ks_mark_text', 'ks_report_scale', 'ks_report_transparency','paynow_qr_code',
                 'image_attachment_ids','sale_report_style_id', 'ks_report_footer', 'ks_show_signature', 'ks_signature','show_reg_no','reg_no_type',
                 'phone','email','ks_show_space','hide_table_border','ks_address','ks_company_logo','ks_show_taxes','ks_discount','ks_footer',
                 'ks_display_company','customer_sign','ks_discount_total','customer_sign_on_do','show_country','display_currency_separately','hide_product_label',
                 'display_qty_as_integer','display_total_amount','show_price','show_quantity','show_so','show_reference','display_currency_name','display_internal_ref',
                 'show_report_header_position','is_name_split_required','show_uen_no','show_due_date','show_payment_terms','show_aging_analysis','show_address_table','show_item',
                 'show_uom','aging_type','use_static_qr','change_signature_position','hide_uom','show_decimal','show_user_signature','display_large_logo','move_address_right','display_note_section',
                 'show_backorder','increase_font_size','display_page_number','show_image','show_remark','show_delivery_date',
                 )
    

    def _ks_compute_preview(self):
        for ks_report in self:
            if ks_report:
                self.env.company._update_asset_style()
                if ks_report.sale_report_style_id.id:
                    ks_dummy_temp_id = "ks_custom_report_layouts.ks_sales_report_dummy_layout_%s" % ks_report.sale_report_style_id.id

                else:
                    ks_dummy_temp_id = "ks_custom_report_layouts.ks_sales_report_dummy_layout_1"

                if ks_report.ks_custom_water_mark_setting:
                    ks_upload_image_id = ks_report.env['ir.attachment'].sudo().search([('res_field', '=', 'ks_upload_image'),
                                       ('res_model', '=', 'ks.report.configuration'),('res_id', '=', ks_report.ids[0])], limit=1).id if ks_report.ids else False
                else:
                    ks_upload_image_id = ks_report.env['ir.attachment'].sudo().search([('res_field', '=', 'ks_upload_image'),
                                     ('res_model', '=', 'res.company'), ('company_id', '=', self.company_id.id)], limit=1).id
                ks_sign_id = ks_report.env['ir.attachment'].sudo().search([('res_field', '=', 'ks_signature'), ('res_id', '=', ks_report.ids[0])], limit=1).id if ks_report.ids else False
                ks_logo_id = ks_report.env['ir.attachment'].sudo().search([('res_field', '=', 'image_1920'),
                                                                           ('res_model', '=', 'res.partner'), ('res_id', '=', self.company_id.partner_id.id)], limit=1).id if ks_report.ids else False
                ks_report.ks_preview = ks_report.env['ir.ui.view']._render_template(ks_dummy_temp_id,
                                                                   {'wizard': self,
                                                                    'res_config': ks_report,
                                                                    'report_name': ks_report.name,
                                                                    'company': self.company_id,
                                                                    'ks_upload_image_id': ks_upload_image_id,
                                                                    'ks_sign_id': ks_sign_id,
                                                                    'ks_logo_id': ks_logo_id,
                                                                    })
                ks_report.ks_html_prv_changes = True

    def ks_preview_pdf(self):
        pdf_content = False
        action_report = self.env['ir.actions.report']
        if action_report.get_wkhtmltopdf_state() == 'install':
            raise UserError(_("Unable to find Wkhtmltopdf on this system. The PDF can not be created."))
        if self.ks_html_prv_changes:
            bodies, header, footer = self.ks_pdf_prvw_html(self.ks_preview)
            pdf_content = action_report._run_wkhtmltopdf(
                bodies,
                header=header,
                footer=footer,
                landscape=None,
                specific_paperformat_args=None,
            )
        ka_attachment_name = self.name + ' ' + self.sale_report_style_id.name + 'style'
        attachment = self.env['ir.attachment'].sudo().search([('name', '=', ka_attachment_name), ('res_id', '=', self.id)])
        if pdf_content:
            if attachment:
                if self.ks_html_prv_changes:
                    attachment.datas = base64.encodebytes(pdf_content)
            else:
                attachment = self.env['ir.attachment'].create({
                    'type': 'binary',
                    'name': ka_attachment_name,
                    'mimetype': 'application/pdf',
                    'res_model': 'ks.report.configuration',
                    'res_id': self.id,
                    'datas': base64.encodebytes(pdf_content),
                })
        self.ks_html_prv_changes = False
        

        return {
            'type': 'ir.actions.client',
            'tag': 'ks_view_report_pdf',
            'params': {'attachment_id': attachment.id}
        }

    def ks_pdf_prvw_html(self, html):
        IrConfig = self.env['ir.config_parameter'].sudo()
        base_url = IrConfig.get_param('report.url') or IrConfig.get_param('web.base.url')

        layout = self.env.ref('web.minimal_layout', False)
        if not layout:
            return {}
        layout = self.env['ir.ui.view'].browse(self.env['ir.ui.view'].get_view_id('web.minimal_layout'))

        root = lxml.html.fromstring(html)
        match_klass = "//div[contains(concat(' ', normalize-space(@class), ' '), ' {} ')]"

        header_node = etree.Element('div', id='minimal_layout_report_headers')
        footer_node = etree.Element('div', id='minimal_layout_report_footers')
        bodies = []

        # body_parent = root.xpath('//main')[0]
        # Retrieve headers
        for node in root.xpath(match_klass.format('header')):
            body_parent = None
            body_parent = node.getparent()
            node.getparent().remove(node)
            header_node.append(node)

        # Retrieve footers
        for node in root.xpath(match_klass.format('footer')):
            body_parent = node.getparent()
            node.getparent().remove(node)
            footer_node.append(node)

        # Retrieve bodies
        for node in root.xpath(match_klass.format('article')):
            layout_with_lang = layout
            # set context language to body language
            if node.get('data-oe-lang'):
                layout_with_lang = layout_with_lang.with_context(lang=node.get('data-oe-lang'))
            body = layout_with_lang._render(dict(subst=False, body=lxml.html.tostring(node), base_url=base_url))
            bodies.append(body)

        if not bodies:
            body = bytearray().join([lxml.html.tostring(c) for c in body_parent.getchildren()])
            bodies.append(body)

        header = layout._render(dict(subst=True, body=lxml.html.tostring(header_node), base_url=base_url))
        footer = layout._render(dict(subst=True, body=lxml.html.tostring(footer_node), base_url=base_url))

        return bodies, header, footer

    def get_report_header_color(self):
        report_stylesheet = ''
        # Header SCSS
        if self.ks_h1_font_color:
            report_stylesheet += '.ks_h1_font_color { ' \
                                 'color: ' + self.ks_h1_font_color + '!important; } '
        if self.ks_company_name_color:
            report_stylesheet += ' .ks_company_name_color { ' \
                                 'color: ' + self.ks_company_name_color + '!important; } '
        if self.ks_total_value_color:
            report_stylesheet += ' .ks_total_value_color { ' \
                                 'color: ' + self.ks_total_value_color + '!important; } '
        if self.ks_company_name_bold:
            report_stylesheet += ' .ks_company_name_bold { ' \
                                 'font-weight: bold !important;} '
        if self.ks_heading_bold:
            report_stylesheet += ' .ks_heading_bold { ' \
                                 'font-weight: bold !important;} '
        if self.ks_h1_font_size:
            report_stylesheet += ' .ks_h1_font_size  { ' \
                                 'font-size: ' + str(self.ks_h1_font_size) + 'px !important; } '
        if self.ks_company_font_size:
            report_stylesheet += ' .ks_company_font_size  { ' \
                                 'font-size: ' + str(self.ks_company_font_size) + 'px !important; } '

        if self.ks_total_value_font_size:
            report_stylesheet += ' .ks_total_value_font_size  { ' \
                                 'background-image: ' + str(self.ks_total_value_font_size) + '% !important; } '

        if self.sale_report_style_id.name == 'Contemporary' or self.sale_report_style_id.name == 'Clean':
            if self.ks_company_logo_font_size:
                report_stylesheet += ' .ks_company_logo_font_size  { ' \
                                     'max-width: ' + str(self.ks_company_logo_font_size) + 'px !important; ' \
                                     'max-height: ' + str(self.ks_company_logo_font_size) + 'px !important; ''} '
            if self.ks_show_company == True and self.ks_company_logo_font_size > 50:
                report_stylesheet += ' .ks_company_logo_font_size  { ' \
                                     'margin-left: ' + '-50' + 'px !important; ''} '

            if self.ks_show_company == True and self.ks_company_logo_font_size == 50:
                report_stylesheet += ' .ks_company_logo_font_size  { ' \
                                     'margin-left: ' + '-10' + 'px !important; ''} '

            if self.ks_show_company == False:
                report_stylesheet += ' .ks_company_logo_font_size  { ' \
                                     'margin-left: ' + '50' + 'px !important; ''} '

        if self.sale_report_style_id.name == 'Professional':
            if self.ks_company_logo_font_size:
                report_stylesheet += ' .ks_company_logo_font_size  { ' \
                                     'max-width: ' + str(self.ks_company_logo_font_size) + 'px !important; ' \
                                                                                           'max-height: ' + str(
                    self.ks_company_logo_font_size) + 'px !important; ''} '
            # if self.ks_show_company == True and self.ks_company_logo_font_size > 50:
            #     report_stylesheet += ' .ks_company_logo_font_size  { ' \
            #                          'margin-left: ' + '-50' + 'px !important; ''} '

            if self.ks_show_company == True and self.ks_company_logo_font_size == 50:
                report_stylesheet += ' .ks_company_logo_font_size  { ' \
                                     'margin-left: ' + '-10' + 'px !important; ''} '

            if self.ks_show_company == False:
                report_stylesheet += ' .ks_company_logo_font_size  { ' \
                                     'margin-left: ' + '50' + 'px !important; ''} '

        if self.sale_report_style_id.name == 'Advanced' or self.sale_report_style_id.name == 'Exclusive' or self.sale_report_style_id.name == 'Elegant' \
                or self.sale_report_style_id.name == 'Retro':
            if self.ks_company_logo_font_size:
                report_stylesheet += ' .ks_company_logo_font_size  { ' \
                                     'max-width: ' + str(self.ks_company_logo_font_size) + 'px !important; ' \
                                     'max-height: ' + str(self.ks_company_logo_font_size) + 'px !important; ''} '

        if self.sale_report_style_id.name == 'Modern':
            if self.ks_company_logo_font_size:
                report_stylesheet += ' .ks_company_logo_font_size  { ' \
                                     'max-width: ' + str(self.ks_company_logo_font_size) + 'px !important; ' \
                                     'max-height: ' + str(self.ks_company_logo_font_size) + 'px !important; ''} '
            if self.ks_show_company == False and self.ks_company_logo_font_size > 50:
                report_stylesheet += ' .ks_company_logo_font_size  { ' \
                                     'margin-left: ' + '-50' + 'px !important; ''} '

        if self.sale_report_style_id.name == 'Classic' or self.sale_report_style_id.name == 'Slim':
            if self.ks_company_logo_font_size:
                report_stylesheet += ' .ks_company_logo_font_size  { ' \
                                     'max-width: ' + str(self.ks_company_logo_font_size) + 'px !important; ' \
                                     'max-height: ' + str(self.ks_company_logo_font_size) + 'px !important; ''} '
                
        if self.sale_report_style_id.name == 'Minimalist':
            pass
        if self.sale_report_style_id.name == 'MCT':
            pass
        



        return report_stylesheet

    def get_report_table_color(self):
        report_stylesheet = ''
        if self.ks_heading_bold:
            report_stylesheet += ' .ks_heading_bold { ' \
                                 'font-weight: bold !important;} '
        if self.ks_h1_font_color:
            report_stylesheet += '.ks_h1_font_color { ' \
                                 'color: ' + self.ks_h1_font_color + '!important; } '
        if self.ks_h1_font_size:
            report_stylesheet += ' .ks_h1_font_size  { ' \
                                 'font-size: ' + str(self.ks_h1_font_size) + 'px !important; } '
        # Table SCSS
        if self.ks_table_head_text_size:
            report_stylesheet += ' .ks_table_head_text_size  { ' \
                                 'font-size: ' + str(self.ks_table_head_text_size) + 'px !important; } '
        if self.ks_table_odd_color:
            report_stylesheet += ' .ks_table_odd_color { ' \
                                 'background: ' + self.ks_table_odd_color + '!important; } '
        if self.ks_table_even_color:
            report_stylesheet += ' .ks_table_even_color { ' \
                                 'background: ' + self.ks_table_even_color + '!important; } '
        if self.ks_table_head_text_color:
            report_stylesheet += ' .ks_table_head_text_color { ' \
                                 'color: ' + self.ks_table_head_text_color + '!important; }'
        if self.ks_table_head_backgrnd_color:
            report_stylesheet += ' .ks_table_head_backgrnd_color { ' \
                                 'background-color: ' + self.ks_table_head_backgrnd_color + '!important; } '\
                                '.ks_hide_design_4.ks_table_head_backgrnd_color {'\
                                'display: none !important;}' \
                                '.ks_table_design_4.ks_table_head_backgrnd_color.ks_table_head_text_color.ks_table_head_text_size{' \
                                'position: static !important;}' \
                                '.ks_table_design_4.ks_table_head_backgrnd_color {' \
                                'border-bottom-right-radius: 0px !important; }'

        if self.ks_total_value_color:
            report_stylesheet += ' .ks_total_value_color { ' \
                                 'color: ' + self.ks_total_value_color + '!important; } '

        if self.ks_total_value_font_size:
            report_stylesheet += ' .ks_total_value_font_size  { ' \
                                 'font-size: ' + str(self.ks_total_value_font_size) + 'px !important; } '

        # Amount in words
        if self.ks_total_text_color:
            report_stylesheet += ' .ks_total_text_color { ' \
                                 'color: ' + self.ks_total_text_color + '!important; } '
        if self.ks_total_bckgrnd_color:
            report_stylesheet += ' .ks_total_bckgrnd_color { ' \
                                 'background-color: ' + self.ks_total_bckgrnd_color + '!important; } '\
                                '.ks_total_bckgrnd_color.ks_hide_design_4 {'\
                                'display : none !important }'
        if self.ks_total_text_size:
            report_stylesheet += ' .ks_total_text_size  { ' \
                                 'font-size: ' + str(self.ks_total_text_size) + 'px !important; } '
        if self.name == 'Invoice':
            if self.ks_payment_history_text_color:
                report_stylesheet += ' .ks_payment_history_text_color { ' \
                                     'color: ' + self.ks_payment_history_text_color + '!important; } '
            if self.ks_payment_history_bckgrnd_color:
                report_stylesheet += ' .ks_payment_history_bckgrnd_color { ' \
                                     'background-color: ' + self.ks_payment_history_bckgrnd_color + '!important; } '
            if self.ks_payment_history_text_size:
                report_stylesheet += ' .ks_payment_history_text_size  { ' \
                                     'font-size: ' + str(self.ks_payment_history_text_size) + 'px !important; } '
        return report_stylesheet

    def get_report_footer_color(self):
        report_stylesheet = ''
        # Footer SCSS
        if self.ks_footnote_text_color:
            report_stylesheet += ' .ks_footnote_text_color { ' \
                                 'color: ' + self.ks_footnote_text_color + '!important; } '
        if self.ks_footnote_text_size:
            report_stylesheet += ' .ks_footnote_text_size  { ' \
                                 'font-size: ' + str(self.ks_footnote_text_size) + 'px !important; } '

        return report_stylesheet



    @api.model
    def ks_create_records(self):
        company_ids = self.env['res.company'].sudo().search([]).ids
        reports = [
            {'name': 'Sales', 'ks_model_id': 'sale.model_sale_order',
            'ks_report_id': 'sale.action_report_saleorder', 'ks_record_status': 'sale_order'},
            {'name': 'Invoice', 'ks_model_id': 'account.model_account_move',
            'ks_report_id': 'account.account_invoices', 'ks_record_status': 'Invoice'},
            {'name': 'Bill', 'ks_model_id': 'account.model_account_move',
            'ks_report_id': 'account.account_invoices', 'ks_record_status': 'Bill'},
            {'name': 'Purchase Order', 'ks_model_id': 'purchase.model_purchase_order',
            'ks_report_id': 'purchase.action_report_purchase_order', 'ks_record_status': 'purchase_order'},
            {'name': 'Purchase RFQ', 'ks_model_id': 'purchase.model_purchase_order',
            'ks_report_id': 'purchase.report_purchase_quotation', 'ks_record_status': 'RFQ'},
            {'name': 'Payment Receipts', 'ks_model_id': 'account.model_account_payment',
            'ks_report_id': 'account.action_report_payment_receipt', 'ks_record_status': 'payment'},
            {'name': 'Picking Slip', 'ks_model_id': 'stock.model_stock_picking',
            'ks_report_id': 'stock.action_report_picking', 'ks_record_status': 'picking'},
            {'name': 'Delivery Note', 'ks_model_id': 'stock.model_stock_picking',
            'ks_report_id': 'stock.action_report_delivery', 'ks_record_status': 'delivery'},
            {'name': 'Progressive Quotation', 'ks_model_id': 'metroerp_progressive_billing.model_progressive_billing_qt',
            'ks_report_id': 'ks_custom_report_layouts.action_ks_pro_billl_quotation_report', 'ks_record_status': 'progressive_quotation'},
            {'name': 'Progressive Invoice', 'ks_model_id': 'account.model_account_move',
            'ks_report_id': 'ks_custom_report_layouts.action_progressive_invoice_report', 'ks_record_status': 'progressive_invoice'},
        ]
        
        for company_id in company_ids:
            existing_reports = self.env['ks.report.configuration'].sudo().search([('company_id', '=', company_id)])
            existing_report_names = existing_reports.mapped('name')
            
            for report in reports:
                if report['name'] not in existing_report_names:
                    self.env['ks.report.configuration'].create({
                        'name': report['name'],
                        'sale_report_style_id': self.env.ref('ks_custom_report_layouts.ks_sale_styles_11').id,
                        'ks_model_id': self.env.ref(report['ks_model_id']).id,
                        'ks_report_id': self.env.ref(report['ks_report_id']).id,
                        'ks_record_status': report['ks_record_status'],
                        'company_id': company_id,
                    })

