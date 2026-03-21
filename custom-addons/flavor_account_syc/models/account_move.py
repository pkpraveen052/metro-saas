# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    flavor_ref_no = fields.Char(string="Flavor Ref No.", readonly=True, copy=False)

    @api.constrains('flavor_ref_no')
    def _check_unique_field(self):
        for record in self.filtered(lambda x: x.flavor_ref_no != False):
            if self.search_count([('flavor_ref_no', '=', record.flavor_ref_no)]) > 1:
                raise ValidationError("Flavor Ref No. must be unique.")



class AccountPayment(models.Model):
    _inherit = "account.payment"

    flavor_ref_no = fields.Char(string="Flavor Ref No.", readonly=True)

    @api.constrains('flavor_ref_no')
    def _check_unique_field(self):
        for record in self.filtered(lambda x: x.flavor_ref_no != False):
            if self.search_count([('flavor_ref_no', '=', record.flavor_ref_no)]) > 1:
                raise ValidationError("Flavor Ref No. must be unique.")