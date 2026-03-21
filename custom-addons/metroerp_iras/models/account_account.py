# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountAccount(models.Model):
    _inherit = "account.account"

    iras_mapping_ids = fields.Many2many('iras.coa.mapping', string="IRAS Mapping")

    _sql_constraints = [
        ('check_name_code_company', 'UNIQUE(name,code,company_id)', "The Name must be unique"),
    ]
