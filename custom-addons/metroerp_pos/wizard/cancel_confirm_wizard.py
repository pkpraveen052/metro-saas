from odoo import api, fields, models

class PosOrderCancelWizard(models.TransientModel):
    _name = 'pos.order.cancel.wizard'
    _description = 'POS Order Cancel Wizard'

    def confirm_cancel(self):
        active_id = self.env.context.get('active_id')
        order = self.env['pos.order'].browse(active_id)
        order.cancel_pos_order()

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}