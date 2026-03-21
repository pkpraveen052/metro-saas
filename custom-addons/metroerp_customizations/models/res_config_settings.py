# -*- coding: utf-8 -*-
import base64, os
from odoo import fields, models, api, tools, _
import logging
from lxml import etree
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime


_logger = logging.getLogger(__name__)


class IrDefault(models.Model):
    _inherit = 'ir.default'

    @api.model
    def set_wk_favicon(self, model, field):
        script_dir = os.path.dirname(__file__)
        rel_path = "../static/src/img/favicon.png"
        abs_file_path = os.path.join(script_dir, rel_path)
        with open(abs_file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
            self.set('res.config.settings', 'wk_favicon', encoded_string.decode("utf-8"))


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auth_signup_uninvited = fields.Selection([
        ('b2b', 'On invitation'),
        ('b2c', 'Free sign up'),
    ], string='Customer Account', default='b2b', config_parameter='auth_signup.invitation_scope')
    module_partner_autocomplete = fields.Boolean("Partner Autocomplete", default=False)

    wk_favicon = fields.Binary(string="Favicon Image")
    title_brand = fields.Char(string="Title Brand")
    odoo_text_replacement = fields.Char(string='Replace Text "Odoo" With?')
    favicon_url = fields.Char(string="Url")
    attach_id = fields.Integer(string="Favicon Attach ID")
    # Base fields overidden to add the groups
    recaptcha_public_key = fields.Char("Site Key", config_parameter='recaptcha_public_key', groups='base.group_system,metroerp_customizations.sub_admin_group')
    recaptcha_private_key = fields.Char("Secret Key", config_parameter='recaptcha_private_key', groups='base.group_system,metroerp_customizations.sub_admin_group')
    recaptcha_min_score = fields.Float("Minimum score", config_parameter='recaptcha_min_score', groups='base.group_system,metroerp_customizations.sub_admin_group', default="0.5", help="Should be between 0.0 and 1.0")

    sales_tc = fields.Text(related='company_id.sales_tc', readonly=False)
    use_sales_tc = fields.Boolean(string='Sales Quotation Terms & Conditions', related='company_id.use_sales_tc', readonly=False)
    
    sales_invoice_tc = fields.Text(related='company_id.sales_invoice_tc', readonly=False)
    use_sales_invoice_tc = fields.Boolean(string='Sales Invoice Terms & Conditions', related='company_id.use_sales_invoice_tc', readonly=False)

    purchase_tc = fields.Text(related='company_id.purchase_tc', readonly=False)
    use_purchase_tc = fields.Boolean(string='Purchase Quotation Terms & Conditions', related='company_id.use_purchase_tc', readonly=False)
    
    purchase_invoice_tc = fields.Text(related='company_id.purchase_invoice_tc', readonly=False)
    use_purchase_invoice_tc = fields.Boolean(string='Purchase Invoice Terms & Conditions', related='company_id.use_purchase_invoice_tc', readonly=False)
    
    use_delivery_tc = fields.Boolean(string='Sales Delivery Terms & Conditions', related='company_id.use_delivery_tc', readonly=False)
    deliver_tc = fields.Text(related='company_id.deliver_tc', readonly=False)

    sale_order_line_record_limit = fields.Integer(string="Record Limit", default=10,
                                                  config_parameter='sale_order_line_record_limit')
    sale_order_status = fields.Selection([('sale', 'Confirm order'), ('done', 'Done (Locked)'), ('both', 'Both')],
                                         string="Price History Based On", default="sale",
                                         config_parameter='sale_order_status')
    purchase_order_line_record_limit = fields.Integer(string="Record Limit", default=10,
                                                      config_parameter='purchase_order_line_record_limit')
    purchase_order_status = fields.Selection(
        [('purchase', 'Purchase order'), ('done', 'Done (Locked)'), ('both', 'Both')], string="Price History Based On",
        default="purchase", config_parameter='purchase_order_status')

    active_user_count = fields.Integer('Number of Active Users', compute="_compute_active_user_count")
    company_count = fields.Integer('Number of Companies', compute="_compute_company_count")
    chart_of_accounts_installed = fields.Boolean(related="company_id.chart_of_accounts_installed", string="Chart of Accounts Installed")
    group_product_variant = fields.Boolean("Variants", implied_group='product.group_product_variant', default=True)
    module_sale_product_configurator = fields.Boolean("Product Configurator", default=True)
    module_sale_product_matrix = fields.Boolean("Sales Grid Entry", default=True)
    group_uom = fields.Boolean("Units of Measure", related="company_id.group_uom", readonly=False)
    group_discount_per_so_line = fields.Boolean('Discount', related="company_id.group_discount_per_so_line", readonly=False)

    group_sale_order_template = fields.Boolean("Quotation Templates", related="company_id.group_sale_order_template",
                                               readonly=False)
    group_sale_delivery_address = fields.Boolean("Customer Addresses", related="company_id.group_sale_delivery_address",
                                                 readonly=False)
    use_quotation_validity_days = fields.Boolean("Default Quotation Validity",
                                                 related="company_id.use_quotation_validity_days", readonly=False)
    group_warning_sale = fields.Boolean("Sale Order Warnings", related="company_id.group_warning_sale", readonly=False)
    group_auto_done_setting = fields.Boolean("Lock Confirmed Sales", related="company_id.group_auto_done_setting",
                                             readonly=False)
    group_proforma_sales = fields.Boolean(string="Pro-Forma Invoice", related="company_id.group_proforma_sales",
                                          help="Allows you to send pro-forma invoice.", readonly=False)
    group_display_incoterm = fields.Boolean("Incoterms", related="company_id.group_proforma_sales", readonly=False)
    automatic_invoice = fields.Boolean("Automatic Invoice", related="company_id.automatic_invoice", readonly=False,
                                       help="The invoice is generated automatically and available in the customer portal "
                                            "when the transaction is confirmed by the payment acquirer.\n"
                                            "The invoice is marked as paid and the payment is registered in the payment journal "
                                            "defined in the configuration of the payment acquirer.\n"
                                            "This mode is advised if you issue the final invoice at the order and not after the delivery.")
    group_show_purchase_receipts = fields.Boolean(string='Purchase Receipt', related="company_id.group_show_purchase_receipts",
                                                    readonly=False)
    group_show_sale_receipts = fields.Boolean(string='Sale Receipt', related="company_id.group_show_sale_receipts",
                                                    readonly=False)
    group_warning_account = fields.Boolean(string="Warnings in Invoices", related="company_id.group_warning_account",
                                                    readonly=False)
    group_cash_rounding = fields.Boolean(string="Cash Rounding", related="company_id.group_cash_rounding",
                                                    readonly=False)
    group_analytic_accounting = fields.Boolean(string='Analytic Accounting',
        related="company_id.group_analytic_accounting", readonly=False)
    group_analytic_tags = fields.Boolean(string='Analytic Tags', related="company_id.group_analytic_tags", readonly=False)
    module_delivery = fields.Boolean("Delivery Methods", default=True)


    # inventory field settings
    group_warning_stock = fields.Boolean("Warnings for Stock", related="company_id.group_warning_stock", readonly=False)
    module_delivery = fields.Boolean("Delivery Methods", default=True)
    group_stock_sign_delivery = fields.Boolean("Signature", related="company_id.group_stock_sign_delivery", readonly=False)
    group_stock_tracking_lot = fields.Boolean("Packages", related="company_id.group_stock_tracking_lot", readonly=False)
    group_stock_tracking_owner = fields.Boolean("Consignment", related="company_id.group_stock_tracking_owner", readonly=False)
    group_lot_on_delivery_slip = fields.Boolean("Display Lots & Serial Numbers on Delivery Slips",
                                                group="base.group_user,base.group_portal",
                                                related="company_id.group_stock_tracking_owner", readonly=False)
    group_lot_on_invoice = fields.Boolean("Display Lots & Serial Numbers on Invoices",
                                          related="company_id.group_lot_on_invoice", readonly=False)
    module_product_expiry = fields.Boolean("Expiration Dates", default=True,
                                           help="Track following dates on lots & serial numbers: best before, removal, end of life, alert. \n Such dates are set automatically at lot/serial number creation based on values set on the product (in days).")
    group_expiry_date_on_delivery_slip = fields.Boolean("Display Expiration Dates on Delivery Slips",
                                                        related="company_id.group_expiry_date_on_delivery_slip",
                                                        readonly=False)
    group_stock_production_lot = fields.Boolean("Lots & Serial Numbers",
                                                related="company_id.group_stock_production_lot",
                                                readonly=False,)
    group_stock_multi_locations = fields.Boolean('Storage Locations', related="company_id.group_stock_multi_locations",
                                                 readonly=False,
                                                 help="Store products in specific locations of your warehouse (e.g. bins, racks) and to track inventory accordingly.")
    group_stock_adv_location = fields.Boolean("Multi-Step Routes", related="company_id.group_stock_adv_location",
                                              readonly=False,
                                              help="Add and customize route operations to process product moves in your warehouse(s): e.g. unload > quality control > stock for incoming products, pick > pack > ship for outgoing products. \n You can also set putaway strategies on warehouse locations in order to send incoming products into specific child locations straight away (e.g. specific bins, racks).")
    

    module_stock_picking_batch = fields.Boolean("Batch Pickings", related="company_id.module_stock_picking_batch", readonly=False)

    module_stock_landed_costs = fields.Boolean("Landed Costs", related="company_id.module_stock_landed_costs", readonly=False,
                                               help="Affect landed costs on reception operations and split them among products to update their cost price.")
    use_security_lead = fields.Boolean(string="Security Lead Time for Sales",
                                       related="company_id.use_security_lead",
                                       readonly=False,
                                       help="Margin of error for dates promised to customers. Products will be scheduled for delivery that many days earlier than the actual promised date, to cope with unexpected delays in the supply chain.")
    use_po_lead = fields.Boolean(string="Security Lead Time for Purchase",
                                 related="company_id.use_po_lead",
                                 readonly=False,
        help="Margin of error for vendor lead times. When the system generates Purchase Orders for reordering products,they will be scheduled that many days earlier to cope with unexpected vendor delays.")
    delivery_product_description = fields.Boolean(related='company_id.delivery_product_description', readonly=False)
    group_stock_sign_delivery = fields.Boolean("Customer Signature", related="company_id.group_stock_sign_delivery", readonly=False)

    order_date_same_as_quotation_date = fields.Boolean(related='company_id.order_date_same_as_quotation_date', string='Order date same as Quotation Date', readonly=False)
    confirmation_date_same_as_order_deadline = fields.Boolean(related='company_id.confirmation_date_same_as_order_deadline', string='Confirmation date same as Order Deadline', readonly=False)
    quotation_auto_sent = fields.Boolean(related='company_id.quotation_auto_sent',readonly=False)
    ks_enable_currency_symbol_on_dynamic_report = fields.Boolean(related="company_id.ks_enable_currency_symbol_on_dynamic_report", string="Currency Symbol On Dynamic Report", readonly=False)
    display_customer_name_on_tax_report = fields.Boolean(related="company_id.display_customer_name_on_tax_report", string="Display Customer/Vendor Name On Tax Report", readonly=False)
    auto_currency_rate = fields.Boolean(
        related='company_id.auto_currency_rate',
        readonly=False
    )

    currency_rate_service = fields.Selection(
        related='company_id.currency_rate_service',
        readonly=False
    )
    merge_bank_accounts = fields.Boolean('Merge Bank & Cash Accounts in BS', related='company_id.merge_bank_accounts', readonly=False)


    def install_chart_of_account(self):
        if self.env.company == self.company_id and self.chart_template_id:
            # Load the chart of accounts
            self.chart_template_id._load(15.0, 15.0, self.env.company)
            self.company_id.chart_of_accounts_installed = True

            # Ensure tax template values are assigned properly
            for tax_template in self.chart_template_id.tax_template_ids:
                if tax_template:
                    # Find the corresponding account.tax record
                    tax = self.env['account.tax'].search([
                        ('company_id', '=', self.env.company.id),
                        ('name', '=', tax_template.name),  # Matching by name (assuming unique names)
                        ('amount', '=', tax_template.amount),  # Ensuring correct tax rate
                        ('type_tax_use', '=', tax_template.type_tax_use),
                    ], limit=1)

                    if tax:
                        tax.write({
                            'for_IRAS': tax_template.for_IRAS,
                            'iras_supplies_type': tax_template.iras_supplies_type,
                        })


    @api.depends('company_id')
    def _compute_company_count(self):
        company_count = self.env['res.company'].search_count([])
        for record in self:
            record.company_count = company_count

    @api.depends('company_id')
    def _compute_active_user_count(self):
        active_user_count = self.env['res.users'].search_count([('share', '=', False)])
        for record in self:
            record.active_user_count = active_user_count

    @api.model
    def fields_view_get(
            self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):
        ret_val = super().fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )

        page_name = ret_val["name"]
        if not page_name == "res.config.settings.view.form":
            return ret_val

        doc = etree.XML(ret_val["arch"])

        query = "//div[div[field[@widget='upgrade_boolean']]]"
        for item in doc.xpath(query):
            item.attrib["class"] = "d-none"

        ret_val["arch"] = etree.tostring(doc)
        return ret_val

    # override setting onchange_module method
    def onchange_module(self, field_value, module_name):
        ModuleSudo = self.env['ir.module.module'].sudo()
        modules = ModuleSudo.search(
            [('name', '=', module_name.replace("module_", '')),
            ('state', 'in', ['to install', 'installed', 'to upgrade'])])
        module_list = ['module_stock_picking_batch', 'module_stock_landed_costs']
        if module_name not in module_list:
            if modules and not int(field_value):
                deps = modules.sudo().downstream_dependencies()
                dep_names = (deps | modules).mapped('shortdesc')
                message = '\n'.join(dep_names)
                return {
                    'warning': {
                        'title': _('Warning!'),
                        'message': _('Disabling this option will also uninstall the following modules \n%s', message),
                    }
                }
        return {}

    # override setting _get_classified_fields method
    @api.model
    def _get_classified_fields(self):
        IrModule = self.env['ir.module.module']
        Groups = self.env['res.groups']
        ref = self.env.ref
        defaults, groups, modules, configs, others = [], [], [], [], []
        group_list = ['group_uom','group_discount_per_so_line','group_sale_order_template', 'group_sale_delivery_address',
                      'group_warning_sale', 'group_auto_done_setting', 'group_proforma_sales', 'group_display_incoterm',
                      'group_show_purchase_receipts', 'group_show_sale_receipts', 'group_warning_account', 'group_cash_rounding', 
                      'group_analytic_accounting', 'group_analytic_tags','group_warning_stock', 'group_stock_sign_delivery', 'group_stock_tracking_lot',
                      'group_stock_tracking_owner', 'group_lot_on_delivery_slip', 'group_lot_on_invoice',
                      'group_expiry_date_on_delivery_slip', 'group_stock_production_lot', 'group_stock_multi_locations',
                      'group_stock_adv_location',]
        config_list = ['use_quotation_validity_days', 'automatic_invoice', 'use_security_lead', 'use_po_lead']
        module_list = ['module_sale_product_configurator', 'module_sale_product_matrix', 'module_stock_picking_batch', 'module_stock_landed_costs']
        for name, field in self._fields.items():
            if name.startswith('default_'):
                if not hasattr(field, 'default_model'):
                    raise Exception("Field %s without attribute 'default_model'" % field)
                defaults.append((name, field.default_model, name[8:]))
            elif name.startswith('group_'):
                if field.type not in ('boolean', 'selection'):
                    raise Exception("Field %s must have type 'boolean' or 'selection'" % field)
                if not hasattr(field, 'implied_group'):
                    raise Exception("Field %s without attribute 'implied_group'" % field)
                field_group_xmlids = getattr(field, 'group', 'base.group_user').split(',')
                field_groups = Groups.concat(*(ref(it) for it in field_group_xmlids))
                if name not in group_list:
                    groups.append((name, field_groups, ref(field.implied_group)))
            elif name.startswith('module_'):
                if field.type not in ('boolean', 'selection'):
                    raise Exception("Field %s must have type 'boolean' or 'selection'" % field)
                module = IrModule.sudo().search([('name', '=', name[7:])], limit=1)
                if name not in module_list:
                    modules.append((name, module))
            elif hasattr(field, 'config_parameter'):
                if field.type not in ('boolean', 'integer', 'float', 'char', 'selection', 'many2one'):
                    raise Exception(
                        "Field %s must have type 'boolean', 'integer', 'float', 'char', 'selection' or 'many2one'" % field)
                if name not in config_list:
                    configs.append((name, field.config_parameter))
            else:
                others.append(name)

        return {'default': defaults, 'group': groups, 'module': modules, 'config': configs, 'other': others}

    def execute(self):
        """
        Called when settings are saved.

        This method will call `set_values` and will install/uninstall any modules defined by
        `module_` Boolean fields and then trigger a web client reload.

        .. warning::

            This method **SHOULD NOT** be overridden, in most cases what you want to override is
            `~set_values()` since `~execute()` does little more than simply call `~set_values()`.

            The part that installs/uninstalls modules **MUST ALWAYS** be at the end of the
            transaction, otherwise there's a big risk of registry <-> database desynchronisation.
        """
       
        self.ensure_one()
        if not self.env.is_admin():
            raise AccessError(_("Only administrators can change the settings"))

        self = self.with_context(active_test=False)
        classified = self._get_classified_fields()

        self.set_values()

        # module fields: install/uninstall the selected modules
        to_install = []
        to_uninstall_modules = self.env['ir.module.module']
        module_list = ['module_stock_picking_batch', 'module_stock_landed_costs']
        lm = len('module_')
        for name, module in classified['module']:
            if int(self[name]):
                to_install.append((name[lm:], module))
            else:
                if module and module.state in ('installed', 'to upgrade'):
                    if name not in module_list:
                        to_uninstall_modules += module

        if to_install or to_uninstall_modules:
            self.flush()

        if to_uninstall_modules:
            to_uninstall_modules.button_immediate_uninstall()

        installation_status = self._install_modules(to_install)
        
        """Custom Code start """
        """Here we are overridingg the for erp_admin groups for (recaptcha_public_key,recaptcha_private_key,recaptcha_min_score)
           when we make reCAPTCHA: Easy on Humans, Hard on Bots is True  and Save then google_recaptcha module will install,
           when we make reCAPTCHA: Easy on Humans, Hard on Bots is False and Save then google_recaptcha module will install
           when we install the google_recaptcha module autoatically metroerp_customizations will upgrade then erp_admin will see 
           (recaptcha_public_key,recaptcha_private_key,recaptcha_min_score) fields. 
           """
        for x,y in to_install:
            if str(x) == 'google_recaptcha':
                to_upgrade_modules = self.env['ir.module.module'].search([('name','=','metroerp_customizations')])
                to_upgrade_modules.button_immediate_upgrade()
        """Custom Code END"""

        if installation_status or to_uninstall_modules:
            # After the uninstall/install calls, the registry and environments
            # are no longer valid. So we reset the environment.
            self.env.reset()
            self = self.env()[self._name]

        # pylint: disable=next-method-called
        config = self.env['res.config'].next() or {}
        if config.get('type') not in ('ir.actions.act_window_close',):
            return config

        # force client-side reload (update user menu and current view)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    @api.model
    def _update_digest_settings(self):
        """While Upgrading Metrogroup customization module Updating the digest email name and State values"""
        digest = self.env['digest.digest'].sudo().search([])
        if digest :
            for record in digest:
                if "Odoo" in record.name:
                    new_name = (record.name).replace("Odoo", "ERP")
                    record.write({'name':new_name,'state':'deactivated'})
        return True

    @api.model
    def get_debranding_settings(self):
        IrDefault = self.env['ir.default'].sudo()
        wk_favicon = IrDefault.get('res.config.settings', "wk_favicon")
        title_brand = IrDefault.get('res.config.settings', "title_brand")
        odoo_text_replacement = IrDefault.get('res.config.settings', "odoo_text_replacement")
        favicon_url = IrDefault.get('res.config.settings', "favicon_url")
        attach_id = IrDefault.get('res.config.settings', "attach_id")
        return {
            'wk_favicon': wk_favicon,
            'attach_id': attach_id,
            'title_brand': title_brand,
            'odoo_text_replacement': odoo_text_replacement,
            'favicon_url': favicon_url,
        }

    # @api.onchange('group_stock_multi_locations')
    # def onchange_group_stock_multy_locations(self):
    #     now = datetime.now()
    #     print('\n\n\nself.env.company', self.env.company)
    #     if not self.env.company.group_stock_multi_locations:
    #         group_stock_multi_warehouses = self.env.ref('stock.group_stock_multi_warehouses')
    #         group_stock_multi_warehouses.write({'users': [(3, self.env.user.id)]})
    #         print('\n\n\n\nmethod statrt', now.strftime('%M:%S'))
        # group_user = self.env.ref('base.group_user')
        # group_stock_multi_warehouses = self.env.ref('stock.group_stock_multi_warehouses')
        # location_grp = self.env.ref('stock.group_stock_multi_locations')
        # if location_grp in group_user.implied_ids and group_stock_multi_warehouses in group_user.implied_ids:
        #     group_user.write({'implied_ids': [(3, group_stock_multi_warehouses.id), (3, location_grp.id)]})
        #     if self.env.user.has_group('stock.group_stock_multi_warehouses'):
        #         group_stock_multi_warehouses.write({'users': [(3, self.env.user.id)]})
        # # check multi ware house on company
        # """
        # base multi warehouse on company user group active and deactive
        # """
        # cnt_by_company = self.env['stock.warehouse'].sudo().search(
        #     [('active', '=', True), ('company_id', '=', self.env.company.id)])
        # if cnt_by_company:
        #     max_cnt = len(cnt_by_company)
        #     group_stock_multi_warehouses = self.env.ref('stock.group_stock_multi_warehouses')
        #     group_stock_multi_locations = self.env.ref('stock.group_stock_multi_locations')
        #     if max_cnt <= 1 and self.env.user.has_group('stock.group_stock_multi_warehouses'):
        #         group_stock_multi_warehouses.write({'users': [(3, self.env.user.id)]})
        #         self.env.company.write({'group_stock_multi_locations': False})
        #     if max_cnt > 1 and (not self.env.user.has_group('stock.group_stock_multi_warehouses')):
        #         group_stock_multi_warehouses.write({'users': [(4, self.env.user.id)]})
        #         group_stock_multi_locations.write({'users': [(4, self.env.user.id)]})
        #         self.env.company.write({'group_stock_multi_locations': True})
        #     if max_cnt > 1:
        #         group_stock_multi_warehouses.write({'users': [(4, self.env.user.id)]})
        #         group_stock_multi_locations.write({'users': [(4, self.env.user.id)]})
        #         self.env.company.write({'group_stock_multi_locations': True})
        # print('\n\n\n\nmethod end', now.strftime('%M:%S'))


        # elif (not location_grp in group_user.implied_ids) and (not group_stock_multi_warehouses in group_user.implied_ids) and not self.group_stock_multi_locations:
        #     group_stock_multi_warehouses.write({'users': [(3, self.env.user.id)]})
        #     location_grp.write({'users': [(3, self.env.user.id)]})

    def write(self, vals):
        """this method to check multiple warehouse with location try to uncheck raise validation"""
        res = super(ResConfigSettings, self).write(vals)
        warehouse_grp = self.env.user.has_group('stock.group_stock_multi_warehouses')
        location_grp = self.env.user.has_group('stock.group_stock_multi_locations')
        # check multiple warehouse
        cnt_by_company = self.env['stock.warehouse'].sudo().search(
            [('active', '=', True), ('company_id', '=', self.env.company.id)])
        if cnt_by_company:
            max_cnt = len(cnt_by_company)
        if (self.group_stock_multi_locations == False) and max_cnt > 1 and warehouse_grp and location_grp:
            raise ValidationError(
                _("You can't dectivate the multi-location if you have more than once warehouse by company"))
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if self.env.company == self.company_id and self.chart_template_id and self.chart_template_id != self.company_id.chart_template_id:
            self.chart_template_id._load(15.0, 15.0, self.env.company)
            self.company_id.chart_of_accounts_installed = True
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set('res.config.settings', "wk_favicon", self.wk_favicon.decode("utf-8"))
        IrDefault.set('res.config.settings', "title_brand", self.title_brand)
        IrDefault.set('res.config.settings', "odoo_text_replacement", self.odoo_text_replacement)
        if not self.attach_id:
            attach_id = self.env['ir.attachment'].sudo().search([('name', '=', 'Favicon')])
            if attach_id:
                attach_id.write({
                    'datas': self.wk_favicon.decode("utf-8"),
                })
            else:
                attach_id = self.env['ir.attachment'].sudo().create({
                    'name': 'Favicon',
                    'datas': self.wk_favicon.decode("utf-8"),
                    'public': True
                })
        else:
            attach_id.write({
                'datas': self.wk_favicon.decode("utf-8"),
            })
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        image_url = base_url + '/web/image/?model=ir.attachment&id=' + str(attach_id.id) + '&field=datas'
        IrDefault.set('res.config.settings', "favicon_url", image_url)
        IrDefault.set('res.config.settings', "sale_order_line_record_limit", self.sale_order_line_record_limit)
        IrDefault.set('res.config.settings', "sale_order_status", self.sale_order_status)
        IrDefault.set('res.config.settings', "purchase_order_line_record_limit", self.purchase_order_line_record_limit)
        IrDefault.set('res.config.settings', "purchase_order_status", self.purchase_order_status)

        users = self.env['res.users'].sudo().search([('company_ids','in',[self.company_id.id])])
        print('\n\n\n\n\nusers', users, len(users))
        group_ref_mapping = {
            'group_uom': 'uom.group_uom',
            'group_discount_per_so_line': 'product.group_discount_per_so_line',
            'group_sale_order_template': 'sale_management.group_sale_order_template',
            'group_sale_delivery_address': 'sale.group_delivery_invoice_address',
            'use_quotation_validity_days': 'metroerp_customizations.group_quotation_validity',
            'group_warning_sale': 'sale.group_warning_sale',
            'group_auto_done_setting': 'sale.group_auto_done_setting',
            'group_proforma_sales': 'sale.group_proforma_sales',
            'group_display_incoterm': 'sale_stock.group_display_incoterm',
            'automatic_invoice': 'metroerp_customizations.group_automatic_invoice',
            'group_show_purchase_receipts': 'account.group_purchase_receipts',
            'group_show_sale_receipts': 'account.group_sale_receipts',
            'group_warning_account': 'account.group_warning_account',
            'group_cash_rounding': 'account.group_cash_rounding',
            'group_analytic_accounting': 'analytic.group_analytic_accounting',
            'group_analytic_tags': 'analytic.group_analytic_tags',
            # Inventory groups
            'group_warning_stock': 'stock.group_warning_stock',
            'group_stock_sign_delivery': 'stock.group_stock_sign_delivery',
            'group_stock_tracking_lot': 'stock.group_tracking_lot',
            'group_stock_tracking_owner': 'stock.group_tracking_owner',
            'group_lot_on_delivery_slip': 'stock.group_lot_on_delivery_slip',
            'group_lot_on_invoice': 'sale_stock.group_lot_on_invoice',
            'group_expiry_date_on_delivery_slip': 'product_expiry.group_expiry_date_on_delivery_slip',
            'group_stock_production_lot': 'stock.group_production_lot',
            'group_stock_multi_locations': 'stock.group_stock_multi_locations',
            'group_stock_adv_location': 'stock.group_adv_location',
            'module_stock_picking_batch': 'metroerp_customizations.group_module_stock_picking_batch',
            'module_stock_landed_costs': 'metroerp_customizations.group_module_stock_landed_costs',
        }
        for user in users:
            group_ids = []
            for field, group_ref in group_ref_mapping.items():
                group_id = self.env.ref(group_ref).id
                if getattr(self, field):
                    print('\n\nfieldgetattr', field)
                    group_ids.append((4, group_id))  # Add group
                else:
                    print('\n\nfields_remove', field)
                    group_ids.append((3, group_id))  # Remove group

            # Write all groups at once
            user.sudo().write({'groups_id': group_ids})


    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrDefault = self.env['ir.default'].sudo()
        wk_favicon = IrDefault.get('res.config.settings', "wk_favicon")
        title_brand = IrDefault.get('res.config.settings', "title_brand")
        odoo_text_replacement = IrDefault.get('res.config.settings', "odoo_text_replacement")
        favicon_url = IrDefault.get('res.config.settings', 'favicon_url')
        attach_id = IrDefault.get('res.config.settings', 'attach_id')
        sale_order_line_record_limit = IrDefault.get('res.config.settings', 'sale_order_line_record_limit')
        sale_order_status = IrDefault.get('res.config.settings', 'sale_order_status')
        purchase_order_line_record_limit = IrDefault.get('res.config.settings', 'purchase_order_line_record_limit')
        purchase_order_status = IrDefault.get('res.config.settings', 'purchase_order_status')
        res.update(
            wk_favicon=wk_favicon,
            title_brand=title_brand,
            odoo_text_replacement=odoo_text_replacement,
            favicon_url=favicon_url,
            attach_id=attach_id,
            sale_order_line_record_limit=int(sale_order_line_record_limit) if sale_order_line_record_limit else 10,
            sale_order_status=sale_order_status,
            purchase_order_line_record_limit=int(purchase_order_line_record_limit) if purchase_order_line_record_limit else 10,
            purchase_order_status=purchase_order_status,
        )
        if not self.chart_template_id:
            res.update(
                chart_template_id=self.env.ref('l10n_sg.sg_chart_template').id,
            )
        return res

    @api.depends('company_id')
    def _compute_active_user_count(self):
        """ Overidden for the sake of new group 'ERP Admin'. """
        if self.env.user.has_group('metroerp_customizations.sub_admin_group') and not self.env.user.has_group(
                'base.group_erp_manager'):
            active_user_count = self.env['res.users'].sudo().search_count(
                [('share', '=', False), ('is_admin_flag', '=', False)])
            for record in self:
                record.active_user_count = active_user_count
        else:
            active_user_count = self.env['res.users'].sudo().search_count([('share', '=', False)])
            for record in self:
                record.active_user_count = active_user_count
