from odoo import models, fields, api

class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    @api.model
    def create(self, vals):
        if 'name' in vals and vals.get('name') == 'auth_oauth_provider':
            vals.update({'group_id': False})
        return super(IrModelAccess, self).create(vals)

    @api.model
    def _disable_oauth_access(self):
        if self.env['ir.model.data'].xmlid_to_res_id("auth_oauth.access_auth_oauth_provider"):
            self.env.ref("auth_oauth.access_auth_oauth_provider").write({'group_id': False})