# -*- coding: utf-8 -*-

from odoo import models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _check_stock_account_installed(self):
        stock_account_app = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'stock_account')], limit=1)
        if stock_account_app.state != 'installed':
            return False
        else:
            return True

    def _check_stock_installed(self):
        stock_app = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'stock')], limit=1)
        if stock_app.state != 'installed':
            return False
        else:
            return True

    def action_purchase_cancel(self):
        for rec in self:
            if rec.company_id.cancel_receipt and self._check_stock_installed():
                self.sh_picking_cancel(rec.sudo().mapped('picking_ids'),'cancel')
            if rec.company_id.cancel_bill:
                if rec.mapped('invoice_ids'):
                    if rec.mapped('invoice_ids'):
                        move = rec.mapped('invoice_ids')
                        move_line_ids = move.sudo().mapped('line_ids')
                        reconcile_ids = []
                        if move_line_ids:
                            reconcile_ids = move_line_ids.sudo().mapped('id')
                        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                            ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                        payments = False
                        if reconcile_lines:
                            payments = self.env['account.payment'].search(['|', ('invoice_line_ids.id', 'in', reconcile_lines.mapped(
                                'credit_move_id').ids), ('invoice_line_ids.id', 'in', reconcile_lines.mapped('debit_move_id').ids)])
                            reconcile_lines.sudo().unlink()
                            if payments:
                                payment_ids = payments
                                if payment_ids.sudo().mapped('move_id').mapped('line_ids'):
                                    payment_lines = payment_ids.sudo().mapped('move_id').mapped('line_ids')
                                    reconcile_ids = payment_lines.sudo().mapped('id')

                        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                            ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                        if reconcile_lines:
                            reconcile_lines.sudo().unlink()
                        move.mapped(
                            'line_ids.analytic_line_ids').sudo().unlink()

                        move_line_ids.sudo().write({'parent_state': 'draft'})
                        move.sudo().write({'state': 'draft'})
                        if payments:
                            payment_ids = payments

                            payment_ids.sudo().mapped(
                                'move_id').write({'state': 'draft'})
                            payment_ids.sudo().mapped('move_id').mapped(
                                'line_ids').sudo().write({'parent_state': 'draft'})
                            payment_ids.sudo().mapped('move_id').mapped('line_ids').sudo().unlink()
                            payment_ids.sudo().write({'state': 'cancel'})

                            payment_ids.sudo().mapped('move_id').with_context(
                                {'force_delete': True}).unlink()

                    rec.mapped('invoice_ids').sudo().write({'state': 'cancel'})
            rec.sudo().write({'state': 'cancel'})

    def action_purchase_cancel_draft(self):
        for rec in self:
            if rec.company_id.cancel_receipt and self._check_stock_installed():
                self.sh_picking_cancel(rec.sudo().mapped('picking_ids'),'draft')
            if rec.company_id.cancel_bill:
                if rec.mapped('invoice_ids'):
                    if rec.mapped('invoice_ids'):
                        move = rec.mapped('invoice_ids')
                        move_line_ids = move.sudo().mapped('line_ids')

                        reconcile_ids = []
                        if move_line_ids:
                            reconcile_ids = move_line_ids.sudo().mapped('id')

                        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                            ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                        payments = False
                        if reconcile_lines:
                            payments = self.env['account.payment'].search(['|', ('invoice_line_ids.id', 'in', reconcile_lines.mapped(
                                'credit_move_id').ids), ('invoice_line_ids.id', 'in', reconcile_lines.mapped('debit_move_id').ids)])

                            reconcile_lines.sudo().unlink()

                            if payments:

                                payment_ids = payments
                                if payment_ids.sudo().mapped('move_id').mapped('line_ids'):
                                    payment_lines = payment_ids.sudo().mapped('move_id').mapped('line_ids')
                                    reconcile_ids = payment_lines.sudo().mapped('id')

                        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                            ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                        if reconcile_lines:
                            reconcile_lines.sudo().unlink()
                        move.mapped(
                            'line_ids.analytic_line_ids').sudo().unlink()

                        move_line_ids.sudo().write({'parent_state': 'draft'})
                        move.sudo().write({'state': 'draft'})

                        if payments:
                            payment_ids = payments
                            payment_ids.sudo().mapped(
                                'move_id').write({'state': 'draft'})
                            payment_ids.sudo().mapped('move_id').mapped(
                                'line_ids').sudo().write({'state': 'draft'})
                            payment_ids.sudo().mapped('move_id').mapped('line_ids').sudo().unlink()
                            payment_ids.sudo().write({'state': 'cancel'})

                            payment_ids.sudo().mapped('move_id').with_context(
                                {'force_delete': True}).unlink()

#                             payment_ids.sudo().unlink()
                    rec.mapped('invoice_ids').sudo().write({'state': 'draft'})
            rec.sudo().write({'state': 'draft'})

    def action_purchase_cancel_delete(self):
        for rec in self:
            if rec.company_id.cancel_receipt and self._check_stock_installed():
                self.sh_picking_cancel(rec.sudo().mapped('picking_ids'),'delete')
            if rec.company_id.cancel_bill:

                if rec.mapped('invoice_ids'):
                    if rec.mapped('invoice_ids'):
                        move = rec.mapped('invoice_ids')
                        move_line_ids = move.sudo().mapped('line_ids')

                        reconcile_ids = []
                        if move_line_ids:
                            reconcile_ids = move_line_ids.sudo().mapped('id')

                        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                            ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                        payments = False
                        if reconcile_lines:
                            payments = self.env['account.payment'].search(['|', ('invoice_line_ids.id', 'in', reconcile_lines.mapped(
                                'credit_move_id').ids), ('invoice_line_ids.id', 'in', reconcile_lines.mapped('debit_move_id').ids)])

                            reconcile_lines.sudo().unlink()

                            if payments:
                                payment_ids = payments
                                if payment_ids.sudo().mapped('move_id').mapped('line_ids'):
                                    payment_lines = payment_ids.sudo().mapped('move_id').mapped('line_ids')
                                    reconcile_ids = payment_lines.sudo().mapped('id')

                        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                            ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                        if reconcile_lines:
                            reconcile_lines.sudo().unlink()
                        move.mapped(
                            'line_ids.analytic_line_ids').sudo().unlink()

                        move_line_ids.sudo().write({'parent_state': 'draft'})
                        move.sudo().write({'state': 'draft'})

                        if payments:
                            payment_ids = payments
                            payment_ids.sudo().mapped(
                                'move_id').write({'state': 'draft'})
                            payment_ids.sudo().mapped('move_id').mapped(
                                'line_ids').sudo().write({'parent_state': 'draft'})
                            payment_ids.sudo().mapped('move_id').mapped('line_ids').sudo().unlink()

                            payment_ids.sudo().write({'state': 'cancel'})
#                             payment_ids.sudo().unlink()
                            payment_ids.sudo().mapped('move_id').with_context(
                                {'force_delete': True}).unlink()

                    rec.mapped('invoice_ids').sudo().write({'state': 'draft'})
                    rec.mapped('invoice_ids').sudo().with_context(
                        {'force_delete': True}).unlink()

            rec.sudo().write({'state': 'cancel'})
            rec.sudo().unlink()

    def sh_cancel(self):
        if self.company_id.po_operation_type == 'cancel':
            self.action_purchase_cancel()
        elif self.company_id.po_operation_type == 'cancel_draft':
            self.action_purchase_cancel_draft()
        elif self.company_id.po_operation_type == 'cancel_delete':
            self.action_purchase_cancel_delete()
            return {
                'name': 'Purchase Order',
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_type': 'form',
                'view_mode': 'tree,kanban,form,pivot,graph,calendar,activity',
                'target': 'current',
                'context': {}
            }

    def sh_picking_cancel(self,picking_ids,cancel_type):
        """
        The function cancels a picking and performs related actions such as cancelling related accounting
        entries and removing packages.
        """
        for rec in picking_ids:
            if rec.state in ('assigned', 'confirmed', 'draft', 'waiting'):
                if cancel_type == 'cancel':
                    rec.action_cancel()
                elif cancel_type == 'draft':
                    rec.do_unreserve()
                    rec.move_ids.state = "draft"
                else:
                    rec.action_cancel()
                    rec.unlink()
                continue
            state="draft"
            if cancel_type == 'cancel':
                state="cancel"
            if rec.sudo().mapped('move_ids_without_package'):
                self._sh_unreseve_qty(rec)
                rec.sudo().mapped('move_ids_without_package').sudo().write(
                    {'state': state})
                rec.sudo().mapped('move_ids_without_package').mapped(
                    'move_line_ids').sudo().write({'state': state})

                if self._check_stock_account_installed():

                    # cancel related accouting entries
                    account_move = rec.sudo().mapped(
                        'move_ids_without_package').sudo().mapped('account_move_ids')
                    account_move_line_ids = account_move.sudo().mapped('line_ids')
                    reconcile_ids = []
                    if account_move_line_ids:
                        reconcile_ids = account_move_line_ids.sudo().mapped('id')
                    reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                        ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                    if reconcile_lines:
                        reconcile_lines.sudo().unlink()
                    account_move.mapped(
                        'line_ids.analytic_line_ids').sudo().unlink()
                    account_move.sudo().write({'state': 'draft', 'name': '/'})
                    account_move.sudo().with_context(
                        {'force_delete': True}).unlink()

                    # cancel stock valuation
                    stock_valuation_layer_ids = rec.sudo().mapped(
                        'move_ids_without_package').sudo().mapped('stock_valuation_layer_ids')
                    if stock_valuation_layer_ids:
                        stock_valuation_layer_ids.sudo().unlink()
            self._remove_packages(rec)
            rec.sudo().write({'state': state})
            if cancel_type == 'delete':
                rec.sudo().unlink()
     
    def _remove_packages(self,picking_id):
        """
        This function removes packages associated with move lines in a record.
        """
        result_package_id = picking_id.move_line_ids.mapped('result_package_id')
        if result_package_id:
            picking_id.move_line_ids.result_package_id = False
            result_package_id.unpack()
            result_package_id.unlink()

        package_id = picking_id.move_line_ids.mapped('package_id')
        if package_id:
            picking_id.move_line_ids.package_id = False
            package_id.unpack()
            package_id.unlink()

    def _sh_unreseve_qty(self,picking_id):
        if picking_id.state != 'done':
            picking_id.do_unreserve()
        for move_line in picking_id.sudo().mapped('move_ids_without_package').mapped('move_line_ids'):
            if move_line.product_id.type == 'consu':
                continue
            # Check qty is not in draft and cancel state
            if picking_id.state not in ['draft','cancel','assigned','waiting'] :

                # unreserve qty
                quant = picking_id.env['stock.quant'].sudo().search([('location_id', '=', move_line.location_id.id),
                                                               ('product_id', '=', move_line.product_id.id),
                                                               ('lot_id', '=', move_line.lot_id.id),
                                                               ('package_id', '=', move_line.package_id.id),
                                                               ], limit=1)
    
                if quant:
                    quant.write({'quantity': quant.quantity + move_line.qty_done})
                else:
                    self.env['stock.quant'].sudo().create({'location_id': move_line.location_id.id,
                                                            'product_id': move_line.product_id.id,
                                                            'lot_id': move_line.lot_id.id,
                                                            'quantity': move_line.qty_done,
                                                            # 'package_id': move_line.package_id.id
                                                            })
                quant = self.env['stock.quant'].sudo().search([('location_id', '=', move_line.location_dest_id.id),
                                                               ('product_id', '=', move_line.product_id.id),
                                                               ('lot_id', '=', move_line.lot_id.id),
                                                               ('package_id', '=', move_line.result_package_id.id),
                                                               ], limit=1)
                if quant:
                    quant.write({'quantity': quant.quantity - move_line.qty_done})
                else:
                    self.env['stock.quant'].sudo().create({'location_id': move_line.location_dest_id.id,
                                                            'product_id': move_line.product_id.id,
                                                            'lot_id':move_line.lot_id.id,
                                                            'quantity':move_line.qty_done * (-1),
                                                            # 'package_id': move_line.result_package_id.id 
                                                            })
