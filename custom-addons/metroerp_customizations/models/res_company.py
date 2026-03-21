# -*- coding: utf-8 -*-
import os
from odoo import api, models, tools, fields,_
from odoo.modules.module import get_resource_path

from random import randrange
from PIL import Image
import base64
import io


class ResCompany(models.Model):
    _inherit = 'res.company'

    sales_tc = fields.Text(translate=True)
    sales_invoice_tc = fields.Text(translate=True)
    purchase_tc = fields.Text(translate=True)
    purchase_invoice_tc = fields.Text(translate=True)
    deliver_tc = fields.Text(translate=True)
    chart_of_accounts_installed = fields.Boolean(default=False, string="Chart of Accounts Installed")
    use_sales_tc = fields.Boolean(string='Sales Quotation Terms & Conditions', default=True)
    use_sales_invoice_tc = fields.Boolean(string='Sales Invoice Terms & Conditions', default=True)
    use_purchase_tc = fields.Boolean(string='Purchase Quotation Terms & Conditions')
    use_purchase_invoice_tc = fields.Boolean(string='Purchase Invoice Terms & Conditions')
    use_delivery_tc = fields.Boolean(string='Sales Delivery Terms & Conditions')

    # setting fields
    group_product_variant = fields.Boolean("Variants")
    group_uom = fields.Boolean("Units of Measure")
    group_discount_per_so_line = fields.Boolean('Discount')
    group_sale_order_template = fields.Boolean("Quotation Templates")
    group_sale_delivery_address = fields.Boolean("Customer Addresses")
    use_quotation_validity_days = fields.Boolean("Default Quotation Validity")
    group_warning_sale = fields.Boolean("Sale Order Warnings")
    group_auto_done_setting = fields.Boolean("Lock Confirmed Sales")
    group_proforma_sales = fields.Boolean(string="Pro-Forma Invoice", help="Allows you to send pro-forma invoice.")
    group_display_incoterm = fields.Boolean("Incoterms")
    automatic_invoice = fields.Boolean("Automatic Invoice",
                                       help="The invoice is generated automatically and available in the customer portal "
                                            "when the transaction is confirmed by the payment acquirer.\n"
                                            "The invoice is marked as paid and the payment is registered in the payment journal "
                                            "defined in the configuration of the payment acquirer.\n"
                                            "This mode is advised if you issue the final invoice at the order and not after the delivery.")
    group_show_purchase_receipts = fields.Boolean(string='Purchase Receipt')
    group_show_sale_receipts = fields.Boolean(string='Sale Receipt')
    group_warning_account = fields.Boolean(string="Warnings in Invoices")
    group_cash_rounding = fields.Boolean(string="Cash Rounding")
    group_analytic_accounting = fields.Boolean(string="Analytic Accounting")
    group_analytic_tags = fields.Boolean(string="Analytic Tags")
    
    # inventory setting field
    group_warning_stock = fields.Boolean("Warnings for Stock")
    group_stock_sign_delivery = fields.Boolean("Signature")
    group_stock_tracking_lot = fields.Boolean("Packages")
    group_stock_tracking_owner = fields.Boolean("Consignment")
    group_lot_on_delivery_slip = fields.Boolean("Display Lots & Serial Numbers on Delivery Slips")
    group_lot_on_invoice = fields.Boolean("Display Lots & Serial Numbers on Invoices")
    group_expiry_date_on_delivery_slip = fields.Boolean("Display Expiration Dates on Delivery Slips")
    group_stock_production_lot = fields.Boolean("Lots & Serial Numbers")
    group_stock_multi_locations = fields.Boolean('Storage Locations')
    group_stock_adv_location = fields.Boolean("Multi-Step Routes")
    module_stock_picking_batch = fields.Boolean("Batch Pickings")
    module_stock_landed_costs = fields.Boolean("Landed Costs")
    use_security_lead = fields.Boolean(string="Security Lead Time for Sales")
    use_po_lead = fields.Boolean(string="Security Lead Time for Purchase")
    delivery_product_description = fields.Boolean(string="Delivery Order Product Description")

    tax_calculation_rounding_method = fields.Selection([
        ('round_per_line', 'Round per Line'),
        ('round_globally', 'Round Globally'),
    ], default='round_globally', string='Tax Calculation Rounding Method')

    order_date_same_as_quotation_date = fields.Boolean(string='Order date same as Quotation Date')
    confirmation_date_same_as_order_deadline = fields.Boolean(string='Confirmation date same as Order Deadline')
    quotation_auto_sent = fields.Boolean(string='Sales Quotation Auto Sent',default=False)
    ks_enable_currency_symbol_on_dynamic_report = fields.Boolean('Currency Symbol On Dynamic Report')
    display_customer_name_on_tax_report = fields.Boolean('Display Customer/Vendor Name On Tax Report')
    

    auto_currency_rate = fields.Boolean(
        string="Automatic Currency Rates",
        default=True
    )

    currency_rate_service = fields.Selection(
        [
            ('mas_sgd', 'MAS (SGD)')
        ],
        string="Exchange Rate Service",
        default='mas_sgd'
    )
    merge_bank_accounts = fields.Boolean('Merge Bank & Cash Accounts in BS', default=True)

    def _get_default_favicon(self, original=False):
        img_path = get_resource_path('metroerp_customizations', 'static/src/img/favicon.png')
        with tools.file_open(img_path, 'rb') as f:
            if original:
                return base64.b64encode(f.read())
            color = (randrange(32, 224, 24), randrange(32, 224, 24), randrange(32, 224, 24))
            original = Image.open(f)
            new_image = Image.new('RGBA', original.size)
            height = original.size[1]
            width = original.size[0]
            bar_size = 1
            for y in range(height):
                for x in range(width):
                    pixel = original.getpixel((x, y))
                    if height - bar_size <= y + 1 <= height:
                        new_image.putpixel((x, y), (color[0], color[1], color[2], 255))
                    else:
                        new_image.putpixel((x, y), (pixel[0], pixel[1], pixel[2], pixel[3]))
            stream = io.BytesIO()
            new_image.save(stream, format="PNG")
            return base64.b64encode(stream.getvalue())
        
    favicon = fields.Binary(string="Company Favicon", help="This field holds the image used to display a favicon for a given company.", default=_get_default_favicon)
        
    
    
    @api.model
    def default_get(self, fields_list):
        defaults = super(ResCompany, self).default_get(fields_list)
        chart_template = self.env['account.chart.template'].search([], limit=1)
        if chart_template:
            defaults['chart_template_id'] = chart_template.id

        return defaults
    
    # def install_chart_of_accounts(self):
    #     if self.chart_template_id:
    #         self.chart_template_id._load(15.0, 15.0, self)
    #         self.chart_of_accounts_installed = True

    def install_chart_of_accounts(self):
        if self.chart_template_id:
            self.chart_template_id._load(15.0, 15.0, self)
            self.chart_of_accounts_installed = True

            # Ensure tax template values are assigned properly
            for tax_template in self.chart_template_id.tax_template_ids:
                if tax_template:
                    # Find the corresponding account.tax record
                    tax = self.env['account.tax'].search([
                        ('company_id', '=', self.env.company.id),
                        ('name', '=', tax_template.name),  # Matching by template ID
                        ('amount', '=', tax_template.amount),
                        ('type_tax_use', '=', tax_template.type_tax_use),
                    ], limit=1)

                    if tax:
                        tax.write({
                            'for_IRAS': tax_template.for_IRAS,
                            'iras_supplies_type': tax_template.iras_supplies_type,
                        })

    #This code for server action to update the existing taxes
    def update_existing_taxes(self):
        """ Updates existing account.tax records based on tax templates. """
        for tax_template in self.chart_template_id.tax_template_ids:
            if tax_template:
                # Find the corresponding account.tax record
                tax = self.env['account.tax'].search([
                    ('company_id', '=', self.env.company.id),
                    ('name', '=', tax_template.name),  # Matching by name
                    ('amount', '=', tax_template.amount),  # Ensuring correct tax rate
                    ('type_tax_use', '=', tax_template.type_tax_use),
                ], limit=1)

                if tax:
                    tax.write({
                        'for_IRAS': tax_template.for_IRAS,
                        'iras_supplies_type': tax_template.iras_supplies_type,
                    })


    @api.model
    def reset_company_logo(self):
        order_objs = self.search([])
        for order_obj in order_objs:
            order_obj.logo = open(
                os.path.join(tools.config['root_path'], 'addons', 'base', 'res', 'res_company_logo.png'),
                'rb').read().encode('base64')

    def get_logo_data_url(self):
        url = image_data_uri(self.logo)
        return url
    
    def create_apps_background_image(self):
        company_obj = self.sudo().search([('id','=',1)], limit=1)
        if company_obj:
            self.background_image = company_obj.background_image

    @api.model
    def create(self, vals):
        # Initialize error log
        error_log = ''
        company_name = ''

        try:
            ctx = dict(self._context) or {}
            ctx.update({'new_company': True})
            if not vals.get('favicon'):
                vals['favicon'] = self._get_default_favicon()  
            obj = super(ResCompany, self.with_context(ctx)).create(vals)
            company_name = obj.name  # Capture company name
            obj.sudo().partner_id.write({'company_id': obj.id})
            obj.create_companies_sequence()
            obj.sudo().create_product_category()
            obj.create_pricelist()
            obj.create_sales_team()
            obj.create_payment_term()
            obj.create_apps_background_image()

        except Exception as e:
            # Rollback the transaction
            self.env.cr.rollback()
            
            # Log the error
            error_log += f'Error creating company "{company_name}": {e}\n'
            error_from = _('Unknown')
            for method_name in ['create_companies_sequence', 'create_product_category', 'create_pricelist', 'create_sales_team', 'create_payment_term']:
                if method_name in str(e):
                    error_from = _(method_name)
                    break  # Stop searching once we've found the method name
            error_log += f'Error from: {error_from}\n'
            error_log += f'Detailed error: {e}\n'

            # Log the error in the company creation log model
            self.env['company.creation.logs'].create({
                'description': error_log,
                'error_from': error_from,
                'company_name': company_name,
                'state': 'error'
            })

            # Re-raise the exception to ensure Odoo's default error handling
            print("\n\nMAIN >>>>>>>>>>>>> EXCEPTON>>>>>>>>")
            raise

        else:
            # Commit the transaction
            # self.env.cr.commit() #13jan25
            # Log success
            self.env['company.creation.logs'].create({
                'description': f'Company "{company_name}" created successfully',
                'company_name': company_name,
                'state': 'success'
            })

        return obj

    def write(self, values):
        # sudo needed to avoid access error on product.list0 (id=1)
        if 'currency_id' in values:
            self = self.sudo()
        return super(ResCompany, self).write(values)

    def create_companies_sequence(self):
        obj = self
        so_sequence = self.env['ir.sequence'].search([('code', '=', 'sale.order'), ('company_id', '=', obj.id)])
        if not so_sequence:
            sale_order_sequence = self.env['ir.sequence'].create({
                'name': 'Sale Order Sequence - ' + obj.name,
                'code': 'sale.order',
                'padding': 5,
                'prefix': 'S',
                'company_id': obj.id
            })
        po_sequence = self.env['ir.sequence'].search([('code','=','purchase.order'),('company_id','=',obj.id)])
        if not po_sequence:
            purchase_order_sequence = self.env['ir.sequence'].create({
                'name': 'Purchase Order Sequence - ' + obj.name,
                'code': 'purchase.order',
                'padding': 5,
                'prefix': 'P',
                'company_id': obj.id,
                # Add other sequence options as needed
            })
        picking_sequence = self.env['ir.sequence'].search([('code', '=', 'stock.picking'), ('company_id', '=', obj.id)])
        if not picking_sequence:
            stock_picking_sequence = self.env['ir.sequence'].create({
                'name': 'Stock Picking Sequence - ' + obj.name,
                'code': 'stock.picking',
                'padding': 5,
                'prefix': 'INT/',
                'company_id': obj.id
            })
        orderpoint_sequence = self.env['ir.sequence'].search([('code', '=', 'stock.orderpoint'), ('company_id', '=', obj.id)])
        if not orderpoint_sequence:
            order_point_sequence = self.env['ir.sequence'].create({
                'name': 'Stock Orderpoint Sequence - ' + obj.name,
                'code': 'stock.orderpoint',
                'padding': 5,
                'prefix': 'OP/',
                'company_id': obj.id
            })
        recurringpayment_sequence = self.env['ir.sequence'].search([('code', '=', 'recurring.payment'), ('company_id', '=', obj.id)])
        if not recurringpayment_sequence:
            recurring_payment_sequence = self.env['ir.sequence'].create({
                'name': 'Recurring Payments Sequence - ' + obj.name,
                'code': 'recurring.payment',
                'padding': 3,
                'prefix': 'RP',
                'company_id': obj.id
            })
        package_sequence = self.env['ir.sequence'].search([('code', '=', 'stock.quant.package'), ('company_id', '=', obj.id)])
        if not package_sequence:
            packages_sequence = self.env['ir.sequence'].create({
                'name': 'Packages Sequence - ' + obj.name,
                'code': 'stock.quant.package',
                'padding': 7,
                'prefix': 'PACK',
                'company_id': obj.id
            })
        pack_sequence = self.env['ir.sequence'].search([('code', '=', 'stock.lot.tracking'), ('company_id', '=', obj.id)])
        if not pack_sequence:
            packs_sequence = self.env['ir.sequence'].create({
                'name': 'Packs Sequence - ' + obj.name,
                'code': 'stock.lot.tracking',
                'padding': 7,
                'prefix': '',
                'company_id': obj.id
            })
        stocklot_sequence = self.env['ir.sequence'].search([('code', '=', 'stock.lot.serial'), ('company_id', '=', obj.id)])
        if not stocklot_sequence:
            serial_number_sequence = self.env['ir.sequence'].create({
                'name': 'Serial Numbers Sequence - ' + obj.name,
                'code': 'stock.lot.serial',
                'padding': 7,
                'prefix': '',
                'company_id': obj.id
            })
        invoice_response_queueout = self.env['ir.sequence'].search([('code', '=', 'invoice.responses.queue.out'), ('company_id', '=', obj.id)])
        if not invoice_response_queueout:
            invoice_response_queue_out_sequence = self.env['ir.sequence'].create({
                'name': 'Invoice Response Queue Out Sequence - ' + obj.name,
                'code': 'invoice.responses.queue.out',
                'padding': 4,
                'prefix': 'INVRESP/',
                'company_id': obj.id
            })
        accountreconcile_sequence = self.env['ir.sequence'].search([('code', '=', 'account.reconcile'), ('company_id', '=', obj.id)])
        if not accountreconcile_sequence:
            account_reconcile_sequence = self.env['ir.sequence'].create({
                'name': 'Account reconcile Sequence - ' + obj.name,
                'code': 'account.reconcile',
                'padding': 0,
                'prefix': 'A',
                'company_id': obj.id
            })
        # landed costs sequence
        stock_landed_costs = self.env['ir.sequence'].search([('code', '=', 'stock.landed.cost'), ('company_id', '=', obj.id)])
        if not stock_landed_costs:
            stock_landed_costs_sequence = self.env['ir.sequence'].create({
                'name': 'Stock Landed Costs - ' + obj.name,
                'code': 'stock.landed.cost',
                'padding': 4,
                'prefix': 'LC/%(year)s/',
                'company_id': obj.id
            })
        # spend money sequence
        spend_money = self.env['ir.sequence'].search(
            [('code', '=', 'account.move.spend'), ('company_id', '=', obj.id)])
        if not spend_money:
            spend_money_sequence = self.env['ir.sequence'].create({
                'name': 'Spend Money - ' + obj.name,
                'code': 'account.move.spend',
                'padding': 4,
                'prefix': 'SM/%(range_year)s/',
                'company_id': obj.id,
                'use_date_range': True
            })
        # receive money sequence
        receive_money = self.env['ir.sequence'].search(
            [('code', '=', 'account.move.receive'), ('company_id', '=', obj.id)])
        if not receive_money:
            receive_money_sequence = self.env['ir.sequence'].create({
                'name': 'Receive Money - ' + obj.name,
                'code': 'account.move.receive',
                'padding': 4,
                'prefix': 'RM/%(range_year)s/',
                'company_id': obj.id,
                'use_date_range': True
            })

    def create_product_category(self):
        self.ensure_one()
        obj = self
        ProductCategory = self.env['product.category'].sudo()

        # "All" category
        all_categ = ProductCategory.search([('name', '=', 'All'), ('company_id', '=', obj.id)], limit=1)
        if not all_categ:
            all_categ_ref = self.env.ref('product.product_category_all')
            all_categ = all_categ_ref.sudo().with_context({'from_company_create': True}).copy()
            all_categ.sudo().write({'company_id': obj.id})

        # "Expenses"
        exp_categ = ProductCategory.search([('name', '=', 'Expenses'), ('company_id', '=', obj.id)], limit=1)
        if not exp_categ:
            exp_ref = self.env.ref('product.cat_expense')
            exp_categ = exp_ref.sudo().with_context({'from_company_create': True}).copy()
            exp_categ.sudo().write({'company_id': obj.id, 'parent_id': all_categ.id})

        # "Saleable"
        sale_categ = ProductCategory.search([('name', '=', 'Saleable'), ('company_id', '=', obj.id)], limit=1)
        if not sale_categ:
            sale_ref = self.env.ref('product.product_category_1')
            sale_categ = sale_ref.sudo().with_context({'from_company_create': True}).copy()
            sale_categ.sudo().write({'company_id': obj.id, 'parent_id': all_categ.id})

    def create_pricelist(self):
        obj = self
        public_pricelist = self.env['product.pricelist'].sudo().search([('name', '=', 'Public Pricelist'), ('company_id', '=', obj.id)])
        if not public_pricelist:
            public_pricelist_vals = {
                'name': 'Public Pricelist',
                'company_id': obj.id,
                'currency_id': obj.currency_id.id
            }
            self.env['product.pricelist'].with_context({'from_create_company':True,'company_id':obj.id}).sudo().create(public_pricelist_vals)


    def create_sales_team(self):
        obj = self
        sales_team = self.env['crm.team'].sudo().search([('name', '=', 'Sales'), ('company_id', '=', obj.id)])
        if not sales_team:
            sales_team_obj = self.env['crm.team'].sudo().create({
                'name': 'Sales',
                'company_id': obj.id
            })
            


    def create_payment_term(self):
        existing_payment_terms = self.env['account.payment.term'].search([('company_id', '=', self.id)])
        if existing_payment_terms:
            print("/n/n/n/n/nPayment terms already exist for this company.")
            return
        

        payment_terms_data = [
            {
                'name': 'Immediate Payment',
                'note': 'Payment terms: Immediate Payment',
                'company_id': self.id,
            },
            {
                'name': '15 Days',
                'note': 'Payment terms: 15 Days',
                'company_id': self.id,
                'line_ids': [(0, 0, {'value': 'balance', 'value_amount': 0.0, 'sequence': 500, 'days': 15, 'option': 'day_after_invoice_date'})],
            },
            {
                'name': '21 Days',
                'note': 'Payment terms: 21 Days',
                'company_id': self.id,
                'line_ids': [(0, 0, {'value': 'balance', 'value_amount': 0.0, 'sequence': 500, 'days': 21, 'option': 'day_after_invoice_date'})],
            },
            {
                'name': '30 Days',
                'note': 'Payment terms: 30 Days',
                'company_id': self.id,
                'line_ids': [(0, 0, {'value': 'balance', 'value_amount': 0.0, 'sequence': 500, 'days': 30, 'option': 'day_after_invoice_date'})],
            },
            {
                'name': '45 Days',
                'note': 'Payment terms: 45 Days',
                'company_id': self.id,
                'line_ids': [(0, 0, {'value': 'balance', 'value_amount': 0.0, 'sequence': 500, 'days': 45, 'option': 'day_after_invoice_date'})],
            },
            {
                'name': '2 Months',
                'note': 'Payment terms: 2 Months',
                'company_id': self.id,
                'line_ids': [(0, 0, {'value': 'balance', 'value_amount': 0.0, 'sequence': 500, 'days': 60, 'option': 'day_after_invoice_date'})],
            },
            {
                'name': 'End of Following Month',
                'note': 'Payment terms: End of Following Month',
                'company_id': self.id,
                'line_ids': [(0, 0, {'value': 'balance', 'value_amount': 0.0, 'sequence': 500, 'days': 31, 'option': 'day_following_month'})],
            },
            {
                'name': '30% Now, Balance 60 Days',
                'note': 'Payment terms: 30% Now, Balance 60 Days',
                'company_id': self.id,
                'line_ids': [
                    (0, 0, {'value': 'percent', 'value_amount': 30.0, 'sequence': 400, 'days': 0, 'option': 'day_after_invoice_date'}),
                    (0, 0, {'value': 'balance', 'value_amount': 0.0, 'sequence': 500, 'days': 60, 'option': 'day_after_invoice_date'}),
                ],
            },
            {
                'name': 'End of Month',
                'note': 'Payment terms: End of Month',
                'company_id': self.id,
                'line_ids': [
                    (5, 0), (0, 0, {'value': 'balance', 'value_amount': 0.0, 'sequence': 500, 'days': 0,
                                    'option': 'day_after_invoice_date', 'day_of_the_month': 31})
                ],
            },
        ]
        payment_term_model = self.env['account.payment.term']
        for term_data in payment_terms_data:
            payment_term_model.create(term_data)



    def replace_payment_terms(self):
        obj = self
        # Update payment terms for res.partner
        partners = self.env['res.partner'].sudo().search([('company_id','=', obj.id), ('property_payment_term_id','!=', False)])
        for partner in partners:
            payment_obj = self.env['account.payment.term'].sudo().search([('name','=',partner.property_payment_term_id.name),('company_id','=',obj.id)], limit=1)
            if payment_obj:
                partner.write({'property_payment_term_id': payment_obj.id})
            else:
                if not partner.property_payment_term_id.company_id:
                    partner.property_payment_term_id.write({'company_id': obj.id})
                else:
                    payment_obj = self.env['account.payment.term'].create({'name':partner.property_payment_term_id.name, 'company_id': obj.id})
                    partner.write({'property_payment_term_id': payment_obj.id})
                    
        partners = self.env['res.partner'].sudo().search([('company_id','=', obj.id), ('property_supplier_payment_term_id','!=', False)])
        for partner in partners:
            payment_supp_obj = self.env['account.payment.term'].sudo().search([('name','=',partner.property_supplier_payment_term_id.name),('company_id','=',obj.id)], limit=1)
            if payment_supp_obj:
                partner.write({'property_payment_term_id': payment_supp_obj.id})
            else:
                if not partner.property_supplier_payment_term_id.company_id:
                    partner.property_supplier_payment_term_id.write({'company_id': obj.id})
                else:
                    payment_supp_obj = self.env['account.payment.term'].create({'name':partner.property_supplier_payment_term_id.name, 'company_id': obj.id})
                    partner.write({'property_payment_term_id': payment_supp_obj.id})

        
        # Update payment terms for sale.order
        orders = self.env['sale.order'].sudo().search([('company_id','=', obj.id), ('payment_term_id','!=', False)])
        for order in orders:
            payment_term = order.payment_term_id
            payment_obj = self.env['account.payment.term'].sudo().search([('name','=',payment_term.name), ('company_id','=',obj.id)], limit=1)
            if payment_obj:
                order.write({'payment_term_id': payment_obj.id})
            else:
                if not order.payment_term_id.company_id:
                    order.payment_term_id.write({'company_id': obj.id})
                else:
                    payment_obj = self.env['account.payment.term'].create({'name':payment_term.name, 'company_id': obj.id})
                    order.write({'payment_term_id': payment_obj.id})
        
        # Update payment terms for purchase.order
        purchase_orders = self.env['purchase.order'].sudo().search([('company_id','=', obj.id), ('payment_term_id','!=', False)])
        for purchase_order in purchase_orders:
            payment_term = purchase_order.payment_term_id
            payment_obj = self.env['account.payment.term'].sudo().search([('name','=',payment_term.name), ('company_id','=',obj.id)], limit=1)
            if payment_obj:
                purchase_order.write({'payment_term_id': payment_obj.id})
            else:
                if not purchase_order.payment_term_id.company_id:
                    payment_term_id.payment_term_id.write({'company_id': obj.id})
                else:
                    payment_obj = self.env['account.payment.term'].create({'name':payment_term.name, 'company_id': obj.id})
                    purchase_order.write({'payment_term_id': payment_obj.id})

        # Update payment terms for account.move
        invoices = self.env['account.move'].sudo().search([('company_id','=', obj.id), ('invoice_payment_term_id','!=', False)])
        for invoice in invoices:
            payment_term = invoice.invoice_payment_term_id
            payment_obj = self.env['account.payment.term'].sudo().search([('name','=',payment_term.name), ('company_id','=',obj.id)], limit=1)
            if payment_obj:
                invoice.write({'invoice_payment_term_id': payment_obj.id})
            else:
                if not invoice.invoice_payment_term_id.company_id:
                    invoice.invoice_payment_term_id.write({'company_id': obj.id})
                else:
                    payment_obj = self.env['account.payment.term'].create({'name':payment_term.name, 'company_id': obj.id})
                    invoice.write({'invoice_payment_term_id': payment_obj.id})

