# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import reports

from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

def pre_init_check_upgrade(cr):
    # Check if the module is already installed
    cr.execute("SELECT state FROM ir_module_module WHERE name = %s", ('ks_dynamic_financial_report',))
    result = cr.fetchone()
    if result and result[0] == 'installed':
        _logger.warning("Upgrade attempt detected on 'ks_dynamic_financial_report'")
        raise UserError("Upgrading this module is not allowed.")
