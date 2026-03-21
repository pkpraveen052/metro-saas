# -*- coding: utf-8 -*-
from odoo import fields, models, _


class PeppolIdentofierWizard(models.TransientModel):
    _name = 'peppol.identifier.wizard'
    _description = 'PEPPOL Identifier Message Wizard'

    message = fields.Text(string="Message", readonly=True)

    def button_send(self):
        return
