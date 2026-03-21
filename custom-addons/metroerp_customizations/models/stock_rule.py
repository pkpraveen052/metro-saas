from odoo import models,fields,_,api


class StockRule(models.Model):
    _inherit = 'stock.rule'

    # Overidden Method
    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        ''' Returns a dictionary of values that will be used to create a stock move from a procurement.
        This function assumes that the given procurement has a rule (action == 'pull' or 'pull_push') set on it.

        :param procurement: browse record
        :rtype: dictionary
        '''
        # Calling super to get the original move values
        move_values = super(StockRule, self)._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
        if company_id.delivery_product_description:
            # Modify the picking_description value
            sale_line = self.env['sale.order.line'].browse(values.get('sale_line_id'))
            picking_description = sale_line.name if sale_line else ""
            if values.get('product_description_variants'):
                picking_description += values['product_description_variants']

            # Update the move_values dictionary with the modified picking_description
            move_values.update({'description_picking': picking_description})

        return move_values
