# -*- coding: utf-8 -*-
from odoo import models, fields, api


class OutgoingMailServerInherited(models.Model):
    _inherit = 'ir.mail_server'

    smtp_user = fields.Char(string='Username', help="Optional username for SMTP authentication",
                            groups='base.group_system,metroerp_customizations.sub_admin_group')
    smtp_pass = fields.Char(string='Password', help="Optional password for SMTP authentication",
                            groups='base.group_system,metroerp_customizations.sub_admin_group')
