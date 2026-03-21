from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    has_only_service_products = fields.Boolean(
        compute="_compute_has_only_service_products",
        store=False
    )

    @api.depends('order_line', 'order_line.product_id.type')
    def _compute_has_only_service_products(self):
        for order in self:
            # True if every product is service
            order.has_only_service_products = all(
                line.product_id.type == 'service'
                for line in order.order_line
            ) if order.order_line else False

    # def action_create_remaining_delivery(self):
    #     for order in self:
    #         if order.state not in ['sale', 'done']:
    #             raise UserError(_("You can only create deliveries for confirmed orders."))

    #         remaining_moves = []

    #         # Loop through order lines
    #         for line in order.order_line:
    #             ordered_qty = line.product_uom_qty

    #             # All moves (regardless of state) already created for this line
    #             # already_moved_qty = sum(line.move_ids.mapped('product_uom_qty'))
    #             already_moved_qty = sum(
    #                 line.move_ids.filtered(lambda m: m.state != 'cancel' and m.picking_id.state != 'cancel')
    #                               .mapped('product_uom_qty')
    #             )
                
    #             # Remaining to deliver
    #             remaining_qty = ordered_qty - already_moved_qty

    #             if remaining_qty > 0:
    #                 remaining_moves.append((line, remaining_qty))

    #         if not remaining_moves:
    #             raise UserError(_("No remaining quantity to deliver. All quantities already have delivery orders created."))

    #         # Create Picking (DO)
    #         picking_type = order.warehouse_id.out_type_id
    #         picking_vals = {
    #             'picking_type_id': picking_type.id,
    #             'partner_id': order.partner_shipping_id.id,
    #             'origin': order.name,
    #             'location_id': order.warehouse_id.lot_stock_id.id,
    #             'location_dest_id': order.partner_shipping_id.property_stock_customer.id,
    #             'sale_id': order.id,
    #             # 'group_id': order.procurement_group_id.id,
    #         }
    #         print(picking_vals)
    #         picking = self.env['stock.picking'].create(picking_vals)

    #         # Create stock moves for remaining qty
    #         for line, qty in remaining_moves:
    #             move_vals = {
    #                 'name': line.name or line.product_id.display_name,
    #                 'product_id': line.product_id.id,
    #                 'product_uom_qty': qty,
    #                 'product_uom': line.product_uom.id,
    #                 'picking_id': picking.id,
    #                 'location_id': picking.location_id.id,
    #                 'location_dest_id': picking.location_dest_id.id,
    #                 'sale_line_id': line.id,
    #                 'group_id': order.procurement_group_id.id
    #             }
    #             self.env['stock.move'].create(move_vals)

    #         picking.action_confirm()
    #         picking.action_assign()

    #         # 🔑 Force recomputation of picking_ids so delivery count updates
    #         order.invalidate_cache(['picking_ids'])

    #         return {
    #             'name': _('Delivery Order'),
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'stock.picking',
    #             'view_mode': 'form',
    #             'res_id': picking.id,
    #         }


    def action_create_remaining_delivery(self):
        for order in self:
            if order.state not in ['sale', 'done']:
                raise UserError(_("You can only create deliveries for confirmed orders."))

            remaining_moves = []

            for line in order.order_line:

                # Skip service products
                if line.product_id.type == 'service':
                    continue

                ordered_qty = line.product_uom_qty

                # Already delivered qty (excluding cancelled)
                already_moved_qty = sum(
                    line.move_ids.filtered(lambda m: m.state != 'cancel' and m.picking_id.state != 'cancel')
                                .mapped('product_uom_qty')
                )

                remaining_qty = ordered_qty - already_moved_qty

                if remaining_qty > 0:
                    remaining_moves.append((line, remaining_qty))

            if not remaining_moves:
                raise UserError(_("No remaining quantity to deliver. All remaining products are services or already delivered."))

            # Create Delivery (Picking)
            picking_type = order.warehouse_id.out_type_id
            picking_vals = {
                'picking_type_id': picking_type.id,
                'partner_id': order.partner_shipping_id.id,
                'origin': order.name,
                'location_id': order.warehouse_id.lot_stock_id.id,
                'location_dest_id': order.partner_shipping_id.property_stock_customer.id,
                'sale_id': order.id,
            }

            picking = self.env['stock.picking'].create(picking_vals)

            # Create only stockable/consumable product moves
            for line, qty in remaining_moves:
                move_vals = {
                    'name': line.name or line.product_id.display_name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': qty,
                    'product_uom': line.product_uom.id,
                    'picking_id': picking.id,
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'sale_line_id': line.id,
                    'group_id': order.procurement_group_id.id
                }
                self.env['stock.move'].create(move_vals)

            picking.action_confirm()
            picking.action_assign()
            order.invalidate_cache(['picking_ids'])

            return {
                'name': _('Delivery Order'),
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'form',
                'res_id': picking.id,
            }

