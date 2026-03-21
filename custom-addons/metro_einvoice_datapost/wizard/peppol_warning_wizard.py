# -*- coding: utf-8 -*-
from odoo import fields, models, _


class PeppolWarnigWizard(models.TransientModel):
    _name = 'peppol.warning.wizard'
    _description = 'PEPPOL Warning Wizard'

    message = fields.Text(readonly=True)
