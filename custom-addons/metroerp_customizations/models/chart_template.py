# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError
from odoo import api, fields, models, _
from odoo import SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.addons.account.models.account_tax import TYPE_TAX_USE

import logging

_logger = logging.getLogger(__name__)

class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        """ Overidden method.
        Installs this chart of accounts on the current company, replacing
        the existing one if it had already one defined. If some accounting entries
        had already been made, this function fails instead, triggering a UserError.

        Also, note that this function can only be run by someone with administration
        rights.
        """
        print("\nCustom _load() >>>>>>>  <<<<<<<< ")
        self.ensure_one()
        super(AccountChartTemplate, self)._load(sale_tax_rate, purchase_tax_rate, company)
        # Metro Custom code
        company.account_sale_tax_id = False
        company.account_purchase_tax_id = False
        # Metro Custom code ends

        return {}