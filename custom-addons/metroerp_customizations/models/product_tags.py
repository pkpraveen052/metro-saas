from random import randint
from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError

class ProductTags(models.Model):
	_name = "product.tags"
	_description = "Product Tags"
	_order = 'sequence'

	def _get_default_color(self):
		return randint(1, 11)
	
	sequence = fields.Integer(string='Sequence')	
	name = fields.Char(string='Tag Name', required=True, index=True)
	color = fields.Integer('Color', default=_get_default_color)
	company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id)
	product_ids = fields.Many2many('product.template', string='Products', ondelete='cascade',domain="[('company_id', '=', company_id)]")


	_sql_constraints = [
        ('name_company_uniq', 'unique (name,company_id)', 'Tag name must be unique!')
    ]
