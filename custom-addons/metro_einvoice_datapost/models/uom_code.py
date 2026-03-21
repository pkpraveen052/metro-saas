from odoo import fields, models, api, _
import logging

_logger = logging.getLogger(__name__)


class UomCode(models.Model):
    _name = "uom.code"
    _description = "Uom code LIst"

    name = fields.Char('Uom Code')
    description = fields.Char("Description")

