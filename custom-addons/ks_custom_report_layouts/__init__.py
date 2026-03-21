# -*- coding: utf-8 -*-

from odoo.api import Environment, SUPERUSER_ID
from . import models
from . import report


app_id = []
def ks_report_uninstall_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    module_list = ['sale', 'purchase', 'account', 'stock']
    for rec in module_list:
        app = env['ir.module.module'].search([('name', 'ilike', rec)], limit=1)[0]
        if app.id not in app_id:
            app_id.append(app.id)
            app.button_immediate_upgrade()