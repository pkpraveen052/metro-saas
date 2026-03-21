from odoo import models,fields,_,api
from odoo.addons.account.models.company import ONBOARDING_STEP_STATES,DASHBOARD_ONBOARDING_STATES
from odoo.modules.module import get_module_resource
import base64


class ResCompany(models.Model):
    _inherit = "res.company"

    # account_setup_admin_details_state = fields.Selection(ONBOARDING_STEP_STATES,
    #                                                  string="State of the onboarding admin detail step",
    #                                                  default='not_done')
    account_invoice_onboarding_state = fields.Selection(DASHBOARD_ONBOARDING_STATES,
                                                        string="State of the account invoice onboarding panel",
                                                        default='closed')
    purchase_onboarding_state = fields.Selection(
        [('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done"), ('closed', "Closed")],
        string="State of the sale onboarding panel", default='not_done')
    purchase_dashboard_onboarding_state = fields.Selection(DASHBOARD_ONBOARDING_STATES,
                                                          string="State of the account dashboard onboarding panel",
                                                          default='not_done')
    account_setup_custom_invoice_layout = fields.Selection(ONBOARDING_STEP_STATES,
                                                     string="State of the onboarding custom invoice layout step",
                                                     default='not_done')
    custom_group_multi_currency = fields.Boolean(string='Multi-Currencies',
                                          help="Allows to work in a multi currency environment")
    sale_onboarding_tc_state = fields.Selection(
        [('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")],
        string="State of the onboarding terms and condition step", default='not_done')

    account_onboarding_delivery_layout_state = fields.Selection(
        [('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")],
        string="State of the onboarding delivery layout step", default='not_done')

    sale_onboarding_product_state = fields.Selection(
        [('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")],
        string="State of the onboarding product step", default='not_done')

    sale_onboarding_partner_state = fields.Selection(
        [('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")],
        string="State of the onboarding partner step", default='not_done')

    sale_onboarding_quotation_layout_state = fields.Selection(
        [('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")],
        string="State of the onboarding quotation layout step", default='not_done')

    purchase_onboarding_tc_state = fields.Selection(
        [('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")],
        string="State of the purchase onboarding terms and condition step", default='not_done')
    purchase_onboarding_rfq_layout_state = fields.Selection(
        [('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")],
        string="State of the onboarding ref layout step", default='not_done')

    purchase_onboarding_po_layout_state = fields.Selection(
        [('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")],
        string="State of the onboarding PO layout step", default='not_done')

    purchase_onboarding_bill_state = fields.Selection(
        [('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")],
        string="State of the purchase onboarding bill step", default='not_done')

    purchase_onboarding_partner_state = fields.Selection(
        [('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")],
        string="State of the purchase onboarding partner step", default='not_done')

    purchase_onboarding_sample_order_state = fields.Selection(
        [('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")],
        string="State of the purchase onboarding sample order step", default='not_done')

    @api.model
    def setting_init_sales_tc_action(self):
        """ Called by the 'Bank Accounts' button of the setup bar."""
        view_id = self.env.ref('metroerp_onboarding.sales_custom_tc_wizard').id
        return {'type': 'ir.actions.act_window',
                'name': _('Sales Terms and Conditions'),
                'res_model': 'sales.terms.condition',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
        }

    @api.model
    def action_open_base_onboarding_company(self):
        """ Onboarding step for company basic information. """
        action = self.env["ir.actions.actions"]._for_xml_id("metroerp_onboarding.action_open_custom_onboarding_company_popup")
        action['res_id'] = self.env.company.id
        return action

    @api.model
    def setting_init_custom_invoice_layout_action(self):
        """ Called by the 'Bank Accounts' button of the setup bar."""
        view_id = self.env.ref('metroerp_onboarding.ks_report_configuration_form_custom_popup').id
        ks_report_id = self.env.ref('account.account_invoices').id
        ks_model_id = self.env.ref('account.model_account_move').id
        report_style_id = self.env.ref('ks_custom_report_layouts.ks_sale_styles_1').id
        record_id = self.env['ks.report.configuration'].search([('ks_report_id', '=', ks_report_id), ('company_id', '=', self.env.company.id), ('name', '=', 'Invoice')])
        return {'type': 'ir.actions.act_window',
                'name': _('Invoice Layout'),
                'res_model': 'ks.report.configuration',
                'target': 'new',
                'view_mode': 'form',
                'res_id': record_id.id,
                'views': [[view_id, 'form']],
                'context': {'default_ks_report_id': ks_report_id, 'default_ks_model_id': ks_model_id, 'default_name': 'Invoice', 'default_sale_report_style_id':report_style_id},
                }

    @api.model
    def setting_chart_of_accounts_action(self):
        """ Called by the 'Chart of Accounts' button of the setup bar."""
        company = self.env.company
        company.sudo().set_onboarding_step_done('account_setup_coa_state')

        # If an opening move has already been posted, we open the tree view showing all the accounts
        if company.opening_move_posted():
            return 'account.action_account_form'

        # Otherwise, we create the opening move
        company.create_op_move_if_non_existant()

        # Then, we open will open a custom tree view allowing to edit opening balances of the account
        view_id = self.env.ref('metroerp_onboarding.init_accounts_tree_custom_popup').id
        # Hide the current year earnings account as it is automatically computed
        domain = [('user_type_id', '!=', self.env.ref('account.data_unaffected_earnings').id), ('company_id','=', company.id)]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Chart of Accounts'),
            'res_model': 'account.account',
            'view_mode': 'tree',
            'limit': 99999999,
            'target': 'new',
            'search_view_id': self.env.ref('account.view_account_search').id,
            'views': [[view_id, 'list']],
            'domain': domain,
        }

    def action_skip_onboarding_sale_tax(self):
        """ Set the onboarding step as done """
        self.set_onboarding_step_done('account_onboarding_sale_tax_state')

    def action_skip_onboarding_company_data(self):
        self.set_onboarding_step_done('base_onboarding_company_state')

    def action_save_onboarding_company_step(self):
        self.set_onboarding_step_done('base_onboarding_company_state')
        default_values_terms = self.env['res.config.settings'].default_get(
            list(self.env['res.config.settings'].fields_get()))
        default_values_terms.update({'sales_invoice_tc': self.invoice_terms})
        self.env['res.config.settings'].create(default_values_terms).execute()


    def get_account_dashboard_onboarding_steps_states_names(self):
        """ Necessary to add/edit steps from other modules (account_winbooks_import in this case). """
        return [
            'account_setup_bill_state',
            'account_setup_bank_data_state',
            'account_setup_fy_data_state',
            'account_setup_coa_state',
            'account_onboarding_sale_tax_state',
            'base_onboarding_company_state',
            'account_setup_custom_invoice_layout'
        ]

    def get_and_update_sale_quotation_onboarding_state(self):
        """ This method is called on the controller rendering method and ensures that the animations
            are displayed only one time. """
        steps = [
            'sale_onboarding_sample_quotation_state',
            'sale_onboarding_tc_state',
            'account_onboarding_delivery_layout_state',
            'sale_onboarding_product_state',
            'sale_onboarding_partner_state',
            'sale_onboarding_quotation_layout_state'
        ]
        return self.get_and_update_onbarding_state('sale_quotation_onboarding_state', steps)

    @api.model
    def action_open_custom_quotation_layout(self):
        """ Called by the 'Bank Accounts' button of the setup bar."""
        view_id = self.env.ref('metroerp_onboarding.ks_report_configuration_form_custom_popup').id
        sale_ks_report_id = self.env.ref('sale.action_report_saleorder').id
        sale_ks_model_id = self.env.ref('sale.model_sale_order').id
        sale_report_style_id = self.env.ref('ks_custom_report_layouts.ks_sale_styles_1').id
        record_id = self.env['ks.report.configuration'].search([('ks_report_id', '=', sale_ks_report_id), ('company_id', '=', self.env.company.id), ('name', '=', 'Sales')])
        return {'type': 'ir.actions.act_window',
                'name': _('Sales Layout'),
                'res_model': 'ks.report.configuration',
                'target': 'new',
                'view_mode': 'form',
                'res_id': record_id.id,
                'views': [[view_id, 'form']],
                'context': {'default_ks_report_id': sale_ks_report_id, 'default_ks_model_id': sale_ks_model_id, 'default_name': 'Sales', 'default_sale_report_style_id':sale_report_style_id},
                }

    @api.model
    def action_open_custom_delivery_layout(self):
        """ Called by the 'Bank Accounts' button of the setup bar."""
        view_id = self.env.ref('metroerp_onboarding.ks_report_configuration_form_custom_popup').id
        delivery_ks_report_id = self.env.ref('stock.action_report_delivery').id
        delivery_ks_model_id = self.env.ref('stock.model_stock_picking').id
        delivery_report_style_id = self.env.ref('ks_custom_report_layouts.ks_sale_styles_11').id
        record_id = self.env['ks.report.configuration'].search([('ks_report_id', '=', delivery_ks_report_id), ('company_id', '=', self.env.company.id), ('name', '=', 'Delivery Note')])
        return {'type': 'ir.actions.act_window',
                'name': _('Delivery Layout'),
                'res_model': 'ks.report.configuration',
                'target': 'new',
                'view_mode': 'form',
                'res_id': record_id.id,
                'views': [[view_id, 'form']],
                'context': {'default_ks_report_id': delivery_ks_report_id, 'default_ks_model_id': delivery_ks_model_id, 'default_name': 'Delivery', 'default_sale_report_style_id':delivery_report_style_id},
                }

    @api.model
    def action_open_custom_product_popup(self):
        """ Onboarding step for company basic information. """
        view_id = self.env.ref('metroerp_onboarding.product_template_form_view_custom_popup').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create your first product'),
            'res_model': 'product.template',
            'view_mode': 'form',
            'target': 'new',
            'views': [[view_id, 'form']]
        }

    @api.model
    def action_open_custom_partner_popup(self):
        """ Onboarding step for company basic information. """
        view_id = self.env.ref('metroerp_onboarding.view_partner_form_custom_popup').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create your first customer'),
            'res_model': 'res.partner',
            'view_mode': 'form',
            'target': 'new',
            'views': [[view_id, 'form']]
        }

    # def _get_sample_sales_order(self):
    #     """ Get a sample quotation or create one if it does not exist. """
    #     # use current user as partner
    #     partner = self.env['res.partner'].sudo().search([], order='create_date desc', limit=1) or self.env.user.partner_id
    #     company_id = self.env.company.id
    #     public_pricelist = self.env['product.pricelist'].search([('company_id', '=', self.env.company.id)], limit=1)
    #     # is there already one?
    #     sample_sales_order = self.env['sale.order'].search(
    #         [('company_id', '=', company_id), ('partner_id', '=', partner.id),
    #          ('state', '=', 'draft')], limit=1)
    #     if len(sample_sales_order) == 0:
    #         sample_sales_order = self.env['sale.order'].create({
    #             'partner_id': partner.id,
    #             'pricelist_id': public_pricelist.id
    #         })
    #         # take any existing product or create one
    #         product = self.env['product.product'].sudo().search([('sale_ok', '=', True), ('categ_id.company_id', '=', self.env.company.id)], order='create_date desc', limit=1) or self.env['product.product'].search([], limit=1)
    #         if len(product) == 0:
    #             default_image_path = get_module_resource('product', 'static/img', 'product_product_13-image.png')
    #             product = self.env['product.product'].create({
    #                 'name': _('Sample Product'),
    #                 'active': False,
    #                 'image_1920': base64.b64encode(open(default_image_path, 'rb').read())
    #             })
    #             product.product_tmpl_id.write({'active': False})
    #         self.env['sale.order.line'].create({
    #             'name': _('Sample Order Line'),
    #             'product_id': product.id,
    #             'product_uom_qty': 10,
    #             'price_unit': 123,
    #             'order_id': sample_sales_order.id,
    #             'company_id': sample_sales_order.company_id.id,
    #         })
    #     return sample_sales_order

    @api.model
    def action_open_sale_onboarding_sample_quotation(self):
        """ Onboarding step for sending a sample quotation. Open a window to compose an email,
            with the edi_invoice_template message loaded by default. """
        # sample_sales_order = self._get_sample_sales_order()
        # template = self.env.ref('sale.email_template_edi_sale', False)
        #
        # message_composer = self.env['mail.compose.message'].with_context(
        #     default_use_template=bool(template),
        #     mark_so_as_sent=True,
        #     custom_layout='mail.mail_notification_paynow',
        #     proforma=self.env.context.get('proforma', False),
        #     force_email=True, mail_notify_author=True
        # ).create({
        #     'res_id': sample_sales_order.id,
        #     'template_id': template and template.id or False,
        #     'model': 'sale.order',
        #     'composition_mode': 'comment'})
        #
        # # Simulate the onchange (like trigger in form the view)
        # update_values = message_composer.onchange_template_id(template.id, 'comment', 'sale.order', sample_sales_order.id)['value']
        # message_composer.write(update_values)
        #
        # message_composer.send_mail()

        self.set_onboarding_step_done('sale_onboarding_sample_quotation_state')

        self.action_close_sale_quotation_onboarding()

        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action.update({
            'views': [[self.env.ref('sale.view_order_form').id, 'form']],
            'view_mode': 'form',
            'target': 'main',
        })
        return action

    @api.model
    def setting_init_bank_account_action(self):
        """ Called by the 'Bank Accounts' button of the setup bar."""
        view_id = self.env.ref('metroerp_onboarding.setup_bank_account_wizard_custom').id
        return {'type': 'ir.actions.act_window',
                'name': _('Create a Bank Account'),
                'res_model': 'account.setup.bank.manual.config',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
        }


    def get_and_update_purchase_onboarding_state(self):
        """ This method is called on the controller rendering method and ensures that the animations
            are displayed only one time. """
        steps = ['purchase_onboarding_tc_state',
                 'purchase_onboarding_rfq_layout_state',
                 'purchase_onboarding_po_layout_state',
                 "purchase_onboarding_bill_state",
                 'purchase_onboarding_partner_state',
                 'purchase_onboarding_sample_order_state'

        ]
        return self.get_and_update_onbarding_state('purchase_onboarding_state', steps)


    @api.model
    def action_close_purchase_dashboard_onboarding(self):
        """ Mark the dashboard onboarding panel as closed. """
        self.env.company.purchase_dashboard_onboarding_state = 'closed'

    @api.model
    def action_open_custom_purchase_tc(self):
        """ Called by the 'Bank Accounts' button of the setup bar."""
        view_id = self.env.ref('metroerp_onboarding.purchase_custom_tc_wizard').id
        return {'type': 'ir.actions.act_window',
                'name': _('Purchase Terms and Conditions'),
                'res_model': 'purchase.terms.conditions',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
        }

    @api.model
    def action_open_custom_rfq_layout(self):
        """ Called by the 'Bank Accounts' button of the setup bar."""
        view_id = self.env.ref('metroerp_onboarding.ks_report_configuration_form_custom_popup').id
        purchase_ks_report_id = self.env.ref('purchase.report_purchase_quotation').id
        purchase_ks_model_id = self.env.ref('purchase.model_purchase_order').id
        purchase_report_style_id = self.env.ref('ks_custom_report_layouts.ks_sale_styles_1').id
        record_id = self.env['ks.report.configuration'].search([('ks_report_id', '=', purchase_ks_report_id), ('company_id', '=', self.env.company.id), ('name', '=', 'Purchase RFQ')])
        return {'type': 'ir.actions.act_window',
                'name': _('RFQ Layout'),
                'res_model': 'ks.report.configuration',
                'target': 'new',
                'view_mode': 'form',
                'res_id': record_id.id,
                'views': [[view_id, 'form']],
                'context': {'default_ks_report_id': purchase_ks_report_id, 'default_ks_model_id': purchase_ks_model_id, 'default_name': 'Purchase RFQ', 'default_sale_report_style_id':purchase_report_style_id},
                }

    @api.model
    def action_open_custom_po_layout(self):
        """ Called by the 'Bank Accounts' button of the setup bar."""
        view_id = self.env.ref('metroerp_onboarding.ks_report_configuration_form_custom_popup').id
        purchase_order_ks_report_id = self.env.ref('purchase.action_report_purchase_order').id
        purchase_order_ks_model_id = self.env.ref('purchase.model_purchase_order').id
        purchase_order_report_style_id = self.env.ref('ks_custom_report_layouts.ks_sale_styles_1').id
        record_id = self.env['ks.report.configuration'].search([('ks_report_id', '=', purchase_order_ks_report_id), ('company_id', '=', self.env.company.id), ('name', '=', 'Purchase Order')])
        return {'type': 'ir.actions.act_window',
                'name': _('Purchase Order Layout'),
                'res_model': 'ks.report.configuration',
                'target': 'new',
                'view_mode': 'form',
                'res_id': record_id.id,
                'views': [[view_id, 'form']],
                'context': {'default_ks_report_id': purchase_order_ks_report_id, 'default_ks_model_id': purchase_order_ks_model_id, 'default_name': 'Purchase RFQ', 'default_sale_report_style_id':purchase_order_report_style_id},
                }


    @api.model
    def action_open_custom_bill_popup_purchase(self):
        """ Onboarding step for company basic information. """
        view_id = self.env.ref('metroerp_onboarding.ks_report_configuration_form_custom_popup').id
        purchase_bill_ks_report_id = self.env.ref('account.account_invoices').id
        purchase_bill_ks_model_id = self.env.ref('account.model_account_move').id
        purchase_bill_report_style_id = self.env.ref('ks_custom_report_layouts.ks_sale_styles_1').id
        record_id = self.env['ks.report.configuration'].search(
            [('ks_report_id', '=', purchase_bill_ks_report_id), ('company_id', '=', self.env.company.id),
             ('name', '=', 'Bill')])
        return {'type': 'ir.actions.act_window',
                'name': _('Bill Layout'),
                'res_model': 'ks.report.configuration',
                'target': 'new',
                'view_mode': 'form',
                'res_id': record_id.id,
                'views': [[view_id, 'form']],
                'context': {'default_ks_report_id': purchase_bill_ks_report_id,
                            'default_ks_model_id': purchase_bill_ks_model_id, 'default_name': 'Bill',
                            'default_sale_report_style_id': purchase_bill_report_style_id},
                }

    @api.model
    def action_open_custom_partner_popup_purchase(self):
        """ Onboarding step for company basic information. """
        view_id = self.env.ref('metroerp_onboarding.view_partner_form_custom_popup').id
        ctx = dict(self._context or {})
        ctx.update({'from_purchase_partner_popup': True})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create your first vendor for RFQ'),
            'res_model': 'res.partner',
            'view_mode': 'form',
            'target': 'new',
            'views': [[view_id, 'form']],
            'context': ctx
        }

    # def _get_sample_purchase_order(self):
    #     """ Get a sample quotation or create one if it does not exist. """
    #     # use current user as partner
    #     partner = self.env.user.partner_id
    #     company_id = self.env.company.id
    #
    #     # is there already one?
    #     sample_purchase_order = self.env['purchase.order'].search(
    #         [('company_id', '=', company_id), ('partner_id', '=', partner.id),
    #          ('state', '=', 'draft')], limit=1)
    #     if len(sample_purchase_order) == 0:
    #         sample_purchase_order = self.env['purchase.order'].create({
    #             'partner_id': partner.id
    #         })
    #         # take any existing product or create one
    #         product = self.env['product.product'].search([('categ_id.company_id', '=', self.env.company.id)], limit=1)
    #         if len(product) == 0:
    #             default_image_path = get_module_resource('product', 'static/img', 'product_product_13-image.png')
    #             product = self.env['product.product'].create({
    #                 'name': _('Sample Product'),
    #                 'active': False,
    #                 'image_1920': base64.b64encode(open(default_image_path, 'rb').read())
    #             })
    #             product.product_tmpl_id.write({'active': False})
    #         self.env['purchase.order.line'].create({
    #             'name': _('Sample Order Line'),
    #             'product_id': product.id,
    #             'product_qty': 10,
    #             'price_unit': 123,
    #             'order_id': sample_purchase_order.id,
    #             'company_id': sample_purchase_order.company_id.id,
    #         })
    #     return sample_purchase_order

    @api.model
    def action_open_purchase_onboarding_sample_quotation(self):
        """ Onboarding step for sending a sample quotation. Open a window to compose an email,
            with the edi_invoice_template message loaded by default. """
        #sample_purchase_order = self._get_sample_purchase_order()

        self.set_onboarding_step_done('purchase_onboarding_sample_order_state')
        self.env.company.purchase_dashboard_onboarding_state = 'closed'
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.purchase_rfq")
        action.update({
            'views': [[self.env.ref('purchase.purchase_order_form').id, 'form']],
            'view_mode': 'form',
            'target': 'main',
        })
        return action

