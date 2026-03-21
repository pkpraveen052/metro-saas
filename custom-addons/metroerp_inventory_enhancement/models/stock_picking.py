from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_reset_to_draft(self):
        for picking in self:
            # Reset stock moves to draft
            if picking.state == 'assigned':
                picking.do_unreserve()  # Unreserve the stock
            for move in picking.move_ids_without_package:
                move.write({'state': 'draft'})
                
                # If move lines exist, reset them to draft too
                for move_line in move.move_line_ids:
                    move_line.write({'state': 'draft'})
            
            # Optionally also reset the picking state
            picking.write({'state': 'draft'})
