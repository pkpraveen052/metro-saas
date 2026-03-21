# -*- coding: utf-8 -*-

import json
import requests

from odoo import http
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)



class IRAS(http.Controller):

    @http.route('/client/iras/update_config', type='http', methods=['GET'], auth='public', website=True)
    def client_iras_update_config(self, **kw):
        print("\nCLIENT ........ client_iras_update_config() ... kw ===",kw)
        if kw.get('iras_apikey') and kw.get('iras_apisecret'):
            for k, val in kw.items():
                request.env['ir.config_parameter'].sudo().set_param(k, val)
            print("DONEEEE")
            return 'success'
        else:
            return 'failure'
            

    @http.route('/client/iras/corppass', type='http', methods=['GET'], auth='public', website=True)
    def client_iras_callback(self, **kw):
        print("\nCLIENT ........ iras_callback() ... kw ===",kw)
        _logger.info('CLIENT ........ iras_callback() ... kw === %s ' % (json.dumps(kw)))
        request.env['corppass.logs'].sudo().create({'content': json.dumps(kw)})
        if kw.get('code') and kw.get('state'):
            obj = request.env['gst.returns.f5f8'].sudo().search([('state_identifier','=', kw['state'])], limit=1)
            obj2 = request.env['gst.returns.f7'].sudo().search([('state_identifier','=', kw['state'])], limit=1)
            obj3 = request.env['form.cs'].sudo().search([('state_identifier','=', kw['state'])], limit=1)
            if obj:
                print("gst.returns.f5f8 >>>>")
                obj.write({'auth_code': kw.get('code')})

                config_params = request.env['ir.config_parameter'].sudo()
                headers = {
                    'accept': 'application/json',
                    'content-type': 'application/json',
                    'X-IBM-Client-Id': config_params.get_param('iras_apikey'),
                    'X-IBM-Client-Secret': config_params.get_param('iras_apisecret')
                }  

                payload = {
                    "scope": 'GSTF5F8SubCP',
                    "callback_url": config_params.get_param('corppass_callback_url'),
                    "code": kw.get('code'),
                    "state": kw['state']
                }
                print("payload ==",payload)

                url = config_params.get_param('corppass_token_endpoint')
                print("url ==",url)
                response = requests.request("POST", url, data=json.dumps(payload), headers=headers, allow_redirects=False)

                res_data = json.loads(response.text)
                print('======res_data', res_data)

                if res_data.get('returnCode'):
                    form_url = "%s/web#id=%s&action=%s&model=gst.returns.f5f8&view_type=form" % (request.env['ir.config_parameter'].sudo().get_param('web.base.url'), obj.id, request.env.ref('metroerp_iras.gst_returns_f5f8_action').id)
                    print("form_url ===",form_url)
                    message = 'Unknown Error'
                    if res_data['returnCode'] in ["10","20"]:
                        obj.access_token = res_data['data']['token']
                        obj.message_post(body="Corppass Token Received: " + res_data['data']['token'])                        
                        res = obj.autosubmit_gst_data()
                        if isinstance(res, dict):
                            message = res['message']                            
                    elif res_data['returnCode'] == "30":
                        obj.message_post(body="Corppass Token API Failure – The request was not processed. Refer to “info” object for error information.\n" + json.dumps(res_data))
                        message = "Corppass Token API Failure – The request was not processed. Refer to “info” object for error information."
                    return """
                            <html>
                                <body>
                                    <h1>%s.</h1><br/>
                                    <h2><a href="%s">Click Here</a> to go back to the form.</h2>
                                </body>
                            </html>
                        """ % (message, form_url)
                else:
                    obj.message_post(body="Corppass Token API Error.\n" + json.dumps(res_data))
            elif obj2:
                print("gst.returns.f7 >>>>>")
                obj2.write({'auth_code': kw.get('code')})

                config_params = request.env['ir.config_parameter'].sudo()
                headers = {
                    'accept': 'application/json',
                    'content-type': 'application/json',
                    'X-IBM-Client-Id': config_params.get_param('iras_apikey'),
                    'X-IBM-Client-Secret': config_params.get_param('iras_apisecret')
                }  

                payload = {
                    "scope": 'GSTF7SubCP',
                    "callback_url": config_params.get_param('corppass_callback_url'),
                    "code": kw.get('code'),
                    "state": kw['state']
                }

                url = config_params.get_param('corppass_token_endpoint')
                response = requests.request("POST", url, data=json.dumps(payload), headers=headers, allow_redirects=False)

                res_data = json.loads(response.text)
                print('======res_data', res_data)

                if res_data.get('returnCode'):
                    form_url = "%s/web#id=%s&action=%s&model=gst.returns.f7&view_type=form" % (request.env['ir.config_parameter'].sudo().get_param('web.base.url'), obj2.id, request.env.ref('metroerp_iras.gst_returns_f7_action').id)
                    print("form_url ===",form_url)
                    message = 'Unknown Error'
                    if res_data['returnCode'] in ["10","20"]:
                        obj2.access_token = res_data['data']['token']
                        obj2.message_post(body="Corppass Token Received: " + res_data['data']['token'])                        
                        res = obj2.autosubmit_gst_data()
                        if isinstance(res, dict):
                            message = res['message']                            
                    elif res_data['returnCode'] == "30":
                        obj2.message_post(body="Corppass Token API Failure – The request was not processed. Refer to “info” object for error information.\n" + json.dumps(res_data))
                        message = "Corppass Token API Failure – The request was not processed. Refer to “info” object for error information."
                    return """
                            <html>
                                <body>
                                    <h1>%s.</h1><br/>
                                    <h2><a href="%s">Click Here</a> to go back to the form.</h2>
                                </body>
                            </html>
                        """ % (message, form_url)
                else:
                    obj2.message_post(body="Corppass Token API Error.\n" + json.dumps(res_data))
            elif obj3:
                obj3.write({'auth_code': kw.get('code')})

                config_params = request.env['ir.config_parameter'].sudo()
                headers = {
                    'accept': 'application/json',
                    'content-type': 'application/json',
                    'X-IBM-Client-Id': config_params.get_param('iras_apikey'),
                    'X-IBM-Client-Secret': config_params.get_param('iras_apisecret')
                }
                print("headers ===",headers)

                if obj3.state == 'pre_fill':
                    scope = 'CITPrefillCS'
                else:
                    scope = 'CITFormCSSub'
                payload = {
                    "scope": scope,
                    "callback_url": config_params.get_param('corppass_callback_url'),
                    "code": kw.get('code'),
                    "state": kw['state']
                }
                print("payload ===",payload)

                url = config_params.get_param('corppass_token_endpoint')
                print("url ===",url)
                response = requests.request("POST", url, data=json.dumps(payload), headers=headers, allow_redirects=False)

                res_data = json.loads(response.text)
                print('response .... res_data ===', res_data)

                if res_data.get('returnCode'):
                    form_url = "%s/web#id=%s&action=%s&model=form.cs&view_type=form" % (request.env['ir.config_parameter'].sudo().get_param('web.base.url'), obj3.id, request.env.ref('metroerp_iras.form_cs_action').id)
                    message = 'Unknown Error'
                    if res_data['returnCode'] in ["10","20"]:
                        obj3.access_token = res_data['data']['token']
                        obj3.message_post(body="Corppass Token Received: " + res_data['data']['token'])
                        if obj3.state == 'pre_fill':                       
                            res = obj3.autosubmit_pre_fill()
                        else:
                            res = obj3.action_submit_cs()
                        if isinstance(res, dict):
                            message = res['message']                            
                    elif res_data['returnCode'] == "30":
                        obj3.message_post(body="Corppass Token API Failure – The request was not processed. Refer to “info” object for error information.\n" + json.dumps(res_data))
                        message = "Corppass Token API Failure – The request was not processed. Refer to “info” object for error information."
                    return """
                            <html>
                                <body>
                                    <h1>%s</h1><br/>
                                    <h2><a href="%s">Click Here</a> to go back to the form.</h2>
                                </body>
                            </html>
                        """ % (message, form_url)
                else:
                    obj3.message_post(body="Corppass Token API Error.\n" + json.dumps(res_data))

        return """
            <html>
                <body>
                    <h1> Internal Error arised which processing the controller. <br/>Reason: No code and state received.</h1><br/>
                    <h2><a href="%s">Click Here</a> to go back to the application.</h2>
                </body>
            </html>
        """ % (request.env['ir.config_parameter'].sudo().get_param('web.base.url'))
