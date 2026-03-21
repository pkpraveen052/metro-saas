
from odoo import api, models, tools, registry, exceptions, tools, http,_
import json
from odoo.http import request, Response
from odoo.exceptions import AccessDenied


def invalid_response(message=None):
    return http.Response(
        status=404,
        content_type="application/json",
        response=json.dumps({
            # "status": False,
            "message": str(message),
        }),
    )
def valid_response(message=None):
    return http.Response(
        status=200,
        content_type="application/json",
        response=json.dumps({
            # "status": True,
            "message": str(message),
            # "data": data
        }),
    )


class CustomCompanyApiController(http.Controller):

    def check_api_key_secret(self, api_key, api_secret):
        properties_key = request.env['ir.property'].sudo().search([('name', '=', 'Company API KEY')])
        properties_secret= request.env['ir.property'].sudo().search([('name', '=', 'Company API SECRET')])
        print("properties_key() >>>>>>", properties_key)
        print("properties_secret() >>>>>>", properties_secret)
        if not api_key or not api_secret:
            print("1", properties_key)
            return invalid_response(message='Something went to wrong!!')
        if not properties_key.value_text or not properties_secret.value_text:
            print("2", properties_key)
            return invalid_response(message='Something went to wrong!!')
        elif api_key != properties_key.value_text or api_secret != properties_secret.value_text:
            print("3", properties_key)
            return invalid_response(message="Something went to wrong!!")
        else:
            return valid_response(message='Successful')

    @http.route('/api/metrogroup/company', auth='public', csrf=False, method=['post'])
    def metro_access_security(self, **kw):
        data = json.loads(request.httprequest.data)
        api_key = request.httprequest.headers.get("API-Key")
        api_secret = request.httprequest.headers.get("API-Secret")
        print("api_key________________>>", api_key, data)
        print("api_secreat>>>>>>>>>>>PPP", api_secret)
        company_security = self.check_api_key_secret(api_key, api_secret)
        if company_security.status_code != 200:
            return company_security
        else:
            try:
                erp_group_id = request.env.ref('metroerp_customizations.sub_admin_group').sudo()
                sale_group_id = request.env.ref('sales_team.group_sale_manager').sudo()
                stock_group_id = request.env.ref('stock.group_stock_manager').sudo()
                purchase_group_id = request.env.ref('purchase.group_purchase_manager').sudo()
                peppol_group_id = request.env.ref('metro_einvoice_datapost.group_peppol_admin').sudo()
                account_group_id = request.env.ref('account.group_account_manager').sudo()
                if not request.httprequest.data:
                    return invalid_response(message='Data is missing. Please check and try again.')
                # for key, value in data.items():
                #     if not value:
                #         return invalid_response(message="Company %s is missing" % (key))
                company_check = request.env['res.company'].sudo().search([('name', '=', data.get('name'))])
                company_uen = request.env['res.company'].sudo().search([('l10n_sg_unique_entity_number', '=', data.get('l10n_sg_unique_entity_number'))])
                user_name_check = request.env['res.users'].sudo().search([('name', '=', data.get('company_admin_name'))])
                user_email_check = request.env['res.users'].sudo().search([('login', '=', data.get('company_admin_email'))])
                if company_check:
                    return invalid_response(message="Company %s is Already Created" % (company_check.name))
                if company_uen:
                    return invalid_response(message="Company UEN %s is Already Set" % (company_uen.l10n_sg_unique_entity_number))
                if user_name_check:
                    return invalid_response(message="User %s is Already Created" % (user_name_check.name))
                if user_email_check:
                    return invalid_response(message="User %s is Already Created" % (user_email_check.name))
                country = request.env['res.country'].sudo().browse(data.get('country_id'))
                record_data = {'name': data.get('name'),
                               'email': data.get('email'),
                               'phone': data.get('phone'),
                               'street': data.get('street'),
                               'street2': data.get('street2'),
                               'zip': data.get('zip'),
                               'country_id': country.id,
                               'website': 'http://www.metrogroup.solutions',
                               'l10n_sg_unique_entity_number': data.get('l10n_sg_unique_entity_number'),
                               }
                company = request.env['res.company'].sudo().create(record_data)
                admin_user = request.env['res.users'].sudo().search([('id', '=', '2')])
                if admin_user:
                    admin_user.write({'company_ids': [(4, company.id)]})
                    admin_user.company_ids = [(4, company.id)]

                user_record = request.env['res.users'].sudo().create({'name': data.get('company_admin_name'),
                                                                      'login': data.get('company_admin_email'),
                                                                      'email': data.get('company_admin_email'),
                                                                      'phone': data.get('company_admin_phone'),
                                                                      'company_ids': company.ids,
                                                                      'company_id': company.id,
                                                                      'groups_id': [(6, 0, [erp_group_id.id,sale_group_id.id,stock_group_id.id,purchase_group_id.id,peppol_group_id.id,account_group_id.id])]})
                if company.chart_template_id and company:
                    company.chart_template_id._load(15.0, 15.0, company)
                    company.chart_of_accounts_installed = True
                if company and user_record:
                    return company_security
                else:
                    return invalid_response(message="UnSuccessful")
            except Exception as e:
                return invalid_response(message="Metro Internal Server Error. %s" % e)
