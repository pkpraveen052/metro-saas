from odoo import models,fields,api,_


class ResCompany(models.Model):
    _inherit = "res.company"

    use_manufacturing_lead = fields.Boolean(
        'Default Manufacturing Lead Time')

    def action_update_buy_route_products(self, name=''):
        """Called from Server Action."""
        print("\n\nCalled .... action_update_buy_route_products()  self", self, name)
        route_pool = self.env['stock.location.route']
        rule_pool = self.env['stock.rule']
        product_temp_pool = self.env['product.template']
        if name == 'Buy':
            for obj in self:
                route_obj = route_pool.sudo().search([('company_id','=',obj.id),('name','=','Buy')], limit=1)
                print("route_obj ==",route_obj)
                product_ids = product_temp_pool.sudo().search([('company_id','=',obj.id)]) or False
                print("product_ids ==",product_ids)
                if product_ids:
                    for product in product_ids:
                        self.env.cr.execute("""
                            INSERT INTO stock_route_product (product_id, route_id)
                            VALUES (%s, %s)
                        """, (product.id, route_obj.id))

                product_ids2 = product_temp_pool.sudo().search([('company_id','=',obj.id),('active','=',False)]) or False
                print("product_ids2 ==",product_ids2)
                if product_ids2:
                    for product in product_ids2:
                        self.env.cr.execute("""
                            INSERT INTO stock_route_product (product_id, route_id)
                            VALUES (%s, %s)
                        """, (product.id, route_obj.id))

    def action_create_replace_routes_rules(self, name=''):
        """Called from Server Action."""
        print("\n\nCalled .... action_create_replace_routes_rules()  self", self, name)
        route_pool = self.env['stock.location.route']
        rule_pool = self.env['stock.rule']

        if name == 'Buy':
            base_buy_obj = self.env.ref('purchase_stock.route_warehouse0_buy')
            for obj in self:
                if obj.id == 1:
                    continue
                if not route_pool.sudo().search([('company_id','=',obj.id),('name','=','Buy')]):
                    route_obj = route_pool.sudo().create({
                        'name': 'Buy',
                        'company_id': obj.id,
                        })
                    print("\nCreated new Route BUY = ",obj.id, " ", obj.name)

                    for ruleobj in rule_pool.sudo().search([('route_id','=',base_buy_obj.id),('company_id','=',obj.id)]):
                        ruleobj.sudo().write({'route_id': route_obj.id})
                        print(".....UNLINKING AND TAGGING")
                    print("--> NEW route_obj.RULES = ",route_obj.rule_ids)
        elif name == 'Replenish on Order (MTO)':
            base_mto_obj = self.env.ref('stock.route_warehouse0_mto')
            for obj in self:
                if obj.id == 1:
                    continue
                if not route_pool.sudo().search([('company_id','=',obj.id),('name','=','Replenish on Order (MTO)'),('active','in',[True,False])]):
                    route_obj = route_pool.sudo().create({
                        'name': 'Replenish on Order (MTO)',
                        'company_id': obj.id,
                        'active': False,
                        'sequence': 5,
                        'sale_selectable': True
                        })
                    print("\nCreated new Route Replenish on Order (MTO) = ",obj.id, " ", obj.name)

                    for ruleobj in rule_pool.sudo().search([('route_id','=',base_mto_obj.id),('company_id','=',obj.id)]):
                        ruleobj.sudo().write({'route_id': route_obj.id})
                        print(".....UNLINKING AND TAGGING")
                    print("--> NEW route_obj.RULES = ",route_obj.rule_ids)


    

    


                
