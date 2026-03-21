# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from calendar import monthrange

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import format_date
from odoo.tools import date_utils


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    totals_below_sections = fields.Boolean(related='company_id.totals_below_sections', string='Add totals below sections', readonly=False,
                                           help='When ticked, totals and subtotals appear below the sections of the report.')