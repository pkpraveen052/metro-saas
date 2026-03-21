# -*- coding: utf-8 -*-

from odoo import fields,api,models,_

class ResCompany(models.Model):
	_inherit = 'res.company'
	
	low_stock_alert_qty = fields.Float('')

	expiry_alert_days = fields.Integer(
        string="Expiry Alert Days",
        default=30,
        help="Alert X days before product expiry"
    )

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	low_stock_alert_qty = fields.Float(related="company_id.low_stock_alert_qty", store=True, readonly=False)
	expiry_alert_days = fields.Integer(related="company_id.expiry_alert_days", store=True, readonly=False)