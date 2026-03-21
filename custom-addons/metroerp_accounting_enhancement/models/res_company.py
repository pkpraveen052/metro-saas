# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import date_utils
from odoo.tools.misc import format_date

class ResCompany(models.Model):
    _inherit = "res.company"

    totals_below_sections = fields.Boolean(
        string='Add totals below sections',
        help='When ticked, totals and subtotals appear below the sections of the report.')