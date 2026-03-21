import json
import requests
from odoo import fields, http 
from datetime import date, datetime
from odoo.http import request,Response
from ..handler import payroll_api,access_token_detail
import logging

logger = logging.getLogger(__name__)


class PayrollAPI(http.Controller):

    @http.route('/AddPayrollEntries', type="json", auth="public", methods=['POST'], csrf=False)
    def add_payroll_entries(self, **post):
        logger.info(">>>>>>>>>>>>>>>>>>>>>>  add_payroll_entries() >>>>>>>>>>>>>>>>>>>>> ")
        #TODO: how to find incoming request request IP Adddress. Handle it in future
        bearer = request.httprequest.headers.get("Authorization")
        data = json.loads(request.httprequest.data)
        print('\n\n\n\n\n\ndataaa', data)
        temp = access_token_detail.AccessTokenDetails.token_access(bearer)        
        print("temp ===",temp)
        
        if not temp:
            res = {
                "status": 0,
                "message": "fail"
            }
            return http.Response(
                json.dumps(res),
                status=401,
                mimetype='application/json')

        if not data:
            res = {
                "status": 0,
                "message": "fail",
            }
            return http.Response(
                json.dumps(res),
                status=401,
                mimetype='application/json')
        else:
            result = payroll_api.PayrollHandlers.create_payroll_account_entries(data)
            print('\n\n\n\n\n\n\n\nFinal resultresult', result)
            logger.info("controllers >>>>>> result ==")
            logger.info(result)
            if result.get('success') == '1':
                res = {
                    "status_code": 200,
                    "success": 1,
                    "message": "success",
                }
                return res
                return http.Response(
                    status=200,
                    content_type='application/json',
                    response=json.dumps(res))
            elif result.get('success') == '2':
                res = {
                    "status_code": 401,
                    "success": 0,
                    "message": "fail",
                }
                return res
                res = {
                    "status": 0,
                    "message": "fail",
                }
                return http.Response(
                    status=401,
                    content_type='application/json',
                    response=json.dumps(res))
            elif result.get('success') == '3':
                res = {
                    "status_code": 401,
                    "success": 0,
                    "message": result.get('msg'),
                }
                return res
                res = {
                    "status": 0,
                    "message": result.get('msg')
                }
                return http.Response(
                    status=401,
                    content_type='application/json',
                    response=json.dumps(res))
            else :
                res = {
                    "status_code": 401,
                    "success": 0,
                    "message": "fail",
                }
                return res
                res = {
                    "status": 0,
                    "message": "fail",
                }
                return http.Response(
                    status=401,
                    content_type='application/json',
                    response=json.dumps(res))
        
           
        

