# -*- coding: utf-8 -*-
from odoo import api, models, tools, fields, _
from odoo.exceptions import UserError

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def default_get(self, fields):
        if self.env.user.has_group('metroerp_saas_customization.accounting_partner') and self.env.user.company_id.id != self.env.company.id:
            raise UserError("You are not allowed to create a new user for this Company")

        # restrict_group = self.env.ref('your_module.group_restrict_user', raise_if_not_found=False)
        # Check if the current user belongs to the "Restrict User" group
        if self.env.user.has_group('metroerp_saas_customization.group_restrict_user'):
            raise UserError(_("You cannot perform this action to create. Please contact Metro Supprt Team to create the new User. Thank you"))
        defaults = super(ResUsers, self).default_get(fields)
        return defaults

    def default_enable_ap(self):
        if self.env.user.has_group('base.group_system') or (self.env.user.has_group('metroerp_customizations.sub_admin_group') and self.env.user.has_group('metroerp_saas_customization.accounting_partner')):
            return True
        else:
            return False

    def default_restrict_ap(self):
        if self.env.user.has_group('base.group_system'):
            return True
        else:
            return False

    enable_ap = fields.Boolean(compute='_compute_enable_ap', string='Enable AP' ,default=default_enable_ap)
    restrict_ap = fields.Boolean(compute='_compute_restrict_ap', string='Restrict AP' ,default=default_restrict_ap)


    def _compute_enable_ap(self):
        for obj in self:
            if self.env.user.has_group('base.group_system') or (self.env.user.has_group('metroerp_customizations.sub_admin_group') and self.env.user.has_group('metroerp_saas_customization.accounting_partner')):
                obj.enable_ap = True
            else:
                obj.enable_ap = False

    def _compute_restrict_ap(self):
        for obj in self:
            if self.env.user.has_group('base.group_system'):
                obj.restrict_ap = True
            else:
                obj.restrict_ap = False

    @api.model
    def create(self, vals):
        print(self.env.user.company_id.id)
        if self.env.user.has_group('metroerp_saas_customization.accounting_partner') and self.env.user.company_id.id != self.env.company.id:
            raise UserError("You are not allowed to create a new user for this Company")
        else:
            return super(ResUsers, self).create(vals)
