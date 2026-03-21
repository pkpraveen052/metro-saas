# -*- coding: utf-8 -*-


import base64
import io,re
import xlsxwriter
from odoo import api, fields, models, tools, _
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang

class ProductTemplate(models.Model):
    _inherit = "product.template"

    @tools.ormcache()
    def _get_default_category_id(self):
        # Deletion forbidden (at least through unlink)
        default_categ = self.env['product.category'].search([('name', '=', 'All'), ('company_id', '=', self.env.company.id)])
        return default_categ or True

    name = fields.Char(tracking=True)
    sale_ok = fields.Boolean(tracking=True, default=True)
    purchase_ok = fields.Boolean(tracking=True, default=True)
    type = fields.Selection(tracking=True)
    categ_id = fields.Many2one(
        'product.category', 'Product Category',
        change_default=True, default=_get_default_category_id, group_expand='_read_group_categ_id',
        required=True, help="Select category for the current product",tracking=True)
    default_code = fields.Char(tracking=True)
    barcode = fields.Char(tracking=True)
    list_price = fields.Float(tracking=True)
    standard_price = fields.Float(tracking=True)
    invoice_policy = fields.Selection(tracking=True)
    description_sale = fields.Text(tracking=True)
    available_in_pos = fields.Boolean(tracking=True)
    pos_categ_id = fields.Many2one("pos.category",tracking=True)
    purchase_method = fields.Selection(tracking=True)
    description_purchase = fields.Text(tracking=True)
    description_sale = fields.Text(tracking=True)
    description = fields.Text(tracking=True)
    uom_id = fields.Many2one('uom.uom', tracking=True)
    create_date_tmp = fields.Datetime('Creation Date', copy=False)
    company_id = fields.Many2one('res.company', 'Company', index=1, default=lambda self: self.env.company.id)
    tag_id = fields.Many2many('product.tags', string="Tags",compute='_compute_tag',inverse='_set_tag_id', search='_search_tag_id',store=True)


    @api.depends('product_variant_ids.tag_id')
    def _compute_tag(self):
        for template in self:
            # Clear existing tags
            template.tag_id = [(5, 0, 0)]
            variant_count = len(template.product_variant_ids)
            if variant_count == 1:
                # Assign the tags from the single variant
                template.tag_id = [(6, 0, template.product_variant_ids.tag_id.ids)]
            elif variant_count == 0:
                archived_variants = template.with_context(active_test=False).product_variant_ids
                if len(archived_variants) == 1:
                    # Assign the tags from the single archived variant
                    template.tag_id = [(6, 0, archived_variants.tag_id.ids)]


    def _search_tag_id(self, operator, value):
        query = self.with_context(active_test=False)._search([('product_variant_ids.tag_id', operator, value)])
        return [('id', 'in', query)]
    

    def _set_tag_id(self):
        for template in self:
            variant_count = len(template.product_variant_ids)
            if variant_count == 1:
                # Update the tags on the single active variant
                template.product_variant_ids.tag_id = [(6, 0, template.tag_id.ids)]
            elif variant_count == 0:
                archived_variants = template.with_context(active_test=False).product_variant_ids
                if len(archived_variants) == 1:
                    # Update the tags on the single archived variant
                    archived_variants.tag_id = [(6, 0, template.tag_id.ids)]


    @api.model
    def create(self, vals):
        res = super(ProductTemplate, self).create(vals)
        if vals.get('tag_id'):
            res.write({'tag_id': [(6, 0, vals['tag_id'][0][2])]})
        if vals.get('create_date_tmp'):
            self.env.cr.execute("UPDATE product_template set create_date = %s where id = %s", (vals.get('create_date_tmp'), res.id))
        else:
            res.create_date_tmp = res.create_date
        return res
    

    def _get_sale_price_history(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        sale_history_obj = self.env['sr.sale.price.history'].sudo()
        sale_history_ids = []
        domain = [('product_id','in', self.product_variant_ids.ids)]
        sale_order_line_record_limit = int(ICPSudo.get_param('sale_order_line_record_limit'))
        sale_order_status = ICPSudo.get_param('sale_order_status')
        if not sale_order_line_record_limit:
            sale_order_line_record_limit = 100
        if not sale_order_status:
            sale_order_status = 'sale'
        if sale_order_status == 'sale':
            domain += [('state','=','sale')]
        elif sale_order_status == 'done':
            domain += [('state','=','done')]
        else:
            domain += [('state','=',('sale','done'))]

        sale_order_line_ids = self.env['sale.order.line'].sudo().search(domain,limit=sale_order_line_record_limit,order ='create_date desc')
        for line in sale_order_line_ids:
            sale_price_history_id = sale_history_obj.create({
                    'name':line.id,
                    'partner_id' : line.order_partner_id.id,
                    'user_id' : line.salesman_id.id,
                    'product_tmpl_id' : line.product_id.product_tmpl_id.id,
                    'variant_id' : line.product_id.id,
                    'sale_order_id' : line.order_id.id,
                    'sale_order_date' : line.order_id.date_order,
                    'product_uom_qty' : line.product_uom_qty,
                    'unit_price' : line.price_unit,
                    'currency_id' : line.currency_id.id,
                    'total_price' : line.price_subtotal
                })
            sale_history_ids.append(sale_price_history_id.id)
        self.sale_price_history_ids = sale_history_ids

    def _get_purchase_price_history(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        purchase_history_obj = self.env['sr.purchase.price.history'].sudo()
        purchase_history_ids = []
        domain = [('product_id','in', self.product_variant_ids.ids)]
        purchase_order_line_record_limit = int(ICPSudo.get_param('purchase_order_line_record_limit'))
        purchase_order_status = ICPSudo.get_param('purchase_order_status')
        if not purchase_order_line_record_limit:
            purchase_order_line_record_limit = 30
        if not purchase_order_status:
            purchase_order_status = 'purchase'
        if purchase_order_status == 'purchase':
            domain += [('state','=','purchase')]
        elif purchase_order_status == 'done':
            domain += [('state','=','done')]
        else:
            domain += [('state','=',('purchase','done'))]

        purchase_order_line_ids = self.env['purchase.order.line'].sudo().search(domain,limit=purchase_order_line_record_limit,order ='create_date desc')
        for line in purchase_order_line_ids:
            purchase_price_history_id = purchase_history_obj.create({
                    'name':line.id,
                    'partner_id' : line.partner_id.id,
                    'user_id' : line.order_id.user_id.id,
                    'product_tmpl_id' : line.product_id.product_tmpl_id.id,
                    'variant_id' : line.product_id.id,
                    'purchase_order_id' : line.order_id.id,
                    'purchase_order_date' : line.order_id.date_order,
                    'product_uom_qty' : line.product_qty,
                    'unit_price' : line.price_unit,
                    'currency_id' : line.currency_id.id,
                    'total_price' : line.price_total
                })
            purchase_history_ids.append(purchase_price_history_id.id)
        self.purchase_price_history_ids = purchase_history_ids

    sale_price_history_ids = fields.Many2many("sr.sale.price.history", string="Sale Price History",
                                              compute="_get_sale_price_history")
    purchase_price_history_ids = fields.Many2many("sr.purchase.price.history", string="Purchase Price History",
                                                  compute="_get_purchase_price_history")

    @api.onchange('company_id')
    def company_id_onchange(self):
        if (not self.company_id.id == self.env.company.id) and self.company_id:
            raise ValidationError("You can only set the company '%s' for this product." % self.env.company.name)
        
    def action_open_sale_price_history_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Export Sale Price History',
            'res_model': 'sale.price.history.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('metroerp_customizations.view_sale_price_history_wizard_form').id,
            'target': 'new',
            'context': {
                'default_template_id': self.id,
            },
        }

    def action_open_purchase_price_history_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Export Purchase Price History',
            'res_model': 'purchase.price.history.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('metroerp_customizations.view_purchase_price_history_wizard_form').id,
            'target': 'new',
            'context': {
                'default_template_id': self.id,
            },
        }

class ProductProduct(models.Model):
    _inherit = "product.product"
    
    create_date_tmp = fields.Datetime('Creation Date', copy=True)
    tag_id = fields.Many2many('product.tags', string="Tags")

    @api.model
    def create(self, vals):
        res = super(ProductProduct, self).create(vals)
        if vals.get('create_date_tmp'):
            self.env.cr.execute("UPDATE product_product set create_date = %s where id = %s", (vals.get('create_date_tmp'), res.id))
        else:
            res.create_date_tmp = res.create_date
        return res

    def _get_sale_price_history(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        sale_history_obj = self.env['sr.sale.price.history'].sudo()
        sale_history_ids = []
        domain = [('product_id', 'in', self.ids)]
        sale_order_line_record_limit = int(ICPSudo.get_param('sale_order_line_record_limit'))
        sale_order_status = ICPSudo.get_param('sale_order_status')
        if not sale_order_line_record_limit:
            sale_order_line_record_limit = 100
        if not sale_order_status:
            sale_order_status = 'sale'
        if sale_order_status == 'sale':
            domain += [('state', '=', 'sale')]
        elif sale_order_status == 'done':
            domain += [('state', '=', 'done')]
        else:
            domain += [('state', '=', ('sale', 'done'))]

        sale_order_line_ids = self.env['sale.order.line'].sudo().search(domain, limit=sale_order_line_record_limit,
                                                                        order='create_date desc')
        for line in sale_order_line_ids:
            sale_price_history_id = sale_history_obj.create({
                'name': line.id,
                'partner_id': line.order_partner_id.id,
                'user_id': line.salesman_id.id,
                'product_tmpl_id': line.product_id.product_tmpl_id.id,
                'variant_id': line.product_id.id,
                'sale_order_id': line.order_id.id,
                'sale_order_date': line.order_id.date_order,
                'product_uom_qty': line.product_uom_qty,
                'unit_price': line.price_unit,
                'currency_id': line.currency_id.id,
                'total_price': line.price_subtotal
            })
            sale_history_ids.append(sale_price_history_id.id)
        self.sale_price_history_ids = sale_history_ids

    def _get_purchase_price_history(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        purchase_history_obj = self.env['sr.purchase.price.history'].sudo()
        purchase_history_ids = []
        domain = [('product_id', 'in', self.product_variant_ids.ids)]
        purchase_order_line_record_limit = int(ICPSudo.get_param('purchase_order_line_record_limit'))
        purchase_order_status = ICPSudo.get_param('purchase_order_status')
        if not purchase_order_line_record_limit:
            purchase_order_line_record_limit = 30
        if not purchase_order_status:
            purchase_order_status = 'purchase'
        if purchase_order_status == 'purchase':
            domain += [('state', '=', 'purchase')]
        elif purchase_order_status == 'done':
            domain += [('state', '=', 'done')]
        else:
            domain += [('state', '=', ('purchase', 'done'))]

        purchase_order_line_ids = self.env['purchase.order.line'].sudo().search(domain,
                                                                                limit=purchase_order_line_record_limit,
                                                                                order='create_date desc')
        for line in purchase_order_line_ids:
            purchase_price_history_id = purchase_history_obj.create({
                'name': line.id,
                'partner_id': line.partner_id.id,
                'user_id': line.order_id.user_id.id,
                'product_tmpl_id': line.product_id.product_tmpl_id.id,
                'variant_id': line.product_id.id,
                'purchase_order_id': line.order_id.id,
                'purchase_order_date': line.order_id.date_order,
                'product_uom_qty': line.product_qty,
                'unit_price': line.price_unit,
                'currency_id': line.currency_id.id,
                'total_price': line.price_total
            })
            purchase_history_ids.append(purchase_price_history_id.id)
        self.purchase_price_history_ids = purchase_history_ids

    sale_price_history_ids = fields.Many2many("sr.sale.price.history", string="Sale Price History",
                                              compute="_get_sale_price_history")
    purchase_price_history_ids = fields.Many2many("sr.purchase.price.history", string="Purchase Price History",
                                                  compute="_get_purchase_price_history")

    @api.onchange('company_id')
    def company_id_onchange(self):
        if (not self.company_id.id == self.env.company.id) and self.company_id:
            raise ValidationError("You can only set the company '%s' for this product." % self.env.company.name)
        

    # Overidden Method	
    def _get_description(self, picking_type_id):
        """ return product receipt/delivery/picking description depending on
        picking type passed as argument.
        """
        self.ensure_one()
        picking_code = picking_type_id.code
        description = self.description or self.name
        if picking_code == 'incoming':
            return self.description_pickingin or description
        if picking_code == 'outgoing':
            return self.description_pickingout
        if picking_code == 'internal':
            return self.description_picking or description
        return description
    
    def action_open_sale_price_history_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Export Sale Price History',
            'res_model': 'sale.price.history.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('metroerp_customizations.view_sale_price_history_wizard_form').id,
            'target': 'new',
            'context': {
                'default_product_id': self.id,
            },
        }

    def action_open_purchase_price_history_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Export Purchase Price History',
            'res_model': 'purchase.price.history.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('metroerp_customizations.view_purchase_price_history_wizard_form').id,
            'target': 'new',
            'context': {
                'default_product_id': self.id,
            },
        }

class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    company_id = fields.Many2one('res.company', 'Company', required=True)
    item_ids = fields.One2many(
        'product.pricelist.item', 'pricelist_id', string="Pricelist Items",copy=True,
        order='product_sort_key'
    )

    @api.model
    def default_get(self, fields):
        defaults = super(ProductPricelist, self).default_get(fields)
        context = dict(self._context or {})
        if context.get('from_create_company', False) and context.get('company_id', False):
            return defaults
        else:
            # Access the current company
            current_company = self.env.company.id
            defaults['company_id'] = current_company
        # Set the current company as the default company in the product pricelist
        return defaults
    


class PricelistItem(models.Model):
    _inherit = 'product.pricelist.item'
    _order = 'product_sort_key'

    @api.depends('product_tmpl_id')
    def _compute_sort_key(self):
        """
        Compute alphanumeric sorting keys for price list items.
        """

        def alphanum_key(string):
            """ Helper function for alphanumeric sorting """
            return ''.join(
                [part.zfill(5) if part.isdigit() else part.lower() for part in re.split('([0-9]+)', string or '')]
            )

        for record in self:
            record.product_sort_key = alphanum_key(record.product_tmpl_id.name)

    product_sort_key = fields.Char(
        string="Sorting Key",
        compute='_compute_sort_key',
        store=True,
        index=True
    )


    @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
        'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
    def _get_pricelist_item_name_price(self):
        """ Overidden Method. """
        for item in self:
            if item.categ_id and item.applied_on == '2_product_category':
                item.name = item.categ_id.display_name  
            elif item.product_tmpl_id and item.applied_on == '1_product':
                item.name = item.product_tmpl_id.display_name 
            elif item.product_id and item.applied_on == '0_product_variant':
                item.name = item.product_id.with_context(display_default_code=False).display_name  
            else:
                item.name = _("All Products") 

            if item.compute_price == 'fixed':
                item.price = formatLang(item.env, item.fixed_price, monetary=True, dp="Product Price", currency_obj=item.currency_id)
            elif item.compute_price == 'percentage':
                item.price = _("%s %% discount", item.percent_price)
            else:
                item.price = _("%(percentage)s %% discount and %(price)s surcharge", percentage=item.price_discount, price=item.price_surcharge)
   
