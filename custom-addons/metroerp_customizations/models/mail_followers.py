from odoo import _, api, fields, models


class Followers(models.Model):
    _inherit = 'mail.followers'

    @api.depends('partner_id', 'channel_id')
    def _compute_related_fields(self):
        for follower in self.sudo():
            if follower.partner_id:
                follower.name = follower.partner_id.name
                follower.email = follower.partner_id.email
                follower.is_active = follower.partner_id.active
            else:
                follower.name = follower.channel_id.name
                follower.is_active = bool(follower.channel_id)
                follower.email = False