from odoo import models,fields,api,_


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    def _get_global_route_rules_values(self):
        print("\nCUSTOM >>> _get_global_route_rules_values() >>>>>>")
        ctx = self._context or {}
        rule_data = super(StockWarehouse, self)._get_global_route_rules_values()
        # print("\nCUSTOM....rule_data ===",rule_data)
        route_pool = self.env['stock.location.route']

        buy_route_id = route_pool.sudo().search([('company_id','=',self.company_id.id),('name','=','Buy')], limit=1) or False
        print("buy_route_id ==",buy_route_id)
        if not buy_route_id:
            buy_route_id = route_pool.sudo().create({
                'name': 'Buy',
                'company_id': self.company_id.id,
            }).id
        else:
            buy_route_id = buy_route_id.id

        mto_route_id = route_pool.sudo().search([('company_id','=',self.company_id.id),('name','=','Replenish on Order (MTO)')], limit=1)
        print(route_pool.sudo().search([('name','=','Replenish on Order (MTO)'),('company_id','=',self.company_id.id)]))
        print("mto_route_id ==",mto_route_id)
        if not mto_route_id and 'active_test' in ctx:
            print("CREATINGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG MTOOOOOOOOOOO")
            mto_route_id = route_pool.sudo().with_context({'no_mto_create': True}).create({
                'name': 'Replenish on Order (MTO)',
                'company_id': self.company_id.id,
                'active': False,
                'sequence': 5,
                'sale_selectable': True
            }).id
        else:
            mto_route_id = mto_route_id.id

        print(self._context)
        manufacture_route_id = route_pool.sudo().search([('name','=','Manufacture'),('company_id','=',self.company_id.id)], limit=1)
        print("manufacture_route_id ==",manufacture_route_id)
        if not manufacture_route_id:
            manufacture_route_id = route_pool.sudo().create({
                'name': 'Manufacture',
                'sequence': 5,
                'company_id': self.company_id.id
            })
        else:
            manufacture_route_id = manufacture_route_id.id

        for key, val in rule_data.items():
            if key == 'buy_pull_id':
                val['create_values']['route_id'] = buy_route_id
            elif key == 'mto_pull_id' and mto_route_id:
                val['create_values']['route_id'] = mto_route_id
            elif key == 'manufacture_pull_id':
                val['create_values']['route_id'] = manufacture_route_id
            elif key == 'manufacture_mto_pull_id':
                val['create_values']['route_id'] = buy_route_id
            elif key == 'pbm_mto_pull_id' and mto_route_id:
                val['create_values']['route_id'] = mto_route_id
            elif key == 'sam_rule_id':
                val['create_values']['route_id'] = manufacture_route_id


        # print("\nFINALLY.....rule_data ===",rule_data)
        return rule_data
            


        # rules.update({
        #     'buy_pull_id': {
        #         'depends': ['reception_steps', 'buy_to_resupply'],
        #         'create_values': {
        #             'action': 'buy',
        #             'picking_type_id': self.in_type_id.id,
        #             'group_propagation_option': 'none',
        #             'company_id': self.company_id.id,
        #             'route_id': self._find_global_route('purchase_stock.route_warehouse0_buy', _('Buy')).id,
        #             'propagate_cancel': self.reception_steps != 'one_step',
        #         },
        #         'update_values': {
        #             'active': self.buy_to_resupply,
        #             'name': self._format_rulename(location_id, False, 'Buy'),
        #             'location_id': location_id.id,
        #             'propagate_cancel': self.reception_steps != 'one_step',
        #         }
        #     }
        # })
        # return rules