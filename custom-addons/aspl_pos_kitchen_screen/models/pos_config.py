# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    restaurant_mode = fields.Selection([('full_service', 'Full Service Restaurant (FCS)'),
                                        ('quick_service', 'Fast-Food/Quick Service Restaurant (QSR)')],
                                       "Restaurant Mode", default="full_service")
    # allow_cook_to_open = fields.Boolean("Allow Cook to open a new session") #Metro added
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
