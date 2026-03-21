# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
import tempfile
import binascii
from odoo.tools.translate import _
from datetime import datetime


class FormCSPartBcheck(models.TransientModel):
    _name = "formcs.partb.check"
    _description = "FormCS Part B check"

    is_produced = fields.Boolean('Is Produced')
    form_cs_id = fields.Many2one('form.cs', string="Form CS")
    message = fields.Html('Detail')

    def proceed_data_partb(self):
        res = self.form_cs_id.action_perform_corppass()
        return res

