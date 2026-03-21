import base64
import hashlib
import hmac
import json
import logging
import requests
import traceback
from collections import defaultdict
from odoo.exceptions import ValidationError

from odoo import api, models, fields, _
from odoo.addons.iap.tools.iap_tools import InsufficientCreditError

logger = logging.getLogger(__name__)


class PeppolQueueC5In(models.Model):
    _name = "peppol.queue.c5.in"
    _description = "Incoming Invoices/Credit Notes Queue"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date desc, id desc"

    name = fields.Char(string="Name", compute="_compute_name", store=True)