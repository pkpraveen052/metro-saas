from odoo import models,fields,api,_
from odoo.exceptions import UserError

class MRPProduction(models.Model):
    _inherit = "mrp.production"


    def action_view_bom_structure(self):
        """Opens the BoM Structure & Cost report with the MO's BoM and correct quantity."""
        self.ensure_one()

        # Retrieve the BoM Report action
        action = self.env.ref('mrp.action_report_mrp_bom')
        if not action:
            raise UserError(_("BoM Report action not found."))

        action = action.read()[0]

        context_data = {
            'active_id': self.bom_id.id,
            'bom_qty': self.product_qty,  # Pass `product_qty` as `bom_qty`
            'mo_id': self.id
        }

        if 'context' in action and isinstance(action['context'], dict):
            action['context'].update(context_data)
        else:
            action['context'] = context_data

        return action
    

    


                
