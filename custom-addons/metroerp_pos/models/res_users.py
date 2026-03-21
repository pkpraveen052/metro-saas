# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    def default_enable_pos(self):
        if self.env.user.has_group('base.group_system') or (self.env.user.has_group('metroerp_customizations.sub_admin_group') and self.env.user.has_group('point_of_sale.group_pos_manager')):
            return True
        else:
            return False

    enable_pos = fields.Boolean(compute='_compute_enable_pos', string='Enable POS' ,default=default_enable_pos)

    def _compute_enable_pos(self):
        for obj in self:
            if self.env.user.has_group('base.group_system') or (self.env.user.has_group('metroerp_customizations.sub_admin_group') and self.env.user.has_group('point_of_sale.group_pos_manager')):
                obj.enable_pos = True
            else:
                obj.enable_pos = False
