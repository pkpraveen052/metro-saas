
import re, os, mimetypes, requests, random, io
import base64, json
from odoo import models, fields
from PIL import Image
import fitz
import tempfile

from odoo.exceptions import UserError


class InvoiceUploadWizard(models.TransientModel):
    _name = 'invoice.upload.wizard'
    _description = 'Upload Invoice'

    invoice_file = fields.Binary('Vendor Bill File', required=True)
    filename = fields.Char('Filename')

    def _extract_invoice_data_with_gemini(self, file_path, gemini_api_key, mime_type):
        model = "models/gemini-2.5-flash-preview-04-17"
        url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={gemini_api_key}"

        # genai.configure(api_key=gemini_api_key)
        # model = genai.GenerativeModel("gemini-2.0-flash")

        dict_prompt = """
            You are an intelligent bill data extraction assistant.
            Please analyze the attached vendor invoice (PDF or image) and extract the following fields in clean JSON format:
            Identify the vendor and customer as follows:
            - The vendor is the company that issued the invoice. This usually appears at the top of the invoice and is associated with fields like: "Vendor", "From", "Issued By", or is near the invoice number and tax ID.
            - The customer is the company that is being billed. This usually appears below the vendor section and is labeled as: "To", "Bill To", "Ship To", or "Customer".
            For the date type field can you provide data this kind of data 
            - '%Y-%m-%d'
            - If there are two mobile numbers, assign one to "mobile" and the other to "phone".
            For the "taxes" field:
            - Look for any percentage number (e.g., 7%, 9%) that appears near "GST" or tax-related labels.
            - If found, extract that number and include it as the "taxes" value (e.g., "9% GST").
            - If no tax is mentioned, return `null`.
            Please identify and extract discount and discount type:
            - In the `line_items`, the discount can either be:
            - A percentage (e.g., "10%")
            - A fixed amount (e.g., "S$100", "$50")
            - `"discount"`: the discount value as a string
            - `"discount_type"`: either `"percentage"` or `"fixed"`.
            Only invoice/bill payments terms should be considered as notes.
            For Line Items:
            - In `line_items`, return each item as one of:
            - `"line_type": "product"` — for standard items with quantity and price.
            - `"line_type": "note"` — for lines that contain only a description.
            - `"line_type": "section"` — for section headers or grouping titles (e.g., "Sections", "Labor", etc.).
            - Section lines will only have a `"description"` and `"line_type": "section"`; all other fields can be empty or null.
            Extract only valid JSON from this invoice. 
            Do not add any explanation, comment, or text outside the JSON structure. 
            Output must be a single JSON object, nothing else.
            Respond only with valid JSON. Do not include explanations, code blocks, or extra text.
            {
              "vendor_name": "",
              "vendor_registration_number": "",
              "street": "",
              "street2":"",
              "city":"",
              "zip_code":"",
              "country":"",
              "mobile":"",
              "phone":"",
              "vendor_email":"",
              "invoice_number": "",
              "invoice_date": "",
              "due_date": "",
              "currency": "",
              "payment_terms": "",
              "customer_reference": "",
              "vendor_reference": "",
              "subtotal": 0.0,
              "tax_total": 0.0,
              "discount_total": 0.0,
              "rounding": 0.0,
              "total": 0.0,
              
              "customer_name": "",
              "customer_street": "",
              "customer_street2": "",
              "customer_city": "",
              "customer_zip": "",
              "customer_country": "",
              "customer_mobile":"",
              "customer_phone":"",
              "customer_email":"",
              "customer_tax_id": "",
              
              "tax_summary": [
                {
                  "tax_type": "",
                  "tax_rate": "",
                  "tax_amount": 0.0
                }
              ],
              "line_items": [
                {
                  "product":"",
                  "description": "",
                  "sku": "",
                  "quantity": 0.0,
                  "uom": "",
                  "unit_price": 0.0,
                  "discount": 0.0,
                  "discount_type": ""
                  "tax_type": "",
                  "tax_rate": "",
                  "tax_amount": 0.0,
                  "line_total": 0.0,
                  "line_type":""
                }
              ],
              "attachments": [
                {
                  "filename": "",
                  "file_type": "",
                  "file_url": ""
                }
              ],
              "notes": "",
              "comments": "",
              "status": "",
              "journal": "",
              "tax_included": "",
              "bill_level_tax": ""
            }
            Return only valid JSON and no other text. No explanation."""

        # add_prompt = """ If this company name appears in the header then also treat the following company as the customer
        # in case it appears anywhere on the bill: "%s" """ % (self.env.company.name)
        prompt =  dict_prompt
        # with open(file_path, "rb") as f:
        #     response = model.generate_content(
        #         contents=[
        #             prompt,
        #             {"mime_type": mime_type, "data": f.read()}
        #         ]
        #     )
        with open(file_path, "rb") as f:
            file_data = base64.b64encode(f.read()).decode("utf-8")
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": file_data
                            }
                        }
                    ]
                }
            ]
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            try:
                self.env['invoice.ocr.logs'].create({'token_id':gemini_api_key, 'message':response.status_code,
                                                     'company_id': self.env.company.id})
                return response.json()["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                raise UserError("There was some error while fetching the data, Please try again later.")
        else:
            raise UserError("There was some error while fetching the data, Please try again later.")

    def extract_json_block(self, text):
        # Remove code block wrappers if present
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return match.group(0)
        return text  # Fallback

    def _get_partner(self, name):
        company_id = self.env.company.id
        partner = self.env['res.partner'].search([('name', '=', name), ('company_id', '=', company_id)], limit=1)
        return partner

    def _get_currency(self, code):
        return self.env['res.currency'].search([('name', '=', code)], limit=1)

    def extract_tax_percent(self, text):
        match = re.search(r'(\d+(\.\d+)?)\s*%?', text)
        return float(match.group(1)) if match else 0.0

    def _get_product(self, name):
        product = self.env['product.product'].search([('name', 'ilike', name)], limit=1)
        return product

    def _get_taxes(self, name=False,summary_tax_text=False, sub_total=False):
        # Try line-level tax
        tax = False
        if name:
            split_words = name.split()
            domain = [('name', 'ilike', word) for word in split_words] + [('type_tax_use', '=', 'purchase')]
            tax = self.env['account.tax'].search(domain, limit=1)
            tax_return  = [tax, False] if tax else  [False, split_words[0]]
            return tax_return

        # Try summary-level fallback
        if summary_tax_text:
            percent = float(summary_tax_text) if isinstance(summary_tax_text,(float, int)) else self.extract_tax_percent(
                summary_tax_text)

            if percent:
                tax_ratio = percent / sub_total
                estimated_tax_percent = round(tax_ratio * 100)
                tax = self.env['account.tax'].search([
                    ('type_tax_use', '=', 'purchase'),
                    ('name', 'ilike', estimated_tax_percent)
                ], limit=1)
                to_return = [tax, False] if tax else [False, estimated_tax_percent]
                return to_return
        return False

    def validate_invoice_data(self, data):
        required_fields = ['invoice_number', 'invoice_date', 'total']

        missing = [field for field in required_fields if not data.get(field)]
        if len(missing) >= 2:
            raise UserError(
                "Uploaded image does not appear to be a valid bill. Please upload a valid bill.")

    def send_values_to_ocr(self):
        params = self.env['ir.config_parameter'].sudo()
        api_keys_raw = params.get_param('gemini_api_key',
                                                 default=False)
        if ',' in api_keys_raw:
            api_keys = [key.strip() for key in api_keys_raw.split(',') if key.strip()]
        else:
            api_keys = [api_keys_raw.strip()] if api_keys_raw.strip() else []

        gemini_key = random.choice(api_keys) if api_keys else False

        # gemini_key = "AIzaSyDCxndzcGeoWtCGhIYAeoTSTB2qXOB2l78"

        # Determine extension from filename or default to .pdf
        extension = '.pdf'
        if self.filename:
            extension = os.path.splitext(self.filename)[1].lower() or '.pdf'

        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
            tmp.write(base64.b64decode(self.invoice_file))
            tmp_path = tmp.name
        # Guess MIME type (e.g., image/jpeg, application/pdf)
        mime_type, _ = mimetypes.guess_type(tmp_path)

        # Validate supported MIME types
        allowed_mime_types = ['application/pdf', 'image/jpeg', 'image/png']
        if mime_type not in allowed_mime_types:
            raise UserError("The uploaded file format is not supported. Only PDF and image files (JPG, PNG) are supported.")

        try:
            result_text = self._extract_invoice_data_with_gemini(tmp_path, gemini_key, mime_type)
        except:
            raise UserError("There was some error while fetching the data, Please try again later.")
        clean_text = self.extract_json_block(result_text)
        print(clean_text)
        data = json.loads(clean_text)

        self.validate_invoice_data(data)

        company_name = self.env.company.name.strip().lower()
        vendor_name = data.get('vendor_name', '').strip().lower()
        # If vendor_name matches current company name, use customer_* fields instead
        if company_name in vendor_name or vendor_name in company_name:
            data['vendor_name'] = data.get('customer_name', '')
            data['street'] = data.get('customer_street', '')
            data['street2'] = data.get('customer_street2', '')
            data['city'] = data.get('customer_city', '')
            data['zip_code'] = data.get('customer_zip', '')
            data['country'] = data.get('customer_country', '')
            data['vendor_registration_number'] = data.get('customer_tax_id', '')
            data['mobile'] = data.get('customer_mobile', '')
            data['phone'] = data.get('customer_phone', '')
            data['vendor_email'] = data.get('customer_email', '')

            # Optional: Clear the customer fields to avoid confusion
            data['customer_name'] = ''
            data['customer_street'] = ''
            data['customer_street2'] = ''
            data['customer_city'] = ''
            data['customer_zip'] = ''
            data['customer_country'] = ''
            data['customer_tax_id'] = ''
            data['customer_mobile'] = ''
            data['customer_phone'] = ''
            data['customer_email'] = ''
        return data

    def action_create_vendor_bill(self):
        context = dict(self._context or {})
        selected_vendor_id = context.get('selected_vendor_id')
        ocr_data = context.get('ocr_data')

        # Get OCR data from context or fetch it
        data = ocr_data if selected_vendor_id and ocr_data else self.send_values_to_ocr()
        if not data:
            return

        # Get or search partner
        partner = self._get_partner(selected_vendor_id) if selected_vendor_id and ocr_data else self._get_partner(data['vendor_name'])
        if not partner:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Vendor Not Found',
                'res_model': 'vendor.not.found.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_ocr_vendor_name': data['vendor_name'],
                    'vendor_registration_number': data['vendor_registration_number'],
                    'street': data['street'],
                    'street2': data['street2'],
                    'city': data['city'],
                    'zip_code': data['zip_code'],
                    'country': data['country'],
                    'mobile': data['mobile'],
                    'phone': data['phone'],
                    'vendor_email': data['vendor_email'],
                    'invoice_file': self.invoice_file,
                    'filename': self.filename,
                    'data': data,
                },
        }

        # Get currency or default to company currency
        currency = self._get_currency(data['currency']) or self.env.company.currency_id

        # Prepare invoice values
        move_vals = {
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_origin': data['invoice_number'],
            'invoice_date': data['invoice_date'],
            'invoice_date_due': data['due_date'],
            'ref': data['customer_reference'] or False,
            'currency_id': currency.id,
            'narration': data['notes'],
            'invoice_line_ids': [],
        }

        # Build invoice lines
        for item in data['line_items']:
            line_type = item.get('line_type', 'product')

            values_dict = {
                'name': item.get('description', '')
            }

            # Handle section or note lines
            if line_type == 'section':
                values_dict['display_type'] = 'line_section'
            elif line_type == 'note':
                values_dict['display_type'] = 'line_note'
            else:
                # Normal product line
                quantity = float(item['quantity']) if item.get('quantity') else 0.0
                unit_price = float(item['unit_price']) if item.get('unit_price') else 0.0

                values_dict.update({
                    'quantity': quantity,
                    'price_unit': unit_price
                })

                # Try to find and assign product
                if item.get('product'):
                    product = self._get_product(item['product'])
                    if product:
                        values_dict['product_id'] = product.id
                        values_dict['product_uom_id'] = product.uom_id.id

                discount_value = item.get('discount')
                discount_type = item.get('discount_type')

                if discount_value and discount_type:
                    try:
                        if discount_type == "percentage":
                            # Clean "%" if included
                            discount_value = str(discount_value).replace("%", "")
                            values_dict['discount'] = float(discount_value)
                            values_dict['discount_type'] = 'percent'
                        elif discount_type == "fixed":
                            # Convert fixed discount to percentage relative to line total
                            fixed_discount = float(discount_value)
                            if item['unit_price'] * item['quantity'] > 0:
                                values_dict['discount'] = round((fixed_discount / (float(item['unit_price']) * float(item['quantity']))) * 100, 2)
                                values_dict['discount_type'] = 'fixed'
                            else:
                                values_dict['discount'] = 0.0
                                values_dict['discount_type'] = 'fixed'
                    except Exception:
                        values_dict['discount'] = 0.0
                tax = []
                if item.get('tax_rate'):
                    tax = self._get_taxes(item['tax_rate'], summary_tax_text=False)
                elif data.get('tax_total'):
                    tax = self._get_taxes(name=False, summary_tax_text=data['tax_total'], sub_total=data.get('subtotal'))

                if tax and tax[0]:
                    values_dict['tax_ids'] = [(6, 0, [tax[0].id])]
                elif tax and tax[1] and not (selected_vendor_id and ocr_data):
                    percent_msg = "The %s" % (tax[1]) if '%' in tax[1] else "The %s" % (tax[1]) + "%"
                    msg =  percent_msg + " purchase tax does not exist in the system. Please create a new tax record."
                    raise UserError(msg)
                elif tax and tax[1] and selected_vendor_id and ocr_data:
                    percent_msg = "The %s" % (tax[1]) if '%' in tax[1] else "The %s" % (tax[1]) + "%"
                    msg = percent_msg + " purchase tax does not exist in the system. Please create a new tax record."
                    return msg

            move_vals['invoice_line_ids'].append((0, 0, values_dict))
            move_vals['is_ocr_created'] = True
        invoice = self.env['account.move'].create(move_vals)

        if self.invoice_file and self.filename:
            self._attach_compressed_bill(invoice.id, 'account.move', self.invoice_file, self.filename)
        elif context.get('filename', False) and context.get('invoice_file', False):
            self._attach_compressed_bill(invoice.id, 'account.move', context.get('invoice_file'), context.get('filename'))

        if data.get('total', False) and data.get('total', False) != invoice.amount_total:
            invoice.message_post(body=(f"Extracted bill total ({data['total']}) does not match created bill total ({round(invoice.amount_total,2)})."))
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': invoice.id,
                'view_mode': 'form',
                'target': 'current',
                'context': {'show_ocr_warning': True}
            }
            # return {
            #     'type': 'ir.actions.act_window',
            #     'res_model': 'mismatch.warning.wizard',
            #     'view_mode': 'form',
            #     'target': 'new',
            #     'context': {
            #         'default_message': f"Extracted bill total ({data['total']}) does not match created bill total ({round(invoice.amount_total,2)}).",
            #         'default_invoice_id': invoice.id
            #     }
            # }

        if selected_vendor_id and ocr_data:
            return invoice.id
        else:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': invoice.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def compress_image(self, base64_data):
        image_data = base64.b64decode(base64_data)
        image = Image.open(io.BytesIO(image_data))
        if image.mode == 'RGBA':
            image = image.convert('RGB')

        output = io.BytesIO()

        image.save(output, format='JPEG', optimize=True, quality=60)  # Adjust quality as needed
        return base64.b64encode(output.getvalue())

    def convert_pdf_to_image(self, base64_pdf):
        pdf_bytes = base64.b64decode(base64_pdf)
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        if not pdf_doc.page_count:
            raise ValueError("Empty PDF")

        page = pdf_doc.load_page(0)
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("jpeg")

        compressed_io = io.BytesIO()
        image = Image.open(io.BytesIO(img_bytes))
        image.save(compressed_io, format="JPEG", optimize=True, quality=60)

        return base64.b64encode(compressed_io.getvalue())

    def _attach_compressed_bill(self, res_id,res_model, base64_file, filename):
        if not base64_file or not filename:
            return

        # base64_file_encoded = base64.b64encode(base64_file)
        if filename.lower().endswith('.pdf'):
            image_base64 = self.convert_pdf_to_image(base64_file)
        else:
            image_base64 = self.compress_image(base64_file)

        self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': image_base64,
            'res_model': res_model,
            'res_id': res_id,
            'mimetype': 'image/jpeg',
        })
