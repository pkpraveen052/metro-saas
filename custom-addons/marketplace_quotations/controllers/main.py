# -*- coding: utf-8 -*-

import ast

from odoo import http
from odoo.http import request
from odoo.addons.website.controllers.main import Website


class Marketplace(http.Controller):

    @http.route('/vendor/products', type='http', auth='public', website=True)
    def vendor_products(self, **post):
        print("\nvendor_products === post",post)
        values = {}
        if post.get('company_name') and post.get('vendor_uen'):
            company_obj = request.env['res.company'].sudo().search([('l10n_sg_unique_entity_number', '=', post.get('vendor_uen'))], limit=1)
            if company_obj:
                customer_company = request.env['res.partner'].sudo().search(
                    [('l10n_sg_unique_entity_number', '=', post.get('company_uen')),('company_type', '=', 'company')], limit=1)
                print("customer_company == ",customer_company)
                if not customer_company:
                    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>customer_company_not_found")
                    country_singapore = request.env['res.country'].search([('code', '=', 'SG')], limit=1)
                    customer_company = request.env['res.partner'].sudo().with_company(company_obj).create({
                        'name': post.get('company_name'),
                        'l10n_sg_unique_entity_number': post.get('company_uen'),
                        'company_type': 'company',
                        'company_id': company_obj.id,
                        'country_id': country_singapore.id,
                    })
                    print("CREATED   customer_company == ",customer_company)
                    customer = request.env['res.partner'].sudo().with_company(company_obj).create({
                        'name': post.get('login_user_name'),
                        'email': post.get('login_user_email'),
                        'company_type': 'person',
                        'parent_id': customer_company.id,
                        'company_id': company_obj.id,
                        'country_id': country_singapore.id,
                    })
                    print("CREATED   customer == ",customer)
                else:
                    print("FOUND ===")
                    country_singapore = request.env['res.country'].search([('code', '=', 'SG')], limit=1)            
                    customer = request.env['res.partner'].sudo().search(
                        [('email', '=', post.get('login_user_email')),('parent_id', '=', customer_company.id)], limit=1)
                    if not customer:
                        customer = request.env['res.partner'].sudo().with_company(company_obj).create({
                            'name': post.get('login_user_name'),
                            'email': post.get('login_user_email'),
                            'company_type': 'person',
                            'type': 'contact',
                            'parent_id': customer_company.id,
                            'company_id': company_obj.id,
                            'country_id': country_singapore.id,
                        })
                products = request.env['product.template'].sudo().search([('company_id','=',company_obj.id),('is_marketplace_product','=',True)])
                print("PRODUTCS  ====",products)
                if not products:
                    return request.redirect('/marketplace/noproduct')
                option_lines = []
                for product in products:
                    option_lines.append((0, 0, {
                                            'product_id': product.product_variant_id.id,
                                            'name':product.product_variant_id.get_product_multiline_description_sale(),
                                            'price_unit': product.product_variant_id.lst_price,
                                            'uom_id': product.product_variant_id.uom_id.id
                                        }))
                tag_record = request.env.ref('marketplace_quotations.demo_record_1')
                order = request.env['sale.order'].sudo().with_company(company_obj).create({
                    'partner_id': customer.id,
                    'sale_order_option_ids': option_lines,
                    'state': 'sent',
                    'company_id': company_obj.id,
                    'tag_ids': [(6, 0, [tag_record.id])] if tag_record else False
                })
                return request.redirect(order.get_portal_url())
            else:
                return request.redirect('/marketplace/error2')
               
        else:
            return request.redirect('/marketplace/error1')


    @http.route('/marketplace/error1', type='http', auth='public', website=True)
    def display_error1(self, **kw):
        return http.request.render('marketplace_quotations.view_marketplace_error_template1')

    @http.route('/marketplace/error2', type='http', auth='public', website=True)
    def display_error2(self, **kw):
        return http.request.render('marketplace_quotations.view_marketplace_error_template2')

    @http.route('/marketplace/noproduct', type='http', auth='public', website=True)
    def display_error3(self, **kw):
        return http.request.render('marketplace_quotations.view_marketplace_no_product_template')