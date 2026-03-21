# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _compute_peppol_log_count(self):
        self.peppol_log_count = len(self.env['peppol.log.sg'].search([('po_id', '=', self.id)]))

    peppol_log_count = fields.Integer(string="Purchase Order Count", compute="_compute_peppol_log_count")

    def action_view_peppol_log(self):
        """It gives a list view of Incoming Invoice Documents which have same purchase order number."""
        action = {
            'name': _('Incoming Invoice Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'peppol.log.sg',
            'target': 'current',
            'view_mode': 'tree,form'
        }
        order_ids = self.env['peppol.log.sg'].search([('po_id', '=', self.id)]).ids
        action['domain'] = [('id', 'in', order_ids)]
        return action

    def map_incoming_invoice(self):
        ctx = self._context
        self.ensure_one()
        if ctx.get('active_model') == 'peppol.log.sg':
            document = self.env['peppol.log.sg'].browse(ctx['active_id'])
            document.write({
                'po_id': self.id,
                'subtype': 'success',
                'message': 'Invoice mapped Successfully !!!',
            })
            return {
                'type': 'ir.actions.act_url',
                'url': "/web#id=" + str(document.id) + "&action=" + str(self.env.ref(
                    'account_peppol_sg.action_pepppol_log_sg_view').id) + "&model=peppol.log.sg&view_type=form&cids"
                                                                          "=&menu_id=" + str(
                    self.env.ref('account_peppol_sg.menu_sub_peppol_log').id)
            }
