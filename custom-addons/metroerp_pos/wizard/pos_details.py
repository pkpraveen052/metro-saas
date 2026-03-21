# -*- coding: utf-8 -*-
import pytz

from odoo import api, fields, models, tools, _


class PosDetails(models.TransientModel):
    _inherit = 'pos.details.wizard'

    paper_type = fields.Selection([
        ('Thermal Printer', 'Thermal Print'),
        ('A4 Size Print', 'A4 Size Print')
    ], default='A4 Size Print', string='Paper Type')

    def generate_report(self):
        data = {'date_start': self.start_date, 'date_stop': self.end_date, 'config_ids': self.pos_config_ids.ids, 'paper_type': self.paper_type}
        if self.paper_type == 'Thermal Printer':
            return self.env.ref('point_of_sale.sale_details_report').report_action([], data=data)
        else:
            data = self.env['report.point_of_sale.report_saledetails']._get_report_values(docids=None, data=data)
            return self.env.ref('metroerp_pos.sale_details_report_custom').report_action([], data=data)