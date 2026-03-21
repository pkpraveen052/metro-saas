# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Menus(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def _update_settings_groups(self):
        """ Sets the important modules of account, sale, purchase, stock, pointofsale.. etc.,
            with the ERP Admin Group access.
        """
        menu_lis = [
            'account.menu_account_config',
            'sale.menu_sale_general_settings',
            'purchase.menu_purchase_general_settings',
            'stock.menu_stock_general_settings',
            'point_of_sale.menu_pos_global_settings'
        ]
        try:
            erpadmin_grp = self.env.ref('metroerp_customizations.sub_admin_group').id
            for menu in menu_lis:
                if self.env['ir.model.data'].xmlid_to_res_id(menu):
                    self.env.ref(menu).write({'groups_id': [(4, erpadmin_grp)]})
        except Exception as e:
            _logger.exception("Error when adding ERP Admin Group to the Menuitems: %s" % e)