from odoo import models,api,fields,_
from lxml import etree


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(SaleOrder, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )

        user = self.env.user

        if view_type == 'form':
            if user.has_group('sales_team.group_sale_salesman') \
               and not user.has_group('sales_team.group_sale_salesman_all_leads') \
               and not user.has_group('sales_team.group_sale_manager'):

                doc = etree.XML(res['arch'])

                domain = "['|', ('user_id','=',uid), ('user_id','=',False), ('company_id','in',allowed_company_ids)]"

                # Apply domain to all three partner fields
                for node in doc.xpath("//field[@name='partner_id'] | //field[@name='partner_invoice_id'] | //field[@name='partner_shipping_id']"):
                    node.set('domain', domain)

                res['arch'] = etree.tostring(doc, encoding='unicode')

        return res