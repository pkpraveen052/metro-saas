from odoo.http import request
import re
import base64
import json
from datetime import datetime
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class PayrollHandlers():
    def create_payroll_account_entries(data):
        responce = data
        result_dict = {}
        payslips = responce.get('payslip',False)
        company = request.env['res.company'].sudo().search([('carbonate_token', '=', responce.get('target_token'))])
        if not company:
            result_dict['status'] = '401'
            result_dict['success'] = '3'
            result_dict['msg'] = 'fail'
            #Carbonate Logs
            request.env['carbonate.log'].sudo().create({
                'name': 'Company Not Found',
                'status': 'fail',
                'status_code': 401,
                'company_id': company.id if company else False,
                'json_data': str(data),
                'message': 'No company found with the provided token.'
            })
            return result_dict
        try:   
            journal = request.env['account.journal'].sudo().search([
                ('name', 'ilike','Payroll'),
                ('type', '=', 'general'),
                ('company_id', '=', company.id)], limit=1)
            if not journal:
                journal_id = request.env['account.journal'].sudo().create({
                                        'name': 'Payroll',
                                        'type': 'general',
                                        'code': 'PAY',
                                        'sequence': 13,
                                        'company_id': company.id}).id
            else:
                journal_id = journal.id
            synced = False
            for payslip_dic in payslips:
                if not payslip_dic["id"]:
                    continue
                reference = payslip_dic.get('user_name','')
                if payslip_dic.get('TxnDate'):
                    reference += ' / ' + 'TxnDate: ' + payslip_dic.get('TxnDate')
                rec = request.env['account.mapping'].sudo().search([('active','=',True), ('company_id', '=', company.id)], limit=1)
                if not rec:
                    logger.info("401 >>>>>>>. failed")
                    result_dict['status'] = '401'
                    result_dict['success'] = '3'
                    result_dict['msg'] = 'fail'
                    #Carbonate Logs
                    request.env['carbonate.log'].sudo().create({
                        'name': 'Account Mapping Not Found',
                        'status': 'fail',
                        'status_code': 401,
                        'company_id': company.id,
                        'json_data': str(payslip_dic),
                        'message': 'No active account mapping found for the company.'
                    })
                    return result_dict

                line_items = []
                if not rec.need_separate_cpf:
                    logger.info("NO NEED CPF LINES")
                    amount = 0.0
                    label = "Sum of "
                    for itemcode_dic in payslip_dic['payslipItemsAndCodes']:
                        if itemcode_dic['amount']:
                            amount += float(itemcode_dic['amount'])
                            label += itemcode_dic['name'] + ", "
                    label = label[:-2]
                    line_items.append((0,0,{
                                        'account_id': rec.credit_account.id,
                                        'name': label,
                                        'credit': amount,
                                        'debit': 0.0}))
                    line_items.append((0,0,{
                                        'account_id': rec.debit_account.id,
                                        'name': label,
                                        'credit': 0.0,
                                        'debit': amount}))
                else:
                    # Exlcude CPF
                    logger.info("CPF>>>>>>>>>>>>>>>>>>>>>>")
                    amount = 0.0
                    label = "Sum of "
                    cpf_line_codes = rec.cpf_lines.mapped('code')
                    logger.info(cpf_line_codes)
                    amount_found = False
                    for itemcode_dic in payslip_dic['payslipItemsAndCodes']:
                        if itemcode_dic['amount'] and str(itemcode_dic['id']) not in cpf_line_codes:
                            amount += float(itemcode_dic['amount'])
                            label += itemcode_dic['name'] + ", "
                            amount_found = True
                    if amount_found:
                        label = label[:-2]
                    logger.info(amount)
                    logger.info(label)
                    line_items.append((0,0,{
                                        'account_id': rec.credit_account.id,
                                        'name': label,
                                        'credit': amount,
                                        'debit': 0.0}))
                    line_items.append((0,0,{
                                        'account_id': rec.debit_account.id,
                                        'name': label,
                                        'credit': 0.0,
                                        'debit': amount}))
                    for cpf_line in rec.cpf_lines: # Include CPF
                        amount = 0.0
                        label = "Sum of "
                        amount_found = False
                        for itemcode_dic in payslip_dic['payslipItemsAndCodes']:
                            if str(itemcode_dic['id']) == cpf_line.code and itemcode_dic.get('amount'):
                                logger.info(itemcode_dic.get('amount'))
                                amount += abs(float(itemcode_dic.get('amount')))
                                label += itemcode_dic['name'] + ", "
                                amount_found = True
                        if amount_found:
                            label = label[:-2]

                            line_items.append((0,0,{
                                        'account_id': cpf_line.credit_account.id,
                                        'name': label,
                                        'credit': amount,
                                        'debit': 0.0}))
                            line_items.append((0,0,{
                                            'account_id': cpf_line.debit_account.id,
                                            'name': label,
                                            'credit': 0.0,
                                            'debit': amount}))
                logger.info("Creating >>>>>>>.")
                new_account_move = request.env['account.move'].sudo().create({
                    'date': datetime.now().date(),
                    'ref': reference,
                    'journal_id': journal_id,
                    'line_ids': line_items,
                    'company_id': company.id})
                json_data = json.dumps(payslip_dic, indent=4)
                new_account_move.message_post(body=f"Payroll Data: \n{json_data}")                
                new_account_move.action_post()

                synced = True

            if synced:
                logger.info("\n>>>>>>>>>>>>>>>>   synced ==")
                result_dict['status'] = '200'
                result_dict['success'] = '1'
                result_dict['msg'] = "success"
                #Carbonate Logs
                request.env['carbonate.log'].sudo().create({
                    'name': 'Sync Successful',
                    'status': 'success',
                    'status_code': 200,
                    'company_id': company.id,
                    'json_data': str(payslips),
                    'message': 'Successfully synced payslips.'
                })
                return result_dict

        except Exception as error:
            error_traceback = error.__traceback__
            logger.info(error_traceback)
            error_dict = {
                "errorType": type(error).__name__,
                "message": str(error),
                "fileName": error_traceback.tb_frame.f_code.co_filename,
                "handlerName": error_traceback.tb_frame.f_code.co_name,
                "lineNumber": error_traceback.tb_lineno,
            }
            logger.info(error_dict)
            logger.info("401 >>>>>>>>>>>  Exception failed")
            result_dict['status'] = '401'
            result_dict['success'] = '3'
            result_dict['msg'] = 'fail'
            #Carbonate Logs
            request.env['carbonate.log'].sudo().create({
                'name': 'Exception Occurred',
                'status': 'fail',
                'status_code': 401,
                'company_id': company.id,
                'json_data': str(data),
                'message': f"Error: {str(error_dict)}"
            })
            return result_dict
