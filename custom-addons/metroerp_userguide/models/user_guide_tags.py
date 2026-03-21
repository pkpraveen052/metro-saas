# -*- coding: utf-8 -*-

from odoo import api, fields, models


class UserGuideTags(models.Model):
    _name = "user.guide.tags"
    _description = "User Guide Tags"

    name = fields.Char(string='Tags')

