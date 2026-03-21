from odoo import models,fields,api,_

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"


    def _get_aggregated_product_quantities(self, **kwargs):
        aggregated_move_lines = {}
        for move_line in self:
            name = move_line.product_id.display_name
            product_name = move_line.product_id.name #Only for displaying product name
            description = move_line.move_id.description_picking
            if description == name or description == move_line.product_id.name:
                description = False
            uom = move_line.product_uom_id
            sale_line_id_str = str(move_line.move_id.sale_line_id.id) if move_line.move_id.sale_line_id else "0"
            line_key = sale_line_id_str + "_" + str(move_line.product_id.id) + "_" + name + (description or "") + "uom " + str(uom.id)

            if line_key not in aggregated_move_lines:
                aggregated_move_lines[line_key] = {'name': name,
                                                   'product_name': product_name,
                                                   'description': description,
                                                   'qty_done': move_line.qty_done,
                                                   'product_uom': uom.name,
                                                   'product_uom_rec': uom,
                                                   'product': move_line.product_id,
                                                   'sale_line_id': move_line.move_id.sale_line_id,}
            else:
                aggregated_move_lines[line_key]['qty_done'] += move_line.qty_done
        return aggregated_move_lines
    

class StockMove(models.Model):
    _inherit = "stock.move"

    product_name = fields.Char(string="Product Name")