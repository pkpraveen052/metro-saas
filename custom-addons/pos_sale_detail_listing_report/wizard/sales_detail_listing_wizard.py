# -*- coding: utf-8 -*-

from odoo import models, fields, _, api
from datetime import datetime,date

class SalesDetailListingWizard(models.TransientModel):
    _name = "sales.detail.listing.wizard"
    _description = "Sales Detail Listing Wizard"
    
    from_date = fields.Date(string="Start Date",required=True,default = fields.Date.today)
    to_date = fields.Date(string="End Date",required=True, default = fields.Date.today)
    pos_config_ids = fields.Many2many('pos.config', default=lambda s: s.env['pos.config'].search([]))

    @api.onchange('from_date')
    def _onchange_from_date(self):
        if self.from_date and self.to_date and self.to_date < self.from_date:
            self.to_date = self.from_date

    @api.onchange('to_date')
    def _onchange_to_date(self):
        if self.from_date and self.to_date and self.to_date < self.from_date:
            self.from_date = self.to_date
    
    def print_report(self):
        data = {
            'from_date': self.from_date,
            'to_date': self.to_date,
            'config_ids': self.pos_config_ids.ids
        }
        return self.env.ref('pos_sale_detail_listing_report.action_sale_detail_listing').report_action(None, data=data)
