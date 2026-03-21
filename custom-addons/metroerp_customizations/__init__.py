# -*- coding: utf-8 -*-

from . import controllers
from . import models
from . import report
from . import wizard

from odoo import api, SUPERUSER_ID

def install_metrogroup_customizations(cr):
    """While installing Metrogroup customization module unlink the system parameter for hiding digest checkbox in General Settings"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    system_parameter = env['ir.config_parameter'].sudo().search([('key','=','digest.default_digest_emails')])
    digest = env['digest.digest'].sudo().search([])
    if system_parameter:
        for record in system_parameter:
            record.sudo().unlink()
    if digest :
        for rec in digest:
            rec.write({'state':'deactivated'})
    return True
