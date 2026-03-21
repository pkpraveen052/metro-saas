from odoo import models, fields, api, _
import os
import qrcode
import base64
import re
from io import BytesIO
from PIL import Image
import pycrc.algorithms
from odoo.modules.module import get_module_resource
from num2words import num2words
from collections import defaultdict
from odoo.tools.misc import formatLang, format_date, get_lang
from odoo.exceptions import UserError,ValidationError

class KsAccountMove(models.Model):
    _inherit = 'account.move'

    ks_total_amount_in_words = fields.Text(string='Total Amount (In Words)', compute="_set_amount_total_in_words")
    price_total = fields.Monetary(string='Total', store=True, readonly=True)
    company_country_code = fields.Char(related='company_id.country_id.code',store=True,readonly=True)

    # uen_number = fields.Char(string="UEN", related='company_id.uen_number',readonly=False,tracking=True)
    # alt_uen_number = fields.Char(string="Secondary UEN", related='company_id.alt_uen_number',readonly=False,tracking=True)
    # mobile_number = fields.Char(string="Mobile Number", related='company_id.mobile_number',readonly=False,tracking=True)

    uen_number = fields.Char(string="UEN", compute='_compute_uen_number', inverse='_inverse_uen_number', store=True)
    alt_uen_number = fields.Char(string="Secondary UEN", compute='_compute_alt_uen_number', inverse='_inverse_alt_uen_number', store=True)
    mobile_number = fields.Char(string="Mobile Number", compute='_compute_mobile_number', inverse='_inverse_mobile_number', store=True)

    use_uen_number = fields.Boolean("Use UEN",tracking=True)
    use_alt_uen_number = fields.Boolean("Use Alt UEN",tracking=True)
    use_mobile_number = fields.Boolean("Use Mobile",tracking=True)

    @api.depends('company_id')
    def _compute_uen_number(self):
        for rec in self:
            rec.uen_number = rec.company_id.uen_number

    def _inverse_uen_number(self):
        for rec in self:
            rec.company_id.sudo().uen_number = rec.uen_number

    @api.depends('company_id')
    def _compute_alt_uen_number(self):
        for rec in self:
            rec.alt_uen_number = rec.company_id.alt_uen_number

    def _inverse_alt_uen_number(self):
        for rec in self:
            rec.company_id.sudo().alt_uen_number = rec.alt_uen_number

    @api.depends('company_id')
    def _compute_mobile_number(self):
        for rec in self:
            rec.mobile_number = rec.company_id.mobile_number

    def _inverse_mobile_number(self):
        for rec in self:
            rec.company_id.sudo().mobile_number = rec.mobile_number

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


    @api.model
    def create(self, vals):
        # Get company ID from vals or fallback to current company
        company_id = vals.get('company_id') or self.env.company.id
        company = self.env['res.company'].browse(company_id)

        # Update vals from company settings
        vals['use_uen_number'] = company.use_uen_number
        vals['use_alt_uen_number'] = company.use_alt_uen_number
        vals['use_mobile_number'] = company.use_mobile_number

        return super(KsAccountMove, self).create(vals)
    

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


   
    @api.depends('amount_total')
    def _set_amount_total_in_words(self):
        for rec in self:
            if rec.currency_id:
                rec.ks_total_amount_in_words = rec.currency_id.amount_to_text(rec.amount_total, rec.partner_id.lang)
            else:
                rec.ks_total_amount_in_words = ''
    def action_invoice_sent(self):
        result = super(KsAccountMove, self).action_invoice_sent()
        company_id = self.company_id.id if self.company_id else self.env.company.id
        report_ui_id = self.env['ks.report.configuration'].search([("ks_record_status", "=", 'Invoice'), ("company_id", "=", company_id)], limit=1)
        result['context']['ks_mail_cc'] = report_ui_id.ks_emailcc_partner_id.mapped('email') if len(report_ui_id.ks_emailcc_partner_id.mapped('email')) else self.company_id.ks_emailcc_partner_id.mapped('email')
        return result
    

    
    def generate_qrcode(self):
        print(">>> NEW generate_qrcode() STARTED >>>")

        PayNow_ID = ''
        Proxy_type = '2'  # Default to UEN

        if self.use_uen_number:
            original_input = str(self.uen_number or '').strip()
            # Clean UEN input: remove spaces and special characters, keeping letters and digits
            cleaned_input = re.sub(r"[^a-zA-Z0-9]", "", original_input)  # Remove anything that's not a letter or digit

            # Log for cleaning process (if needed)
            if original_input != cleaned_input:
                self.message_post(body=f"⚠️ <b>UEN Number Cleaned:</b><br/>"
                                    f"Original input: <code>{original_input}</code><br/>"
                                    f"Cleaned input: <code>{cleaned_input}</code><br/>"
                                    f"<i>Spaces and special characters have been removed.</i>")

            PayNow_ID = cleaned_input
            Proxy_type = "2"  # UEN

        elif self.use_alt_uen_number:
            original_input = str(self.alt_uen_number or '').strip()
            # Clean Alternative UEN input: remove spaces and special characters, keeping letters and digits
            cleaned_input = re.sub(r"[^a-zA-Z0-9]", "", original_input)  # Remove anything that's not a letter or digit

            # Log for cleaning process (if needed)
            if original_input != cleaned_input:
                self.message_post(body=f"⚠️ <b>Alternative UEN Number Cleaned:</b><br/>"
                                    f"Original input: <code>{original_input}</code><br/>"
                                    f"Cleaned input: <code>{cleaned_input}</code><br/>"
                                    f"<i>Spaces and special characters have been removed.</i>")

            PayNow_ID = cleaned_input
            Proxy_type = "2"  # UEN

        elif self.use_mobile_number:
            original_input = str(self.mobile_number or '').strip()

            # Clean input: remove spaces and special characters except '+'
            cleaned_input = re.sub(r"\s+", "", original_input)  # Remove spaces
            cleaned_input = re.sub(r"[^\d+]", "", cleaned_input)  # Remove special characters

            if original_input != cleaned_input:
                self.message_post(body=f"⚠️ <b>Mobile Number Cleaned:</b> <code>{original_input}</code> -> <code>{cleaned_input}</code>")

            # Validation and formatting
            if re.fullmatch(r'\+65\d{8}', cleaned_input):
                PayNow_ID = cleaned_input
            elif re.fullmatch(r'\d{8}', cleaned_input):
                PayNow_ID = '+65' + cleaned_input
            else:
                if len(cleaned_input) < 8:
                    error_msg = "⚠️ Mobile number is too short. Please enter exactly 8 digits or +65 followed by 8 digits."
                elif len(cleaned_input) > 8:
                    error_msg = "⚠️ Mobile number is too long. Please enter exactly 8 digits or +65 followed by 8 digits."
                else:
                    error_msg = "⚠️ Invalid mobile number. Please remove spaces, special characters, and ensure correct format."

                self.message_post(body=error_msg)
                return False  # Stop further processing

            Proxy_type = "0"  # Mobile Number

        if not PayNow_ID:
            company_uen = str(self.company_id.l10n_sg_unique_entity_number or '').strip()
            if company_uen:
                PayNow_ID = company_uen
                Proxy_type = "2"  # UEN
            else:
                self.message_post(body="⚠️ <b>No valid PayNow ID found</b>: Please select a QR code option on the invoice or ensure a UEN is set in the company settings.")
                return False

        # Standard QR fields
        Merchant_name = self.company_id.name or ''
        Bill_number = self.name or ''
        Transaction_amount = "{:.2f}".format(self.amount_total or 0.0)

        Can_edit_amount = "0"
        Merchant_category = "0000"
        Transaction_currency = "702"
        Country_code = "SG"
        Merchant_city = "Singapore"
        Globally_Unique_ID = "SG.PAYNOW"

        start_string = "010212"
        Dynamic_PayNow_QR = "000201"
        Merchant_Account_Info_field = "26"
        Globally_Unique_ID_field = "00"
        Proxy_type_field = "01"
        PayNow_ID_field = "02"
        Can_edit_amount_field = "03"

        merchant_account_info_value = (
            Globally_Unique_ID_field + str(len(Globally_Unique_ID)).zfill(2) + Globally_Unique_ID +
            Proxy_type_field + str(len(Proxy_type)).zfill(2) + Proxy_type +
            PayNow_ID_field + str(len(PayNow_ID)).zfill(2) + PayNow_ID +
            Can_edit_amount_field + str(len(Can_edit_amount)).zfill(2) + Can_edit_amount
        )
        Merchant_Account_Info_length = str(len(merchant_account_info_value)).zfill(2)

        Transaction_amount_field = "54"
        Country_code_field = "58"
        Merchant_name_field = "59"
        Merchant_city_field = "60"
        Bill_number_field = "62"

        bill_reference = "01" + str(len(Bill_number)).zfill(2) + Bill_number
        bill_reference_length = str(len(bill_reference)).zfill(2)

        data_for_crc = (
            Dynamic_PayNow_QR + start_string +
            Merchant_Account_Info_field + Merchant_Account_Info_length + merchant_account_info_value +
            "52" + "04" + Merchant_category +
            "53" + "03" + Transaction_currency +
            Transaction_amount_field + str(len(Transaction_amount)).zfill(2) + Transaction_amount +
            Country_code_field + str(len(Country_code)).zfill(2) + Country_code +
            Merchant_name_field + str(len(Merchant_name)).zfill(2) + Merchant_name +
            Merchant_city_field + str(len(Merchant_city)).zfill(2) + Merchant_city +
            Bill_number_field + bill_reference_length + bill_reference +
            "6304"
        )

        crc = pycrc.algorithms.Crc(
            width=16, poly=0x1021,
            reflect_in=False, xor_in=0xffff,
            reflect_out=False, xor_out=0x0000
        )
        my_crc = crc.bit_by_bit_fast(data_for_crc)
        crc_data_upper = '{:04X}'.format(my_crc)

        final_string = data_for_crc + crc_data_upper

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=5,
            border=2,
        )
        qr.add_data(final_string)
        qr.make(fit=True)

        # Determine color based on used field
        if self.use_uen_number:
            qr_color = "#57004700"
        elif self.use_mobile_number:
            qr_color = "#0071CE"
        elif self.use_alt_uen_number:
            qr_color = "#006400"
        else:
            qr_color = "#57004700"

        img = qr.make_image(fill_color=qr_color, back_color="white")

        # Add PayNow logo
        paynow_logo_path = get_module_resource('ks_custom_report_layouts', 'static/img', 'paynow.png')
        paynow_image = Image.open(paynow_logo_path)

        max_size = 100
        scale = max_size / max(paynow_image.size)
        resized_img = paynow_image.resize(
            (int(paynow_image.width * scale), int(paynow_image.height * scale)),
            Image.ANTIALIAS
        )

        qr_width, qr_height = img.size
        x_position = int((qr_width - resized_img.width) / 2)
        y_position = int((qr_height - resized_img.height) / 2)
        img.paste(resized_img, (x_position, y_position))

        temp = BytesIO()
        img.save(temp, format="PNG")
        img_str = base64.b64encode(temp.getvalue())

        return img_str

        
     # Method overridden
    def _get_name_invoice_report(self):
        """ This method need to be inherit by the localizations if they want to print a custom invoice report instead of
        the default one. For example please review the l10n_ar module """
        self.ensure_one()
        return 'ks_custom_report_layouts.report_invoice_inherit_document_dynamic'
    

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.browse(docids)

        # Fetch the sale_report_style_id from ks.report.configuration
        report_config = self.env['ks.report.configuration'].sudo().search([], limit=1)

        # Validate conditions
        if docs and (docs.move_type != 'out_invoice' or (report_config and report_config.sale_report_style_id != 'Minimalist')):
            raise UserError(_("""Only the Invoice Minimalist report could be printed."""))

        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
        }
    

    def get_aging_bucket_data(self):
        self.ensure_one()
        company_id = self.company_id.id
        partner_id = self.partner_id.id
        partner_ids = [partner_id]
        date_end = self.invoice_date_due or self.invoice_date or fields.Date.today()
        account_type = 'receivable' if self.move_type in ['out_invoice', 'out_refund'] else 'payable'

        # Call for day-wise buckets
        aging_data_days = self.env['statement.common']._get_account_show_buckets(
            company_id, partner_ids, date_end, account_type, 'days'
        )

        # Call for month-wise buckets
        aging_data_months = self.env['statement.common']._get_account_show_buckets(
            company_id, partner_ids, date_end, account_type, 'months'
        )

        return {
            'days': aging_data_days.get(partner_id, []),
            'months': aging_data_months.get(partner_id, []),
            'date_end': date_end,
            'currency': self.currency_id.name,
        }
    
    



   

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    lot_serial_numbers = fields.Char(
        string='Lot/Serial Numbers',
        compute='_compute_lot_serial_numbers',
        store=False
    )
    
    @api.depends('sale_line_ids')
    def _compute_lot_serial_numbers(self):
        for line in self:
            lots = line.sale_line_ids.mapped('move_ids.move_line_ids.lot_id.name')
            print("LOTS >>>>>>>>>>>>>>>>>>>>>>>>>>", lots)
            line.lot_serial_numbers = ', '.join(lots) if lots else ''
