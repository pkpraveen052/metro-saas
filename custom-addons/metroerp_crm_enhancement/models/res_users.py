# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    def default_enable_crm(self):
        if self.env.user.has_group('base.group_system') or (self.env.user.has_group('metroerp_customizations.sub_admin_group') and self.env.user.has_group('metroerp_crm_enhancement.group_crm_manager')):
            return True
        else:
            return False

    enable_crm = fields.Boolean(compute='_compute_enable_crm', string='Enable CRM' ,default=default_enable_crm)

    def _compute_enable_crm(self):
        for obj in self:
            if self.env.user.has_group('base.group_system') or (self.env.user.has_group('metroerp_customizations.sub_admin_group') and self.env.user.has_group('metroerp_crm_enhancement.group_crm_manager')):
                obj.enable_crm = True
            else:
                obj.enable_crm = False
