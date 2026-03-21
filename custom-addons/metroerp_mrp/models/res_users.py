# -*- coding: utf-8 -*-
from odoo import fields, models, api
import re


class ResUsers(models.Model):
    _inherit = 'res.users'

    def default_enable_mrp(self):
        if self.env.user.has_group('base.group_system') or (self.env.user.has_group('metroerp_customizations.sub_admin_group') and self.env.user.has_group('mrp.group_mrp_manager')):
            return True
        else:
            return False

    enable_mrp = fields.Boolean(compute = '_compute_enable_mrp', string = 'Enable MRP', default = default_enable_mrp)

    def _compute_enable_mrp(self):
        for obj in self:
            if self.env.user.has_group('base.group_system') or (self.env.user.has_group('metroerp_customizations.sub_admin_group') and self.env.user.has_group('mrp.group_mrp_manager')):
                obj.enable_mrp = True
            else:
                obj.enable_mrp = False


    def write(self, vals):
        res = super(ResUsers, self).write(vals)
        print("\n\nvals ======",vals)
        # Check if groups are updated
        for a,b in vals.items():
            match = re.search(r'sel_groups_([\d_]+)', a)
            if match:
                manufacturing_grp_ids = [self.env.ref('mrp.group_mrp_manager').id, self.env.ref('mrp.group_mrp_user').id]
                if vals[a] in manufacturing_grp_ids:
                    for user in self:
                        if not self.env['stock.location.route'].sudo().search([('name','=','Manufacture'),('company_id','=',user.company_id.id)]):
                            route_obj = self.env['stock.location.route'].sudo().create({
                                'name': 'Manufacture',
                                'sequence': 5,
                                'company_id': user.company_id.id
                            })
                            print(route_obj)
                            print(self.env['stock.warehouse'].search([('company_id','=',user.company_id.id)]))
                            for warehouse_obj in self.env['stock.warehouse'].sudo().search([('company_id','=',user.company_id.id)]):
                                print("warehouse_obj========",warehouse_obj)
                                location_id = warehouse_obj.manufacture_steps == 'pbm_sam' and warehouse_obj.sam_loc_id or warehouse_obj.lot_stock_id
                                route_obj.sudo().write({
                                    'rule_ids': [(0,0,
                                        {
                                            'action': 'manufacture',
                                            'procure_method': 'make_to_order',
                                            'company_id': user.company_id.id,
                                            'picking_type_id': warehouse_obj.manu_type_id.id,
                                            'route_id': route_obj.id,
                                            'active': warehouse_obj.manufacture_to_resupply,
                                            'name': warehouse_obj._format_rulename(location_id, False, 'Production'),
                                            'location_id': location_id.id,
                                            'propagate_cancel': warehouse_obj.manufacture_steps == 'pbm_sam',
                                            'warehouse_id': warehouse_obj.id
                                        })]
                                    })
                    break
        return res

    @api.model
    def create(self, vals):
        res = super(ResUsers, self).create(vals)
        print("\n\nvals ======",vals)
        # Check if groups are updated
        for a,b in vals.items():
            match = re.search(r'sel_groups_([\d_]+)', a)
            print("match ==",match)
            if match:
                manufacturing_grp_ids = [self.env.ref('mrp.group_mrp_manager').id, self.env.ref('mrp.group_mrp_user').id]
                if vals[a] in manufacturing_grp_ids:
                    print("Found....",res)
                    for user in res:
                        print(self.env['stock.location.route'].sudo().search([('name','=','Manufacture'),('company_id','=',res.company_id.id)]))
                        if not self.env['stock.location.route'].sudo().search([('name','=','Manufacture'),('company_id','=',res.company_id.id)]):
                            route_obj = self.env['stock.location.route'].sudo().create({
                                'name': 'Manufacture',
                                'sequence': 5,
                                'company_id': res.company_id.id
                            })
                            print(route_obj)
                            print(self.env['stock.warehouse'].search([('company_id','=',res.company_id.id)]))
                            for warehouse_obj in self.env['stock.warehouse'].sudo().search([('company_id','=',res.company_id.id)]):
                                print("warehouse_obj========",warehouse_obj)
                                location_id = warehouse_obj.manufacture_steps == 'pbm_sam' and warehouse_obj.sam_loc_id or warehouse_obj.lot_stock_id
                                route_obj.sudo().write({
                                    'rule_ids': [(0,0,
                                        {
                                            'action': 'manufacture',
                                            'procure_method': 'make_to_order',
                                            'company_id': res.company_id.id,
                                            'picking_type_id': warehouse_obj.manu_type_id.id,
                                            'route_id': route_obj.id,
                                            'active': warehouse_obj.manufacture_to_resupply,
                                            'name': warehouse_obj._format_rulename(location_id, False, 'Production'),
                                            'location_id': location_id.id,
                                            'propagate_cancel': warehouse_obj.manufacture_steps == 'pbm_sam',
                                            'warehouse_id': warehouse_obj.id
                                        })]
                                    })
                    break
        return res