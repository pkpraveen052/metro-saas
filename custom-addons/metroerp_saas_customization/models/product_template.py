# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero

class ProductProduct(models.Model):
    _inherit = "product.product"
    
    is_brs_deposit = fields.Boolean(
        related='product_tmpl_id.is_brs_deposit', store=True, readonly=False
        )
    
    brs_deposit_amount = fields.Float(
        related='product_tmpl_id.brs_deposit_amount', store=True, readonly=False
        )
    

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_brs_deposit = fields.Boolean(
        default=False,
        string="BCRS Deposit Required?",
        help="Indicates if this product is used for BCRS deposits."
    )

    brs_deposit_amount = fields.Float(
        default=lambda self: self.env.company.brs_deposit_amount,
        string="BCRS Deposit Amount",
        help="Amount associated with BCRS deposit products.")
    
    @api.constrains('taxes_id')
    def _check_brs_deposit_tax(self):
        for rec in self:
            company = rec.company_id or self.env.company

            if company.brs_deposit_product_id and rec.product_variant_id == company.brs_deposit_product_id:
                if rec.taxes_id:
                    raise ValidationError(
                        "You cannot set Customer Taxes for the BCRS Deposit Product."
                    )

    def open_uom_wizard(self):
        view_id = self.env.ref('metroerp_saas_customization.view_product_change_uom_form').id
        return {'type': 'ir.actions.act_window',
                'name': _('Change Uom'),
                'res_model': 'product.change.uom',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                }


    def write(self, vals):
        if 'company_id' in vals and vals['company_id']:
            products_changing_company = self.filtered(lambda product: product.company_id.id != vals['company_id'])
            if products_changing_company:
                move = self.env['stock.move'].sudo().search([
                    ('product_id', 'in', products_changing_company.product_variant_ids.ids),
                    ('company_id', 'not in', [vals['company_id'], False]),
                ], order=None, limit=1)
                if move:
                    raise UserError(_("This product's company cannot be changed as long as there are stock moves of it belonging to another company."))

                # Forbid changing a product's company when quant(s) exist in another company.
                quant = self.env['stock.quant'].sudo().search([
                    ('product_id', 'in', products_changing_company.product_variant_ids.ids),
                    ('company_id', 'not in', [vals['company_id'], False]),
                    ('quantity', '!=', 0),
                ], order=None, limit=1)
                if quant:
                    raise UserError(_("This product's company cannot be changed as long as there are quantities of it belonging to another company."))

        if 'uom_id' in vals:
            new_uom = self.env['uom.uom'].browse(vals['uom_id'])
            updated = self.filtered(lambda template: template.uom_id != new_uom)
            done_moves = self.env['stock.move'].sudo().search([('product_id', 'in', updated.with_context(active_test=False).mapped('product_variant_ids').ids)], limit=1)
            if done_moves:
                raise UserError(_("Since this product is already in use, you can update the unit of measure by clicking the Update Uom button."))
        if 'type' in vals and vals['type'] != 'product' and sum(self.mapped('nbr_reordering_rules')) != 0:
            raise UserError(_('You still have some active reordering rules on this product. Please archive or delete them first.'))
        if any('type' in vals and vals['type'] != prod_tmpl.type for prod_tmpl in self):
            existing_done_move_lines = self.env['stock.move.line'].sudo().search([
                ('product_id', 'in', self.mapped('product_variant_ids').ids),
                ('state', '=', 'done'),
            ], limit=1)
            if existing_done_move_lines:
                raise UserError(_("You can not change the type of a product that was already used."))
            existing_reserved_move_lines = self.env['stock.move.line'].search([
                ('product_id', 'in', self.mapped('product_variant_ids').ids),
                ('state', 'in', ['partially_available', 'assigned']),
            ])
            if existing_reserved_move_lines:
                raise UserError(_("You can not change the type of a product that is currently reserved on a stock move. If you need to change the type, you should first unreserve the stock move."))
        if 'type' in vals and vals['type'] != 'product' and any(p.type == 'product' and not float_is_zero(p.qty_available, precision_rounding=p.uom_id.rounding) for p in self):
            raise UserError(_("Available quantity should be set to zero before changing type"))
        return super(ProductTemplate, self).write(vals)


class ProductProduct(models.Model):
    _inherit = 'product.product'
    _inherits = {'product.template': 'product_tmpl_id'}

    def open_uom_wizard(self):
        view_id = self.env.ref('metroerp_saas_customization.view_product_change_uom_form').id
        return {'type': 'ir.actions.act_window',
                'name': _('Change Uom'),
                'res_model': 'product.change.uom',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                }

