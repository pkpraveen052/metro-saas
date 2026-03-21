# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsersInherited(models.Model):
    _inherit = "res.users"


    def write(self, vals):
        """ Set the Accounting Full Group as False when Billing User is set. """
        for user_field in list(vals):
            data = 'sel_groups_' + str(self.env.ref('metroerp_userguide.manager_sub_admin_group').id) + '_' + str(self.env.ref(
                'metroerp_userguide.admin_sub_admin_group').id)
            if vals[user_field] == self.env.ref('metroerp_userguide.manager_sub_admin_group').id or vals[user_field] == self.env.ref('metroerp_userguide.admin_sub_admin_group').id:
                self.env.ref('metroerp_userguide.all_user_guide_url_groups').write({'users': [(3, self.id)]})
            else:
                if user_field == data and vals[user_field] == False:
                    self.env.ref('metroerp_userguide.all_user_guide_url_groups').write({'users': [(4, self.id)]})
        return super(ResUsersInherited, self).write(vals)
