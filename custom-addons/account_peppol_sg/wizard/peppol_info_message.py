# -*- coding: utf-8 -*-
from odoo import fields, models, _
import requests
from datetime import datetime


class PeppolInfoMessage(models.TransientModel):
    _name = 'peppol.info.message'
    _description = "Show Message"

    message = fields.Text('Message', required=True)

    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}
