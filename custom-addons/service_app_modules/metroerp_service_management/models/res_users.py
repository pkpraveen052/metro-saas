# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    def default_enable_service(self):
        if self.env.user.has_group('base.group_system') or self.env.user.has_group('metroerp_service_management.group_service_management_admin') or self.env.user.has_group('metroerp_service_management.group_service_management_user_read') or self.env.user.has_group('metroerp_service_management.group_service_management_user_own'):
            return True
        else:
            return False

    enable_service = fields.Boolean(compute='_compute_enable_service', string='Enable Service' ,default=default_enable_service)

    def _compute_enable_service(self):
        if self.env.user.has_group('base.group_system') or self.env.user.has_group('metroerp_service_management.group_service_management_admin') or self.env.user.has_group('metroerp_service_management.group_service_management_user_read') or self.env.user.has_group('metroerp_service_management.group_service_management_user_own'):
            self.enable_service = True
        else:
            self.enable_service = False
