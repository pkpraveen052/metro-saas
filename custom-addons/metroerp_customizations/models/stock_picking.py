# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class Stock(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking','portal.mixin']

    def _get_default_require_signature(self):
        return self.env.company.group_stock_sign_delivery

    signature = fields.Image('Signature', help='Signature received through the portal.', copy=False, attachment=True, max_width=1024, max_height=1024)
    signed_by = fields.Char('Signed By', help='Name of the person that signed the DO.', copy=False)
    signed_on = fields.Datetime('Signed On', help='Date of the signature.', copy=False)
    require_signature = fields.Boolean('Online Signature',default=_get_default_require_signature,readonly=True,
        states={'draft': [('readonly', False)], 'assigned': [('readonly', False)]},
        help='Request a online signature to the customer.')
    is_expired = fields.Boolean(string="Expired")
    so_reference = fields.Char(string="Reference",help="Reference of the sale order related to this delivery order.")


    @api.model
    def _delivery_default_note(self):
        """Default note for Delivery Orders (manual creation case)."""
        picking_type_id = self.env.context.get('default_picking_type_id')
        if picking_type_id:
            picking_type = self.env['stock.picking.type'].browse(picking_type_id)
            if (picking_type.code == 'outgoing' and self.env.company.use_delivery_tc and self.env.company.deliver_tc):
                return self.env.company.deliver_tc
        return ''

    note = fields.Text('Notes', default=_delivery_default_note)

    @api.model
    def create(self, vals_list):
        """Ensure Delivery Orders created from SO get default note."""
        records = super().create(vals_list)
        for rec in records:
            if (
                rec.picking_type_id.code == 'outgoing'
                and not rec.note
                and rec.env.company.use_delivery_tc
                and rec.env.company.deliver_tc
            ):
                rec.note = rec.env.company.deliver_tc
        return records

    @api.onchange('picking_type_id')
    def _onchange_picking_type_id_set_note(self):
        """Auto-fill or clear note when user changes operation type in UI."""
        if (
            self.picking_type_id
            and self.picking_type_id.code == 'outgoing'
            and self.env.company.use_delivery_tc
            and not self.note
            and self.env.company.deliver_tc
        ):
            self.note = self.env.company.deliver_tc
        elif self.picking_type_id and self.picking_type_id.code != 'outgoing':
            self.note = ''




    def preview_delivery(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }

    def _get_total_item(self):
        total = 0.0
        for line in self.move_lines:
            total += line.product_uom_qty
        return total

    def action_send_mail(self):
        self.ensure_one()
        lang = self.env.context.get('lang')
        templates = self.env.ref(
            'metroerp_customizations.mail_template_delivery_order_confirmation'
        )
        if templates.lang:
            lang = templates._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'stock.picking',
            'default_res_id': self.ids[0],
            'default_use_template': bool(templates),
            'default_template_id': templates.id,
            'default_composition_mode': 'comment',
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }
    
    def _get_portal_return_action(self):
        """ Return the action used to display orders when returning from customer portal. """
        self.ensure_one()
        return self.env.ref('stock.action_picking_tree_all')
    
    def _compute_access_url(self):
        super(Stock, self)._compute_access_url()
        for delivery in self:
            delivery.access_url = '/my/deliveries/%s' % (delivery.id)

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Delivery Order-%s' % (self.name)
    
    def has_to_be_signed(self, include_draft=False):
        return (self.state in ['assigned','done'] or (self.state == 'draft' and include_draft)) and self.require_signature and not self.signature
    
    def _compute_is_expired(self):
        today = fields.Date.today()
        for order in self:
            order.is_expired = order.state == 'done' and order.date_deadline and order.date_deadline < today


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _assign_picking_post_process(self, new=False):
        res = super()._assign_picking_post_process(new=new)
        if new:
            pickings = self.mapped('picking_id')
            sale_orders = self.mapped('sale_line_id.order_id')

            for picking in pickings:
                for sale_order in sale_orders:
                    # Post origin message as usual
                    picking.message_post_with_view(
                        'mail.message_origin_link',
                        values={'self': picking, 'origin': sale_order},
                        subtype_id=self.env.ref('mail.mt_note').id
                    )
                    # Set the custom reference from the sale order
                    if sale_order.client_order_ref:
                        picking.so_reference = sale_order.client_order_ref
        return res