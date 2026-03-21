# -*- coding: utf-8 -*-
from odoo import fields, models, api

class PosConfig(models.Model):
    _inherit = 'pos.config'

    display_token_no = fields.Boolean(string='Display Token Number', default=False)
     