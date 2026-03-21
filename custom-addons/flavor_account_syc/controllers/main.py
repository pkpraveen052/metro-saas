# -*- coding: utf-8 -*-

from odoo import api, models, tools, registry, exceptions, tools, http,_
import json
from odoo.http import request
import logging
from odoo.tests import Form
import random
from odoo.addons.web.controllers.main import Session

_logger = logging.getLogger(__name__)

class CustomSession(Session):

    @http.route('/web/session/write_flavor_grp', type='json', auth="none")
    def write_flavor_grp(self, company_id):
        print("\n NEW ite_flavor_grp() >>>>>",company_id, request.session.uid)
        company_obj = request.env['res.company'].browse(company_id)
        if company_obj.enable_flavor_sync:
            request.env['res.users'].browse(request.session.uid).sudo().write({'groups_id': [(4, request.env.ref('flavor_account_syc.group_flavor_sync').id)]})
        else:
            request.env['res.users'].browse(request.session.uid).sudo().write({'groups_id': [(3, request.env.ref('flavor_account_syc.group_flavor_sync').id)]})
        return True

def invalid_response(message=None):
    return http.Response(
        status=404,
        content_type="application/json",
        response=json.dumps({
            "status": False,
            "message": str(message),
        }),
    )

def valid_response(data, message=None):
    return http.Response(
        status=200,
        content_type="application/json",
        response=json.dumps({
            "status": True,
            "message": str(message),
            "data": data
        }),
    )

class FlavorAccountSync(http.Controller):

    def check_flavor_api(self, req_api_key, req_api_secret):
        print("check_flavor_api() >>>>>>")
        company_o = request.env['res.company'].sudo().search([('enable_flavor_sync','=',True),('flavor_apikey','=',req_api_key),
                                                            ('flavor_apisecret','=',req_api_secret)], limit=1)
        print("company_o ==",company_o)
        if not req_api_key or not req_api_secret:
            return invalid_response(message='API Key or Secret token is missing. Please check and try again.')
        if not company_o:
            return invalid_response(message='Either API Key & Secret are missing in Metro Or Flavor Sync is disabled in Metro.')
        elif req_api_key != company_o.flavor_apikey or req_api_secret != company_o.flavor_apisecret:
            return invalid_response(message="API Key or Secret token is not matching with Metro website's Data.")
        else:
            return valid_response(data={}, message='Successful')


    @http.route('/flavor/account/invoice_sync', auth="public", methods=['POST'], csrf=False)
    def flavor_account_invoice(self, **kw):
        print("\n/flavor/account/invoice_sync >>>>>>>>")
        print("request.httprequest.data ==",request.httprequest.data)
        _logger.info(request.httprequest.data)
        if not request.httprequest.data:
            return invalid_response(message='Data is missing. Please check and try again.')
        data = json.loads(request.httprequest.data)
        partner_o = request.env['res.partner']
        invoice_o = request.env['account.move']
        journal_o = request.env['account.journal']
        product_o = request.env['product.product']
        product_categ_o = request.env['product.category']
        acc_tax_o = request.env['account.tax']
        accounts_o = request.env['account.account']
        req_api_key = request.httprequest.headers.get("Metro-Client-Id")
        req_api_secret = request.httprequest.headers.get("Metro-Client-Secret")
        invoice_res = self.check_flavor_api(req_api_key, req_api_secret)
        print("invoice_res.status_code ==",invoice_res.status_code)
        company_o = request.env['res.company'].sudo().search([('enable_flavor_sync','=',True),('flavor_apikey', '=', req_api_key),
                                                              ('flavor_apisecret', '=', req_api_secret)], limit=1)
        print("company_o >>>>",company_o.name)
        if invoice_res.status_code != 200:
            return invoice_res
        else:
            try:
                _logger.info(data)
                partner, invoice = data.get("customer"), data.get("invoice")
                if not partner or not invoice:
                    return invalid_response(message='Either of the following are missing [Customer Data, Invoice Data].')

                if not partner.get("customer_name"):
                    return invalid_response(message='Customer name is missing.')
                else:
                    partner_obj = partner_o.sudo().search([('name','=',partner.get("customer_name")),
                                                           ('company_id','=',company_o.id)], limit=1)
                    if not partner_obj:
                        partner_obj = partner_o.sudo().create({
                                                                'name': partner.get("customer_name"),
                                                                'mobile': partner.get("customer_mobile"),
                                                                'email': partner.get("customer_email"),
                                                                'company_type':'person',
                                                                'company_id':company_o.id
                                                            })
                if not invoice.get("invoice_no"):
                    return invalid_response(message='Invoice Number is missing.')
                else:
                    invoice_obj = invoice_o.sudo().search([('flavor_ref_no', '=', invoice.get("invoice_no")),
                                                            ('company_id','=',company_o.id)])
                    if invoice_obj:
                        return invalid_response(message="Invoice already exists with this Invoice number: %s" % (invoice.get("invoice_no")))
                    else:
                        journal_obj = journal_o.sudo().search([('company_id','=',company_o.id),'|',('code','=','INV'),('name','=','Customer Invoices')], limit=1)
                        if not journal_obj:
                            return invalid_response(message="No Journal 'Customer Invoices' is found for the Company: %s. Please contact the ERP Admin to resolve this issue." % (company_o.name))
                        
                        if not invoice.get("invoice_line_item"):
                            return invalid_response(message='Invoice line is missing.')
                        else:
                            invoice_line_data = []
                            for line in invoice.get("invoice_line_item"):
                                if not line.get("item_type"):
                                    return invalid_response(message='Item Type is missing in Invoice Line.')

                                if line.get('tax_rate') != 0:
                                    acc_tax_obj = acc_tax_o.sudo().search(
                                        [('type_tax_use', '=', 'sale'), ('amount', '=', line.get('tax_rate')),
                                         ('company_id', '=', company_o.id)
                                         ], limit=1)
                                    print("acc_tax_obj FOUND", acc_tax_obj, acc_tax_obj.company_id)
                                    if not acc_tax_obj:                                    
                                        acc_tax_grp_obj = request.env['account.tax.group'].sudo().search(
                                            [("name", "=", 'TAX ' +str(line.get('tax_rate'))+'%')], limit=1)
                                        print("acc_tax_grp_obj FOUND", acc_tax_grp_obj)
                                        if not acc_tax_grp_obj:
                                            acc_tax_grp_obj = request.env['account.tax.group'].sudo().create(
                                                {'name': 'TAX ' + str(line.get('tax_rate')) + '%'})
                                            print("acc_tax_grp_obj CREATED", acc_tax_grp_obj)

                                        ##################################################################################################
                                        account_obj = request.env['account.account'].sudo().search([('company_id','=',company_o.id),
                                            ('name','=ilike','Sales Tax Account ' + str(line.get('tax_rate')) + '%')], limit=1)
                                        print("account_obj FOUND",account_obj)
                                        if not account_obj:
                                            account_obj = request.env['account.account'].sudo().sudo().create({
                                                                            'code':''.join([str(random.randint(0, 9)) for _ in range(6)]),
                                                                            'name':'Sales Tax Account '+str(line.get('tax_rate'))+"%",
                                                                            'user_type_id':request.env['account.account.type'].sudo().search([('name','=','Current Liabilities')])[0].id,
                                                                            'company_id': company_o.id,
                                                                         })
                                            print("account_obj CREATED",account_obj)

                                        print("account_obj >>>>>",account_obj)
                                        ##################################################################################################

                                        acc_tax_obj = acc_tax_o.sudo().create({
                                            'type_tax_use': 'sale',
                                            'amount': line.get('tax_rate'),
                                            'amount_type': 'percent',
                                            'company_id': company_o.id,
                                            'name': 'GST ' + str(line.get('tax_rate')) + '%',
                                            'description': str(line.get('tax_rate')) + ' %',
                                            'tax_group_id': acc_tax_grp_obj.id,
                                            'invoice_repartition_line_ids': [
                                                (0, 0, {
                                                    'factor_percent': 100,
                                                    'repartition_type': 'base',
                                                }),
                                                (0, 0, {
                                                    'factor_percent': 100,
                                                    'repartition_type': 'tax',
                                                    'account_id': account_obj.id,
                                                    # 'account_id': request.env['account.account'].sudo().search([('name','=ilike','Sales Tax Account%')],limit=1).id,
                                                }),
                                            ],
                                            'refund_repartition_line_ids': [
                                                (0, 0, {
                                                    'factor_percent': 100,
                                                    'repartition_type': 'base',
                                                }),
                                                (0, 0, {
                                                    'factor_percent': 100,
                                                    'repartition_type': 'tax',
                                                    'account_id': account_obj.id,
                                                    # 'account_id': request.env['account.account'].sudo().search([('name','=ilike','Sales Tax Account%')],limit=1).id,
                                                }),
                                            ],
                                        })


                                parent_product_categ_obj = product_categ_o.sudo().search([('name','=','All'), ('company_id','=',company_o.id)], limit=1)
                                if not parent_product_categ_obj:
                                    parent_product_categ_obj = product_categ_o.sudo().with_context({'from_company_create': True}).create({
                                        'name': 'All',
                                        'company_id': company_o.id
                                    })

                                product_categ_obj = product_categ_o.sudo().search([('name','=', 'Flavor'), ('company_id','=',company_o.id), ('parent_id','=',parent_product_categ_obj.id)], limit=1)
                                if not product_categ_obj:
                                    product_categ_obj = product_categ_o.sudo().with_context({'from_company_create': True}).create({
                                        'name': 'Flavor',
                                        'parent_id': parent_product_categ_obj.id,
                                        'company_id': company_o.id
                                    })
                                print("product_categ_obj ==",product_categ_obj)

                                print("company_o.account_sale_tax_id ==",company_o.account_sale_tax_id)
                                if not line.get("item_name"):
                                    return invalid_response(message='Item Name is missing in Invoice Line.')
                                product_obj = product_o.sudo().search([('name','=',line.get("item_name")),
                                                                       ('company_id','=',company_o.id)
                                                                       ])
                                print("product_obj FOUND",product_obj)
                                if not product_obj:
                                    product_obj = product_o.sudo().create({
                                                                            'name': line.get("item_name"),
                                                                            'categ_id': product_categ_obj.id,
                                                                            'company_id': company_o.id,
                                                                            'taxes_id': company_o.account_sale_tax_id and [(6, 0, [company_o.account_sale_tax_id.id])] or False
                                                                        })
                                    print("product_obj CREATED",product_obj)
                                    print("product_obj taxe",product_obj.taxes_id)
                                print("product_obj",product_obj)
                                acc_obj = False
                                if line.get('account_code'):
                                    acc_obj = accounts_o.sudo().search([('company_id','=',company_o.id), ('code','=',line.get('account_code'))], limit=1)
                                    if not acc_obj:
                                        return invalid_response(message='Account Code %s is missing in the Metro.' % (line.get('account_code')))
                                    else:
                                        pass

                                invoice_line_dic = {
                                    "product_id": product_obj.id,
                                    "product_uom_id": product_obj.uom_id.id,
                                    "quantity": line.get("item_quantity") or 1,
                                    "price_unit": line.get("item_unit_price"),
                                    "discount": line.get("discount_amount"),
                                    "discount_type": 'fixed',
                                    # "discount": line.get("discount_percentage"),
                                    "name": line.get("item_description", False) or (product_obj.description_sale or " "),
                                    "tax_ids": [(6, 0, [acc_tax_obj.id])] if line.get('tax_rate') != 0 else False,
                                    "price_subtotal": line.get("item_subtotal_amount"),
                                }
                                if acc_obj:
                                    invoice_line_dic.update({'account_id': acc_obj.id})
                                invoice_line_data.append((0, 0, invoice_line_dic))

                            invoice_avail = invoice_o.sudo().create({
                                'flavor_ref_no': invoice.get("invoice_no"),  
                                # 'name': invoice.get("invoice_no"),
                                'ref': invoice.get("invoice_id"),
                                'partner_id': partner_obj.id,
                                'move_type': 'out_invoice',
                                'journal_id': journal_obj.id,
                                # 'state': 'posted',
                                'invoice_date': invoice.get("invoice_issue_date"),
                                'invoice_date_due': invoice.get("invoice_due_date"),
                                'narration': invoice.get("invoice_remark") if invoice.get("invoice_remark") else "",
                                "invoice_line_ids": invoice_line_data,
                            })
                            data = {
                                'customer_id': invoice_avail.partner_id.id,
                                'customer_name': invoice_avail.partner_id.name,
                                'invoice_id': invoice_avail.id,
                                'invoice_name': invoice_avail.flavor_ref_no,  
                            }
                            return valid_response(data=data, message='Invoice Synced Successfully.')
                return invoice_res
            except Exception as e:
                return invalid_response(message="Metro Internal Server Error. %s" % e)

    @http.route('/flavor/account/invoice_cancel', auth="public", methods=['POST', 'GET'], csrf=False)
    def flavor_invoice_cancel(self, **kw):
        if not request.httprequest.data:
            return invalid_response(message='Data is missing. Please check and try again.')
        data = json.loads(request.httprequest.data)
        req_api_key = request.httprequest.headers.get("Metro-Client-Id")
        req_api_secret = request.httprequest.headers.get("Metro-Client-Secret")
        invoice_res = self.check_flavor_api(req_api_key, req_api_secret)
        company_o = request.env['res.company'].sudo().search([('enable_flavor_sync','=',True),('flavor_apikey', '=', req_api_key),
                                                              ('flavor_apisecret', '=', req_api_secret)], limit=1)
        if invoice_res.status_code != 200:
            return invoice_res
        else:
            try:
                invoice = data.get("invoice")
                if not invoice.get("invoice_no"):
                    return invalid_response(message='This invoice number is missing.')
                else:
                    invoice_o = request.env['account.move'].sudo().search(
                        [('flavor_ref_no', '=', invoice.get("invoice_no")),('company_id','=',company_o.id)], limit=1)
                    # invoice_o = request.env['account.move'].sudo().search([('name', '=', invoice.get("invoice_no"))])
                    if not invoice_o:
                        return invalid_response(message='This invoice number is not available in the database.')
                    else:
                        if invoice_o.state == 'cancel':
                            return invalid_response(message="This Invoice is already cancelled.")
                        else:
                            invoice_o.button_draft()
                            invoice_o.button_cancel()
                            data = {
                                'invoice_no': invoice_o.flavor_ref_no,  # added
                                # 'invoice_no': invoice_o.name,
                            }
                            return valid_response(data=data, message='Invoice is cancelled Successfully.')
            except Exception as e:
                return invalid_response(message="Metro Internal Server Error. %s" % e)

    @http.route('/flavor/account/payment_sync', auth="public", methods=['POST'], csrf=False)
    def flavor_account_payment(self, **kw):
        if not request.httprequest.data:
            return invalid_response(message='Data is missing. Please check and try again.')
        data = json.loads(request.httprequest.data)
        req_api_key = request.httprequest.headers.get("Metro-Client-Id")
        req_api_secret = request.httprequest.headers.get("Metro-Client-Secret")
        invoice_res = self.check_flavor_api(req_api_key, req_api_secret)
        company_o = request.env['res.company'].sudo().search([('enable_flavor_sync','=',True),('flavor_apikey', '=', req_api_key),
                                                              ('flavor_apisecret', '=', req_api_secret)], limit=1)
        print("data ==",data)
        print("company_o >>>",company_o.name)
        print('transaction_fee_flag' in data)
        print(data.get('transaction_fee_flag') == 1, data.get('transaction_fee_flag'))
        if invoice_res.status_code != 200:
            return invoice_res
        else:
            try:
                partner, receipt = data.get("customer"), data.get("reciept")
                journal_o = request.env['account.journal']
                if not partner or not receipt:
                    return invalid_response(message='Either of the following are missing [Customer, Receipt].')
                payment_o = request.env['account.payment']
                if not partner.get("customer_name"):
                    return invalid_response(message='Customer name is missing.')
                if not receipt.get("receipt_no"):
                    return invalid_response(message='Receipt number is missing.')
                if not receipt.get("invoice_no"):
                    return invalid_response(message='Invoice number is missing.')
                if not receipt.get("payment_date"):
                    return invalid_response(message='Payment Date is missing')
                invoice_obj = request.env['account.move'].sudo().search([
                                                                        ('flavor_ref_no', '=',receipt.get('invoice_no')),  
                                                                        ('company_id', '=', company_o.id)
                                                                    ], limit=1)
                print("invoice_obj ==",invoice_obj)
                if not invoice_obj:
                    return invalid_response(message='Invoice is missing for this payment receipt. Please first make an invoice.')
                if invoice_obj.payment_state == 'paid':
                    return invalid_response(message='You cannot register a payment because there is nothing left to pay on the selected journal items.')

                payment_obj = payment_o.sudo().search([('flavor_ref_no', '=', receipt.get("receipt_no")),('company_id', '=', company_o.id)])  
                if payment_obj:
                    return invalid_response(message="Receipt already exists with this Receipt number: %s" % (receipt.get("receipt_no")))

                if not receipt.get("payment_mode") or not receipt.get("payment_amount"):
                    return invalid_response(message='Either of the following are missing [Payment Mode, Payment Amount].')

                journal_obj = journal_o.sudo().search([('name', '=', receipt.get("payment_mode")),('company_id', '=', company_o.id)])
                if not journal_obj:
                    journal_obj = journal_o.sudo().create({
                                                            'name': receipt.get("payment_mode"),
                                                            'type': 'bank',
                                                            'code': 'BNK1',
                                                            'company_id': company_o.id,
                                                        })
                if invoice_obj.state != 'posted':
                    try:
                        invoice_obj.action_post()
                    except Exception as e:
                        return invalid_response(message="Invoice Post Error: %s" % e)
                action_data = invoice_obj.action_register_payment()
                context = action_data['context']
                context.update({
                    'default_flavor_ref_no': receipt.get("receipt_no"),  
                    # 'default_name': receipt.get("receipt_no"),
                    'default_journal_id': journal_obj.id,
                    'default_amount': receipt.get("payment_amount"),
                    'default_payment_date': receipt.get("payment_date")
                })
                wizard = Form(request.env['account.payment.register'].sudo().with_context(context)).save()
                action = wizard.action_create_payments()
                return_data = {
                    'receipt_name': receipt.get("receipt_no"),
                    'receipt_id': action.get('res_id'),
                    'invoice_no': receipt.get("invoice_no"),
                    'amount': receipt.get("payment_amount"),
                    'customer_name': partner.get("customer_name"),
                }
                print("\nFirst half done >>>")
                print('transaction_fee_flag' in data)
                print(data.get("transaction_fee_flag", 0) == 1)
                if 'transaction_fee_flag' in data and data.get("transaction_fee_flag", 0) == 1:
                    print("IS TRANSACTION FEE >>>")
                    journal_obj = journal_o.sudo().search([('name', '=', "Omise"),('company_id', '=', company_o.id)], limit=1)
                    if not journal_obj:
                        journal_obj = journal_o.sudo().create({
                                                                'name': "Omise",
                                                                'type': 'general',
                                                                'code': 'OMS',
                                                                'company_id': company_o.id,
                                                            })
                    print("journal_obj ..",journal_obj)

                    credit_acc_code = data['reciept']['payment_gateway_charges_account']['credit_account']['account_code']
                    debit_acc_code = data['reciept']['payment_gateway_charges_account']['debit_account']['account_code']
                    print("codesss")
                    account_credit_obj = request.env['account.account'].sudo().search([('company_id','=',company_o.id),
                                            ('code','=',credit_acc_code)], limit=1)
                    if not account_credit_obj:
                        return invalid_response(message="Payment Gateway Charges Credit Account not found in Metro.")
                    account_debit_obj = request.env['account.account'].sudo().search([('company_id','=',company_o.id),
                                            ('code','=',debit_acc_code)], limit=1)
                    if not account_debit_obj:
                        return invalid_response(message="Payment Gateway Charges Debit Account not found in Metro.")
                    print("DONE CHECKING THE ACOUNT OBJs")
                    total_fee = receipt['transaction_charges']['total_fee']
                    line_name = 'Payment Gateway Transaction Charges:: ' + 'Fee Flat: ' + str(receipt['transaction_charges']['fee_flat']) + \
                        ' / Fee Rate: ' + str(receipt['transaction_charges']['fee_rate']) + ' / VAT Rate: ' + str(receipt['transaction_charges']['vat_rate'])
                    print(total_fee, line_name)
                    line_ids = [
                        (0,0,{'account_id': account_credit_obj.id, 'partner_id': invoice_obj.partner_id.id, 'name': line_name, 'credit': float(total_fee)}),
                        (0,0,{'account_id': account_debit_obj.id, 'partner_id': invoice_obj.partner_id.id, 'name': line_name, 'debit': float(total_fee)})
                    ]
                    print(line_ids)
                    misc_data = {
                        'date': receipt.get("payment_date"),
                        'journal_id': journal_obj.id,
                        'flavor_ref_no': receipt.get("payment_reference_num"),
                        'ref': "Customer: " + partner.get("customer_name") + " / " + "Flavor Inv No: " + receipt.get("invoice_no","") + " / Metro Inv No: " + invoice_obj.name + " / Flavor Receipt No: " +  receipt.get("receipt_no"),
                        'line_ids': line_ids
                    }
                    print(misc_data)
                    misc_obj = request.env['account.move'].sudo().create(misc_data)
                    print(misc_obj)
                    misc_obj.sudo().action_post()
                    print("DONE")

                if invoice_obj.payment_state == 'partial':
                    return valid_response(data=return_data, message='Receipt Synced Successfully with partial amount of invoice.')
                elif invoice_obj.payment_state == 'paid':
                    return valid_response(data=return_data, message='Receipt Synced Successfully with fully paid amount of invoice.')
                else:
                    return valid_response(data=return_data,message='Receipt Synced Successfully.')
            except Exception as e:
                return invalid_response(message="Metro Internal Server Error. %s" % e)


    @http.route('/flavor/account/payment_cancel', auth="public", methods=['POST', 'GET'], csrf=False)
    def flavor_payment_cancel(self, **kw):
        if not request.httprequest.data:
            return invalid_response(message='Data is missing. Please check and try again.')
        data = json.loads(request.httprequest.data)
        req_api_key = request.httprequest.headers.get("Metro-Client-Id")
        req_api_secret = request.httprequest.headers.get("Metro-Client-Secret")
        invoice_res = self.check_flavor_api(req_api_key, req_api_secret)
        company_o = request.env['res.company'].sudo().search([('enable_flavor_sync','=',True),('flavor_apikey', '=', req_api_key),
                                                              ('flavor_apisecret', '=', req_api_secret)], limit=1)
        if invoice_res.status_code != 200:
            return invoice_res
        else:
            try:
                receipt = data.get("receipt")
                if not receipt.get("receipt_no"):
                    return invalid_response(message='Payment receipt number is missing.')
                else:
                    payment_o = request.env['account.payment'].sudo().search([('flavor_ref_no', '=', receipt.get("receipt_no")),
                                                                              ('company_id','=',company_o.id)])
                    # payment_o = request.env['account.payment'].sudo().search([('name', '=', receipt.get("receipt_no"))])
                    if not payment_o:
                        return invalid_response(message='This payment receipt is not available in the database.')
                    else:
                        if payment_o.state == 'cancel':
                            return invalid_response(message="Payment receipt is already cancelled with this Invoice number: %s" % (
                                receipt.get("receipt_no")))
                        else:
                            payment_o.action_draft()
                            payment_o.action_cancel()
                            #TODO:
                            #Check if 'payment_reference_num' is present in json, then cncel that JEntry.
                            if receipt.get("payment_reference_num", False):
                                misc_journal_entry = request.env['account.move'].sudo().search([('flavor_ref_no', '=',
                                                                                                 receipt.get("payment_reference_num"))])
                                for journal_entry in misc_journal_entry:
                                    journal_entry.button_draft()
                                    journal_entry.button_cancel()
                            data = {
                                'receipt_no': payment_o.flavor_ref_no,  
                            }
                            return valid_response(data=data, message='Payment receipt is cancelled Successfully.')
            except Exception as e:
                return invalid_response(message="Metro Internal Server Error. %s" % e)

    @http.route('/metro/account/fetch_accounts', auth='public', methods=['GET'], csrf=False)
    def send_charts_of_accounts(self):
        req_api_key = request.httprequest.headers.get("Metro-Client-Id")
        req_api_secret = request.httprequest.headers.get("Metro-Client-Secret")
        invoice_res = self.check_flavor_api(req_api_key, req_api_secret)

        if invoice_res.status_code != 200:
            return invoice_res
        else:
            company_o = request.env['res.company'].sudo().search([('enable_flavor_sync','=',True),
                                                              ('flavor_apikey', '=', req_api_key),
                                                              ('flavor_apisecret', '=', req_api_secret)], limit=1)
            accounts = http.request.env['account.account'].sudo().search([('company_id','=',company_o.id),
                                                                        ('is_off_balance','=',False),
                                                                        ('user_type_id.type', 'not in', ('receivable', 'payable')),
                                                                        ('deprecated', '=', False)])
            if not accounts:
                return invalid_response(message='This Charts of Accounts are not available for this Company in Metro.')

            accounts_data = []
            for account in accounts:
                accounts_data.append({
                    'code': account.code,
                    'name': account.name,
                    'account_type': str(account.user_type_id.type) + ' / ' + str(account.user_type_id.name),
                })

            # Return a JSON response with the list of accounts
            return valid_response(data=accounts_data, message='Successful!.')
