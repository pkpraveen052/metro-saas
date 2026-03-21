# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################
from odoo import fields, models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    pos_logo = fields.Binary()
    show_logo_on_receipt = fields.Boolean(string="Show Logo on Receipt", default=True)