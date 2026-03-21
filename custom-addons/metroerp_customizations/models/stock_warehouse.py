# -*- coding: utf-8 -*-
from traceback import print_tb

from odoo import _, _lt, api, fields, models
from odoo.exceptions import UserError



class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    def _check_multiwarehouse_group(self):
        """"method override on warehouse and location group on multi company"""
        cnt_by_company = self.env['stock.warehouse'].sudo().search([('active', '=', True), ('company_id', '=', self.env.company.id)])
        users = self.env['res.users'].sudo().search([('company_ids', 'in', [self.env.company.id])])
        if cnt_by_company:
            max_cnt = len(cnt_by_company)
            group_stock_multi_warehouses = self.env.ref('stock.group_stock_multi_warehouses')
            group_stock_multi_locations = self.env.ref('stock.group_stock_multi_locations')
            if max_cnt <= 1 and self.env.user.has_group('stock.group_stock_multi_warehouses'):
                # group_stock_multi_warehouses.write({'users': [(3, self.env.user.id)]})
                group_stock_multi_warehouses.write({'users': [(3, user.id) for user in users]})
            if max_cnt > 1:
                group_stock_multi_warehouses.write({'users': [(4, user.id) for user in users]})
                group_stock_multi_locations.write({'users': [(4, user.id) for user in users]})
                self.env.company.write({'group_stock_multi_locations': True})
            # if max_cnt > 1:
            #     group_stock_multi_warehouses.write({'users': [(4, self.env.user.id)]})
            #     group_stock_multi_locations.write({'users': [(4, self.env.user.id)]})
            #     self.env.company.write({'group_stock_multi_locations': True})

            # max_cnt = max(cnt_by_company, key=lambda k: k['company_id_count'])
            # group_user = self.env.ref('base.group_user')
            # if max_cnt['company_id_count'] <= 1 and group_stock_multi_warehouses in group_user.implied_ids:
            #     group_user.write({'implied_ids': [(3, group_stock_multi_warehouses.id)]})
            #     group_stock_multi_warehouses.write({'users': [(3, user.id) for user in group_user.users]})
            # if max_cnt['company_id_count'] > 1 and group_stock_multi_warehouses not in group_user.implied_ids:
            #     group_user.write({'implied_ids': [(4, group_stock_multi_warehouses.id), (4, self.env.ref('stock.group_stock_multi_locations').id)]})
