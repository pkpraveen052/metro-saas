# -*- coding: utf-8 -*-

import io
import base64
import qrcode

from odoo import http, _, fields


import os
from io import BytesIO
from PIL import Image
from odoo import http, api, fields, models, _

import pycrc.algorithms
from odoo.modules.module import get_module_resource
from odoo.http import request

class PosPayNowController(http.Controller):

    # @http.route('/pos/payment/paynow_test', methods=['GET', 'POST'], type='json', auth='public', website=True, csrf=False)
    # def paynow_details(self, **post):
    #     print('\n/pos/payment/paynow >>>>> paynow_details() === post',post)
    #     data = {'img_str': False}
    #     if post.get('string'):
    #         qr = qrcode.QRCode(
    #             version = 1,
    #             error_correction = qrcode.constants.ERROR_CORRECT_H,
    #             box_size = 5,
    #             border = 2,
    #         )
    #         # Add data
    #         qr.add_data(post.get('string'))
    #         qr.make(fit=True)

    #         img = qr.make_image()
    #         buffered = io.BytesIO()
    #         img.save(buffered, format="PNG")
    #         img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    #         data['img_str'] = img_str
    #     return data

    @http.route('/pos/payment/paynow', methods=['GET', 'POST'], type='json', auth='public', website=True, csrf=False)
    def paynow_details(self, **post):
        print('\n/pos/payment/paynow >>>>> paynow_details() === post',post)
        data = {'img_str': False}
        # if post.get('string'):
            # qr = qrcode.QRCode(
            #     version = 1,
            #     error_correction = qrcode.constants.ERROR_CORRECT_H,
            #     box_size = 5,
            #     border = 2,
            # )
            # # Add data
            # qr.add_data(post.get('string'))
            # qr.make(fit=True)

            # img = qr.make_image()
            # buffered = io.BytesIO()
            # img.save(buffered, format="PNG")
            # img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            # data['img_str'] = img_str



        # Starts
        # post {'amount': 210, 
        # 'company': 
        # {'id': 108, 'currency_id': [37, 'SGD'], 'email': 'enquiry@erzatleemotor.com', 'website': False, 'company_registry': '201918537M', 'vat': '201918537M', 'name': 'ERZAT LEE MOTOR TRADING PTE LTD', 'phone': '+6588147031', 'partner_id': [7690, 'ERZAT LEE MOTOR TRADING PTE LTD'], 'country_id': [197, 'Singapore'], 'state_id': False, 'tax_calculation_rounding_method': 'round_per_line', 'country': {'id': 197, 'name': 'Singapore', 'vat_label': 'GST No.', 'code': 'SG'}},

        #  'refNumber': '00049-036-0001'}

        print("NEW    generate_qrcode () >>>>")
        company_obj = request.env['res.company'].browse(post.get('company')['id'])
        PayNow_ID = company_obj.l10n_sg_unique_entity_number
        Merchant_name = company_obj.name
        ref_number = post.get('refNumber')

        Transaction_amount = "{:.2f}".format(post.get('amount'))

        Can_edit_amount = "0"
        Merchant_category = "0000"
        Transaction_currency = "702"
        Country_code = "SG"
        Merchant_city = "Singapore"
        Globally_Unique_ID = "SG.PAYNOW"
        Proxy_type = "2"

        start_string = "010212"
        Dynamic_PayNow_QR = "000201"
        Globally_Unique_ID_field = "00"
        Globally_Unique_ID_length = str(len(Globally_Unique_ID)).zfill(2)
        Proxy_type_field = "01"
        Proxy_type_length = str(len(Proxy_type)).zfill(2)
        PayNow_ID_field = "02"
        PayNow_ID_Length = str(len(PayNow_ID)).zfill(2)
        Can_edit_amount_field = "03"
        Can_edit_amount_length = str(len(Can_edit_amount)).zfill(2)
        Merchant_category_field = "52"
        Merchant_category_length = str(len(Merchant_category)).zfill(2)
        Transaction_currency_field = "53"
        Transaction_currency_length = str(len(Transaction_currency)).zfill(2)
        Merchant_Account_Info_field = "26"
        Merchant_Account_Info_length = str(
            len(Globally_Unique_ID_field + Globally_Unique_ID_length + Globally_Unique_ID + \
                Proxy_type_field + Proxy_type_length + Proxy_type + \
                PayNow_ID_field + PayNow_ID_Length + PayNow_ID + \
                Can_edit_amount_field + Can_edit_amount_length + Can_edit_amount)).zfill(2)

        Transaction_amount_field = "54"
        Transaction_amount_length = str(len(Transaction_amount)).zfill(2)
        Country_code_field = "58"
        Country_code_length = str(len(Country_code)).zfill(2)
        Merchant_name_field = "59"
        Merchant_name_length = str(len(Merchant_name)).zfill(2)
        Merchant_city_field = "60"
        Merchant_city_length = str(len(Merchant_city)).zfill(2)
        Bill_number_field = "62"
        Bill_number_sub_length = str(len(ref_number)).zfill(2)
        Bill_number_length = str(len("01" + Bill_number_sub_length + ref_number)).zfill(2)

        data_for_crc = Dynamic_PayNow_QR + start_string + Merchant_Account_Info_field + Merchant_Account_Info_length + \
                       Globally_Unique_ID_field + Globally_Unique_ID_length + Globally_Unique_ID + \
                       Proxy_type_field + Proxy_type_length + Proxy_type + \
                       PayNow_ID_field + PayNow_ID_Length + PayNow_ID + \
                       Can_edit_amount_field + Can_edit_amount_length + Can_edit_amount + \
                       Merchant_category_field + Merchant_category_length + Merchant_category + \
                       Transaction_currency_field + Transaction_currency_length + Transaction_currency + \
                       Transaction_amount_field + Transaction_amount_length + Transaction_amount + \
                       Country_code_field + Country_code_length + Country_code + \
                       Merchant_name_field + Merchant_name_length + Merchant_name + \
                       Merchant_city_field + Merchant_city_length + Merchant_city + \
                       Bill_number_field + Bill_number_length + "01" + Bill_number_sub_length + ref_number + \
                       "6304"

        print("\ndata_for_crc ========", data_for_crc)

        crc = pycrc.algorithms.Crc(width=16, poly=0x1021,
                                   reflect_in=False, xor_in=0xffff,
                                   reflect_out=False, xor_out=0x0000)

        my_crc = crc.bit_by_bit_fast(data_for_crc)  # calculate the CRC, using the bit-by-bit-fast algorithm.
        crc_data_upper = ('{:04X}'.format(my_crc))

        final_string = data_for_crc + crc_data_upper

        print("\nfinal_string =======", final_string)

        # Create qr code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=5,
            border=2,
        )

        qr.add_data(final_string)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#57004700")  # fill_color="#993333", back_color="white"

        paynow_logo_path = get_module_resource('metro_pos_paynow', 'static/src/img', 'paynow.png')
        paynow_image = Image.open(paynow_logo_path)

        max_size = 100
        width, height = paynow_image.size
        print("width, height", width, height)

        # Calculate the scaling factor to fit the image into max_size
        scale = max_size / max(width, height)
        print("scale ==", scale)

        # Resize the image
        new_width = int(width * scale)
        new_height = int(height * scale)
        print("new_width ==", new_width)
        print("new_height ==", new_height)

        resized_img = paynow_image.resize((new_width, new_height), Image.ANTIALIAS)

        qr_width, qr_height = img.size
        paynow_width, paynow_height = resized_img.size
        x_position = int((qr_width - paynow_width) / 2)
        y_position = int((qr_height - paynow_height) / 2)

        img.paste(resized_img, (x_position, y_position))

        temp = BytesIO()
        img.save(temp, format="PNG")
        img_str = base64.b64encode(temp.getvalue())
        # qr_code = img_str
        # return qr_code
        data['img_str'] = img_str
        print("FINALLLLLLLLLLLLLL",data)
        return data