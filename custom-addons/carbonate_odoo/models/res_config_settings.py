# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import AccessError, UserError
import secrets
import random
import string

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    carbonate_token = fields.Char(related="company_id.carbonate_token", string="Token", readonly=False)
    enable_carbonate_sync = fields.Boolean(related="company_id.enable_carbonate_sync", string="Enable Carbonate Sync", readonly=False)


    @api.onchange('enable_carbonate_sync')
    def onchange_carbonate_sync(self):
        if self.enable_carbonate_sync == False:
            self.carbonate_token = False



    def action_auto_generate_token(self):
        self.company_id.write({
            'carbonate_token': ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32)),
        })

    def action_regenerate_token(self):
        self.company_id.write({
            'carbonate_token': ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32)),
        })

