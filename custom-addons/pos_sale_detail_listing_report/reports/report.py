# -*- coding: utf-8 -*-

from odoo import api, models
from datetime import datetime,date,time

class SaleDetailsListing(models.AbstractModel):
    _name = 'report.pos_sale_detail_listing_report.report_saledetailslisting'
    _description = 'Report Sale Details Listing'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['pos.order'].browse(docids)
        from_date = datetime.strptime(data.get('from_date') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
        to_date = datetime.strptime(data.get('to_date') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
        data['from_date'] = from_date
        data['to_date'] = to_date
        configs = self.env['pos.config'].browse(data['config_ids'])
        orders = self.env['pos.order'].search([('date_order','>=',from_date),('date_order','<=',to_date)])
        config_data = {}
        valid_order_ids, valid_total_taxes, valid_amount_total, valid_amount_tot_paid, valid_amount_notax, curr_obj = [], 0.0, 0.0, 0.0, 0.0, self.env.user.company_id.currency_id
        for config in configs:
            sessions = orders.filtered(lambda x:x.config_id.id == config.id).mapped('session_id')
            session_data = {}
            for session in sessions:
                session_orders = orders.filtered(lambda x:x.session_id.id == session.id)
                orders_data = []
                for order in session_orders:
                    currency = order.session_id.currency_id
                    order_lines = [l for l in order.lines]
                    orders_data.append({
                        'order': order,
                        'order_lines': order_lines,
                        'currency': currency
                    })
                    valid_order_ids.append(order.id)
                    valid_total_taxes += order.amount_tax
                    valid_amount_total += order.amount_total
                    valid_amount_tot_paid += order.amount_paid
                    valid_amount_notax += sum(order.lines.mapped('price_subtotal'))
                    curr_obj = currency

                if orders_data:
                    session_data[session] = orders_data
            config_data[config] = {
                'sessions': session_data
            }
        data.update({'config_data': config_data})

        payment_ids = self.env["pos.payment"].sudo().search([('pos_order_id', 'in', valid_order_ids)]).ids
        if payment_ids:
            self.env.cr.execute("""
                SELECT method.name, sum(amount) total
                FROM pos_payment AS payment,
                     pos_payment_method AS method
                WHERE payment.payment_method_id = method.id
                    AND payment.id IN %s
                GROUP BY method.name
            """, (tuple(payment_ids),))
            payments = self.env.cr.dictfetchall()
        else:
            payments = []

        data['currency'] = curr_obj

        return {
              'doc_ids': docs.ids,
              'doc_model': 'pos.order',
              'docs': docs,
              'data': data,
              'total_payments': payments,
              'total_taxes': valid_total_taxes,
              'total_amount': valid_amount_total,
              'total_amount_notax': valid_amount_notax,
              'total_amount_paid': valid_amount_tot_paid,
        }
