from odoo import api, fields, models, _
from odoo.exceptions import UserError

class UoMMergeAutomaticWizard(models.TransientModel):
    _name = 'uom.merge.automatic.wizard'
    _description = 'Merge UoM Wizard'

    uom_ids = fields.Many2many(
        'uom.uom',
        'uom_merge_automatic_wizard_uom_uom_rel',
        'uom_merge_automatic_wizard_id',
        'uom_uom_id',
        string='Units of Measure to Merge'
    )

    dst_uom_id = fields.Many2one(
        'uom.uom',
        string='Destination UoM',
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            # remove duplicates to avoid unique constraint error
            res['uom_ids'] = [(6, 0, list(set(active_ids)))]
        return res


    def action_merge(self):
        self.ensure_one()
        if not self.uom_ids:
            raise UserError(_("Please select at least one UoM to merge."))

        uoms_to_merge = self.uom_ids - self.dst_uom_id

        if not uoms_to_merge:
            raise UserError(_("You must select at least one UoM different from the destination."))

        for uom in uoms_to_merge:
            # --- Update Product Templates everywhere ---
            self._cr.execute("""
                UPDATE product_template
                SET uom_id = %s, uom_po_id = %s
                WHERE uom_id = %s OR uom_po_id = %s
            """, (self.dst_uom_id.id, self.dst_uom_id.id, uom.id, uom.id))

            # --- Update Purchase Order Lines ---
            self._cr.execute("""
                UPDATE purchase_order_line
                SET product_uom = %s
                WHERE product_uom = %s
            """, (self.dst_uom_id.id, uom.id))

            # --- Update Sales Order Lines ---
            self._cr.execute("""
                UPDATE sale_order_line
                SET product_uom = %s
                WHERE product_uom = %s
            """, (self.dst_uom_id.id, uom.id))

            # --- Update Sales Order Options ---
            self._cr.execute("""
                UPDATE sale_order_option
                SET uom_id = %s
                WHERE uom_id = %s
            """, (self.dst_uom_id.id, uom.id))

            # --- Update Invoice Lines ---
            self._cr.execute("""
                UPDATE account_move_line
                SET product_uom_id = %s
                WHERE product_uom_id = %s
            """, (self.dst_uom_id.id, uom.id))

            # --- Update Stock Moves ---
            self._cr.execute("""
                UPDATE stock_move
                SET product_uom = %s
                WHERE product_uom = %s
            """, (self.dst_uom_id.id, uom.id))

            # --- Update Stock Move Lines ---
            self._cr.execute("""
                UPDATE stock_move_line
                SET product_uom_id = %s
                WHERE product_uom_id = %s
            """, (self.dst_uom_id.id, uom.id))

            # --- Update Bill of Materials (BoM) ---
            self._cr.execute("""
                UPDATE mrp_bom
                SET product_uom_id = %s
                WHERE product_uom_id = %s
            """, (self.dst_uom_id.id, uom.id))

            # --- Update BoM Lines ---
            self._cr.execute("""
                UPDATE mrp_bom_line
                SET product_uom_id = %s
                WHERE product_uom_id = %s
            """, (self.dst_uom_id.id, uom.id))

            # --- Update Manufacturing Orders ---
            self._cr.execute("""
                UPDATE mrp_production
                SET product_uom_id = %s
                WHERE product_uom_id = %s
            """, (self.dst_uom_id.id, uom.id))

            # --- Clean cache for ORM sync ---
            self.env.clear()

            # --- Finally delete merged uom ---
            uom.unlink()

        return {'type': 'ir.actions.act_window_close'}



