# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import AccessError, UserError
import secrets
import random
import string

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    flavor_apikey = fields.Char(string="API Key", related='company_id.flavor_apikey', size=16, readonly=True)
    flavor_apisecret = fields.Char(string="API Secret", related='company_id.flavor_apisecret', size=32, readonly=True)
    enable_flavor_sync = fields.Boolean(related="company_id.enable_flavor_sync", string="Enable Flavor Sync", readonly=False)

    @api.onchange('enable_flavor_sync')
    def onchange_flavor_sync(self):
        if self.enable_flavor_sync == False:
            self.flavor_apikey = False
            self.flavor_apisecret = False

    def set_values(self):
        print("\nset_values() >>>>>",self, self.company_id.name)
        super(ResConfigSettings, self).set_values()
        print("self.enable_flavor_sync ==",self.enable_flavor_sync)
        if self.enable_flavor_sync == False:
            self.write({
                'flavor_apikey': False,
                'flavor_apisecret': False
                })
        if self.enable_flavor_sync:
            self.env.user.sudo().write({
                'groups_id': [(4, self.env.ref('flavor_account_syc.group_flavor_sync').id)]
            })
        else:
            self.env.user.sudo().write({
                'groups_id': [(3, self.env.ref('flavor_account_syc.group_flavor_sync').id)]
            })


    def action_auto_generate(self):
        self.company_id.write({
            'flavor_apikey': secrets.token_hex(16),
            'flavor_apisecret': ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32)),
        })

    def action_regenerate(self):
        self.company_id.write({
            'flavor_apikey': secrets.token_hex(16),
            'flavor_apisecret': ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32)),
        })

