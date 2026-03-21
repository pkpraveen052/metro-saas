from odoo import models,fields,api,_
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _get_buy_route(self):
    	""" Overidden the base method to not set the base record 'purchase_stock.route_warehouse0_buy' as default routes on 
    	the porducts. """
    	buy_route = self.env['stock.location.route'].search([('name','=','Buy')], limit=1)
    	if buy_route:
    		return [buy_route.id]
    	return []