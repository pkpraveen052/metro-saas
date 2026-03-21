# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model
    def _purchase_default_note(self):
        return self.env.company.use_purchase_tc and self.env.company.purchase_tc or ''

    notes = fields.Text('Terms and Conditions', default=_purchase_default_note)
    create_date_tmp = fields.Datetime('Creation Date', copy=False)
    date_approve = fields.Datetime('Confirmation Date', readonly=0, index=True, copy=False, track_visibility='always')

    @api.model
    def create(self, vals):
        res = super(PurchaseOrder, self).create(vals)
        if vals.get('create_date_tmp'):
            self.env.cr.execute("UPDATE purchase_order set create_date = %s where id = %s", (vals.get('create_date_tmp'), res.id))
        else:
            res.create_date_tmp = res.create_date
        return res

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        date_setting_check = self.company_id.confirmation_date_same_as_order_deadline
        if date_setting_check:
            self.date_approve = self.date_order
        return res

    def _prepare_invoice(self):
        res = super(PurchaseOrder, self)._prepare_invoice()
        date_setting_check = self.company_id.confirmation_date_same_as_order_deadline
        if date_setting_check:
            res['invoice_date'] = res['date'] = res['invoice_date_due'] = self.date_order
        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('product_id')
    def onchange_product_id(self):
        """ Inherited Method """
        if not self.product_id:
            return
        result = super(PurchaseOrderLine, self).onchange_product_id()

        valid_values = self.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
        if valid_values and (self.product_id.product_tmpl_id.product_variant_count > 1):
            return result
            
        if not self.product_id.description_purchase:
            self.name = " "
        elif self.product_id.description_purchase:
            description_purchase = self.product_id.description_purchase.strip()
            if not description_purchase:
                description_purchase = " "
            self.name = description_purchase
        return result

