# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
import json
from datetime import datetime, timedelta


class SaleOrder(models.Model):
    _inherit = "sale.order"

    create_date_tmp = fields.Datetime('Creation Date', copy=False)

    # def create(self, vals):
    #     res = super(SaleOrder, self).create(vals)
    #     if 'create_date_tmp' in vals:
    #         self.env.cr.execute("UPDATE sale_order set create_date = %s where id = %s", (vals.get('create_date_tmp'), res.id))
    #     else:
    #         res.create_date_tmp = res.create_date
    #     return res

    @api.model
    def create(self, vals):
        record = super(SaleOrder, self).create(vals)
        if record.company_id.quotation_auto_sent:
            record.write({'state': 'sent'})
        return record

    @api.model
    def _sales_default_note(self):
        return self.env.company.use_sales_tc and self.env.company.sales_tc or ''

    note = fields.Text('Terms and conditions', default=_sales_default_note)
    date_order = fields.Datetime(string='Order Date', required=True, readonly=True, index=True,
                                 states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'sale': [('readonly', False)]}, copy=False,
                                 default=fields.Datetime.now,
                                 track_visibility='always',
                                 help="Creation date of draft/sent orders,\nConfirmation date of confirmed orders.")

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """ Inherited Method """
        res = super(SaleOrder, self).onchange_partner_id()
        if self.env.company.use_sales_tc and self.env.company.sales_tc:
            self.update({'note': self.with_context(lang=self.partner_id.lang).env.company.sales_tc})
        if self.partner_id and self.partner_id.ref:
            self.client_order_ref = self.partner_id.ref
        return res
    
    def action_confirm_sale_order(self):
        for rec in self:
            if rec.state in ['draft','sent']:
                rec.state = 'sale'

    @api.model
    def default_get(self, fields):
        rec = super(SaleOrder, self).default_get(fields)
        pricelist_id = self.env['product.pricelist'].sudo().search([('company_id', '=', self.env.company.id)], limit=1)
        if pricelist_id:
            rec['pricelist_id'] = pricelist_id.id
        else:
            rec['pricelist_id'] = False
        return rec

    @api.onchange('company_id')
    def onchange_company_id(self):
        if self.company_id:
            public_pricelist = self.env['product.pricelist'].sudo().search([('company_id', '=', self.company_id.id)], limit=1)
            if public_pricelist:
                self.pricelist_id = public_pricelist.id

    def _default_validity_date(self):
        if self.env.user.has_group('metroerp_customizations.group_quotation_validity'):
            days = self.env.company.quotation_validity_days
            if days > 0:
                return fields.Date.to_string(datetime.now() + timedelta(days))
        return False

    validity_date = fields.Date(string='Expiration', readonly=True, copy=False,
                                states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                                default=_default_validity_date)



    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        company = self.company_id

        if company.order_date_same_as_quotation_date:
            invoice_vals['invoice_date'] = self.date_order

        if company.use_sales_invoice_tc:
            if company.sales_invoice_tc:
                invoice_vals['narration'] = company.sales_invoice_tc
            elif self.note:
                invoice_vals['narration'] = self.note
            else:
                invoice_vals['narration'] = False
        else:
            invoice_vals['narration'] = False

        return invoice_vals




    def _prepare_confirmation_values(self):
        date_order = fields.Datetime.now()
        param = self.company_id.order_date_same_as_quotation_date
        if param:
            date_order = self.date_order
        return {
            'state': 'sale',
            'date_order': date_order
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def product_id_change(self):
        """ Inherited Method """
        result = super(SaleOrderLine, self).product_id_change()
        # if not self.order_id.partner_id:
        #     self.price_unit = self.product_id.lst_price #TODO Change to Default company's public pricelist
        valid_values = self.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
        print("valid_values ===",valid_values)
        if valid_values and (self.product_id.product_tmpl_id.product_variant_count > 1):
            return result
        if not self.product_id.description_sale:
            self.name = " "
        elif self.product_id.description_sale:
            description_sale = self.product_id.description_sale.strip()
            if not description_sale:
                description_sale = " "
            self.name = description_sale
        return result

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"


class Tag(models.Model):
    _inherit = "crm.tag"

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    _sql_constraints = [('name_uniq', 'check(1=1)', 'No error')]

    @api.constrains('name', 'company_id')
    def _check_unique_name_within_company(self):
        for record in self:
            if self.search_count([('name', '=', record.name), ('company_id', '=', record.company_id.id)]) > 1:
                raise ValidationError('Tag name already exists !')

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    company_id = fields.Many2one(
        'res.company', string='Company', index=True,required=True,
        default=lambda self: self.env.company)

