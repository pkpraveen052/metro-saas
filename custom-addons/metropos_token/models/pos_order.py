from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

class PosOrder(models.Model):
    _inherit = 'pos.order'

    pos_receipt_sequence = fields.Char(string='POS Receipt Sequence', size=3)

    @api.model
    def create(self, vals):
        if vals.get('session_id'):
            session_obj = self.env['pos.session'].browse(vals['session_id'])
            if session_obj.config_id.display_token_no:
                vals['pos_receipt_sequence'] = self.with_context({'session_id': vals['session_id']}).get_next_token()
        return super(PosOrder, self).create(vals)
    
    @api.model
    def get_next_token(self):
        ctx = self._context or {}
        # Get the last token number assigned and increment it
        last_order = self.search([('session_id','=',ctx['session_id'])], order='id desc', limit=1)
        if last_order and last_order.pos_receipt_sequence:
            last_token = int(last_order.pos_receipt_sequence)
            new_token = (last_token % 999) + 1  # Resets to 1 after 999
        else:
            new_token = 1  # Start from 1 if no previous token exists

        return '{:03}'.format(new_token)  # Ensure it's always 3 digits