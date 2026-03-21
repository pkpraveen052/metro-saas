from odoo import fields, models, api, _
import logging

_logger = logging.getLogger(__name__)


class MinistriesStatuaryBoards(models.Model):
    _name = "ministries.statuary.boards"
    _description = "List of Ministries / Statutory Boards"
    _rec_name = "business_unit"

    ministry_statutory_board = fields.Char(string='Ministry / Statutory Board')
    department = fields.Char(string='Department')
    business_unit = fields.Char(string='BUSINESS Unit')
    business_unit_code = fields.Char(string='Code', compute='_compute_business_unit_code', store=True)

    @api.depends('business_unit')
    def _compute_business_unit_code(self):
        for rec in self:
            if rec.business_unit:
                rec.business_unit_code = rec.business_unit.split('-')[0].strip()
            else:
                rec.business_unit_code = False




