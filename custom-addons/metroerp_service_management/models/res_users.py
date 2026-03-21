# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    def default_enable_service(self):
        if self.env.user.has_group('base.group_system') or (self.env.user.has_group('metroerp_customizations.sub_admin_group') and self.env.user.has_group('metroerp_service_management.service_management_group_administrator')):
            return True
        else:
            return False

    enable_service = fields.Boolean(compute='_compute_enable_service', string='Enable Service' ,default=default_enable_service)

    def _compute_enable_service(self):
        if self.env.user.has_group('base.group_system') or (self.env.user.has_group('metroerp_customizations.sub_admin_group') and self.env.user.has_group('metroerp_service_management.service_management_group_administrator')):
            self.enable_service = True
        else:
            self.enable_service = False
