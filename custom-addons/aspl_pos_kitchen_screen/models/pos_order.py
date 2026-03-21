# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo.exceptions import UserError
import re
import pytz
from odoo import models, fields, api
from itertools import groupby
# Metro changes added here
line_state = {'Waiting': 1, 'Preparing': 2, 'Delivering': 3, 'Done': 4, False: 0}


class PosOrder(models.Model):
    _inherit = "pos.order"

    order_state = fields.Selection(
        [("Start", "Start"), ("Done", "Done"), ("Deliver", "Deliver"), ("Complete", "Complete")], default="Start")
    line_cancel_reason_ids = fields.One2many('order.line.cancel.reason', 'pos_order_id', string="Line Cancel Reason")
    send_to_kitchen = fields.Boolean('Send to Kitchen', readonly=True)

    def _get_fields_for_order_line(self):
        res = super(PosOrder, self)._get_fields_for_order_line()
        if isinstance(res, list):
            res.append('state')
            res.append('line_cid')
        return res
    
    def _get_fields_for_draft_order(self):
        res = super(PosOrder, self)._get_fields_for_draft_order()
        if isinstance(res, list):
            res.append('order_state')
            res.append('send_to_kitchen')
        return res

    @api.model
    def _process_order(self, order, draft, existing_order):
        res = super(PosOrder, self)._process_order(order, draft, existing_order)
        if order and order.get('data') and order.get('data').get('delete_product') and order.get('data').get(
                'server_id') and order.get('data').get('cancel_product_reason'):
            order_id = self.browse(order.get('data').get('server_id'))
            reason = order.get('data').get('cancel_product_reason')
            order_id.write({
                'line_cancel_reason_ids': [(0, 0, {
                    'pos_order_id': order_id.id,
                    'product_id': reason.get('product'),
                    'reason': reason.get('reason_id'),
                    'description': reason.get('description'),
                })],
            })
        self.broadcast_order_data(True)
        return res

    def _get_order_lines(self, orders):
        order_lines = self.env['pos.order.line'].search_read(
            domain=[('order_id', 'in', [to['id'] for to in orders])],
            fields=self._get_fields_for_order_line())

        if order_lines:
            self._get_pack_lot_lines(order_lines)

        extended_order_lines = []
        for order_line in order_lines:
            order_line['product_id'] = order_line['product_id'][0]
            order_line['server_id'] = order_line['id']
            del order_line['id']
            if 'pack_lot_ids' not in order_line:
                order_line['pack_lot_ids'] = []
            extended_order_lines.append([0, 0, order_line])
        for order_id, order_lines in groupby(extended_order_lines, key=lambda x: x[2]['order_id']):
            next(order for order in orders if order['id'] == order_id[0])['lines'] = list(order_lines)

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        res['send_to_kitchen'] = ui_order.get('send_to_kitchen', False)
        res['order_state'] = ui_order.get('order_state', False)
        return res

    @api.model
    def broadcast_order_data(self, new_order):
        pos_order = self.search([('lines.state', 'not in', ['cancel', 'done']),
                                 ('amount_total', '>', 0.00), ('send_to_kitchen', '=', True)])
        screen_table_data = []
        for order in pos_order:
            # if order.order_state != 'Complete':
            order_line_list = []
            for line in order.lines:
                order_line = {
                    'id': line.id,
                    'order_id': order.id,
                    'line_cid': line.line_cid,
                    'name': line.product_id.display_name,
                    'full_product_name': line.full_product_name,
                    'qty': line.qty,
                    'note': line.note,
                    'table': line.order_id.table_id.name,
                    'floor': line.order_id.table_id.floor_id.name,
                    'state': line.state,
                    'categ_id': line.product_id.product_tmpl_id.pos_categ_id.id,
                    'order_name': line.order_id.name,
                    'user': line.create_uid.id,
                    'route_id': line.product_id.product_tmpl_id.route_ids.active,
                }
                order_line_list.append(order_line)
            order_dict = {
                'order_id': order.id,
                'order_name': order.name,
                'order_time': order.date_order,
                'table': order.table_id.name,
                'floor': order.table_id.floor_id.name,
                'customer': order.partner_id.name,
                'order_lines': order_line_list,
                'total': order.amount_total,
                'note': order.note,
                'user_id': order.user_id.id,
                'user_name': order.user_id.name,
                'guests': order.customer_count,
                'order_state': order.order_state,
                'pos_reference': order.pos_reference
            }
            screen_table_data.append(order_dict)
        screen_table_data = screen_table_data[::-1]
        notifications = []
        cook_user_ids = self.env['res.users'].search([('kitchen_screen_user', '=', 'cook')])
        manager_user_ids = self.env['res.users'].search([('kitchen_screen_user', '=', 'manager')])
        if cook_user_ids:
            for each_cook_id in cook_user_ids:
                notifications.append(
                    ((self._cr.dbname, 'pos.order.line', each_cook_id.id),
                     {'screen_display_data': screen_table_data, 'new_order': new_order, 'manager': False}))
        if manager_user_ids:
            for each_manager_id in manager_user_ids:
                notifications.append(
                    ((self._cr.dbname, 'pos.order.line', each_manager_id.id),
                     {'screen_display_data': screen_table_data, 'new_order': new_order, 'manager': True}))
        if notifications:
            self.env['bus.bus'].sendmany(notifications)
        return True
    
    #Metro added this method to auto remove kitchenscreen order once validated done by manager
    def action_pos_order_paid(self):
        res = super(PosOrder, self).action_pos_order_paid()
        for order in self:
            for line in order.lines.filtered(lambda l: l.state != 'Done'):
                line.update_orderline_state({
                    'state': 'Done',
                    'order_line_id': line.id,
                    'order_id': order.id,
                })
        return res

    # def _export_for_ui(self, order):
    #     timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
    #     try:
    #         uid_match = re.search(r'([0-9]|-){14}', order.pos_reference or '')
    #         uid_value = uid_match.group(0) if uid_match else (order.name or 'Unknown')

    #         return {
    #             'lines': [[0, 0, line] for line in order.lines.export_for_ui()],
    #             'statement_ids': [[0, 0, payment] for payment in order.payment_ids.export_for_ui()],
    #             'name': order.pos_reference,
    #             'uid': uid_value,
    #             'amount_paid': order.amount_paid,
    #             'amount_total': order.amount_total,
    #             'amount_tax': order.amount_tax,
    #             'amount_return': order.amount_return,
    #             'pos_session_id': order.session_id.id,
    #             'is_session_closed': order.session_id.state == 'closed',
    #             'pricelist_id': order.pricelist_id.id,
    #             'partner_id': order.partner_id.id,
    #             'user_id': order.user_id.id,
    #             'sequence_number': order.sequence_number,
    #             'creation_date': order.date_order.astimezone(timezone),
    #             'fiscal_position_id': order.fiscal_position_id.id,
    #             'to_invoice': order.to_invoice,
    #             'state': order.state,
    #             'account_move': order.account_move.id,
    #             'id': order.id,
    #             'is_tipped': order.is_tipped,
    #             'tip_amount': order.tip_amount,
    #         }
    #     except Exception as e:
    #         # Wrap in UserError so frontend can display properly
    #         raise UserError(f"POS export failed: {str(e)}")
    

    # @api.model
    # def get_table_draft_orders(self, table_id):
    #     """Generate an object of all draft orders for the given table."""
    #     table_orders = self.search_read(
    #         domain=[('state', '=', 'draft'), ('table_id', '=', table_id)],
    #         fields=self._get_fields_for_draft_order()
    #     )

    #     self._get_order_lines(table_orders)
    #     self._get_payment_lines(table_orders)

    #     for order in table_orders:
    #         order['pos_session_id'] = order['session_id'][0]

    #         # Safe regex check
    #         match = re.search(r"\d{5,}-\d{3,}-\d{4,}", order['pos_reference'] or "")
    #         if match:
    #             order['uid'] = match.group(0)
    #         else:
    #             # fallback: use pos_reference directly
    #             order['uid'] = order['pos_reference']

    #         order['name'] = order['pos_reference']
    #         order['creation_date'] = order['create_date']
    #         order['server_id'] = order['id']

    #         if order['fiscal_position_id']:
    #             order['fiscal_position_id'] = order['fiscal_position_id'][0]
    #         if order['pricelist_id']:
    #             order['pricelist_id'] = order['pricelist_id'][0]
    #         if order['partner_id']:
    #             order['partner_id'] = order['partner_id'][0]
    #         if order['table_id']:
    #             order['table_id'] = order['table_id'][0]
    #         if 'employee_id' in order:
    #             order['employee_id'] = order['employee_id'][0] if order['employee_id'] else False

    #         if 'lines' not in order:
    #             order['lines'] = []
    #         if 'statement_ids' not in order:
    #             order['statement_ids'] = []

    #         del order['id']
    #         del order['session_id']
    #         del order['pos_reference']
    #         del order['create_date']

    #     return table_orders



class PosOrderLines(models.Model):
    _inherit = "pos.order.line"

    state = fields.Selection(
        selection=[("Waiting", "Waiting"), ("Preparing", "Preparing"), ("Delivering", "Delivering"),
                   ("Done", "Done")], default="Waiting")
    line_cid = fields.Char('Line cid')

    # @api.model
    # def update_orderline_state(self, vals):
    #     order_line = self.browse(vals['order_line_id'])
    #     order = self.env['pos.order'].browse(vals['order_id'])
    #     if line_state[vals['state']] >= line_state[order_line.state]:
    #         order_line.sudo().write({
    #             'state': vals['state']
    #         })
    #         vals['pos_reference'] = order_line.order_id.pos_reference
    #         state_list = [line.state for line in order.lines]
    #         if 'Waiting' in state_list:
    #             order_state = 'Start'
    #             order.sudo().write({'order_state': order_state})
    #         elif 'Preparing' in state_list:
    #             order_state = 'Done'
    #             order.sudo().write({'order_state': order_state})
    #         elif 'Preparing' in state_list:
    #             order_state = 'Deliver'
    #             order.sudo().write({'order_state': order_state})
    #         else:
    #             print("Done")
    #         order.broadcast_order_data(False)
    #         vals.update({
    #             'server_id': order_line.id,
    #             'product_id': order_line.product_id.id,
    #         })
    #         notifications = [
    #             ((self._cr.dbname, 'pos.order.line', order_line.create_uid.id), {'order_line_state': vals})]
    #         self.env['bus.bus'].sendmany(notifications)
    #         return True

    @api.model
    def update_orderline_state(self, vals):
        order_line = self.browse(vals['order_line_id'])
        order = self.env['pos.order'].browse(vals['order_id'])

        if line_state[vals['state']] >= line_state[order_line.state]:
            order_line.sudo().write({
                'state': vals['state']
            })
            vals['pos_reference'] = order_line.order_id.pos_reference

            # Recompute the overall order state based on line states
            state_list = [line.state for line in order.lines]

            if any(state == 'Waiting' for state in state_list):
                order_state = 'Start'
            elif any(state == 'Preparing' for state in state_list):
                order_state = 'Deliver'
            elif all(state == 'Done' for state in state_list):
                order_state = 'Done'
            else:
                order_state = order.order_state  # Keep existing state

            if order.order_state != order_state:
                order.sudo().write({'order_state': order_state})

            order.broadcast_order_data(False)

            vals.update({
                'server_id': order_line.id,
                'product_id': order_line.product_id.id,
            })

            notifications = [
                ((self._cr.dbname, 'pos.order.line', order_line.create_uid.id), {'order_line_state': vals})
            ]
            self.env['bus.bus'].sendmany(notifications)
            return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
