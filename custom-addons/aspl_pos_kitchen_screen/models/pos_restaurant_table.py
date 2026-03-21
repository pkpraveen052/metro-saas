from odoo import models, fields, api, _

class POSRestaurantTable(models.Model):
    _inherit = 'restaurant.table'
    _description = 'Restaurant Table'

    @api.model
    def create_from_ui(self, table):
        """Create or modify a table from the point of sale UI.
        Handles both list ([id, name]) and int floor_id formats safely.
        """
        floor_id = table.get('floor_id')
        if floor_id:
            # ✅ handle both cases safely
            if isinstance(floor_id, (list, tuple)):
                table['floor_id'] = floor_id[0]
            elif isinstance(floor_id, int):
                table['floor_id'] = floor_id

        table_id = table.pop('id', False)
        if table_id:
            self.browse(table_id).write(table)
        else:
            table_id = self.create(table).id
        return table_id


