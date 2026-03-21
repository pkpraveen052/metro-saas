# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    adjust_in_carry_fwd_bal = fields.Boolean('Adjust in Carry Forward Balance', track_visibility=True)
    offset_carry_fwd_bal_date = fields.Date('Offset Date', track_visibility=True)

    @api.onchange('adjust_in_carry_fwd_bal')
    def onchange_adjust_in_carry_fwd_bal(self):
        if self.adjust_in_carry_fwd_bal:
            self.offset_carry_fwd_bal_date = str(self.date)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.offset_carry_fwd_bal_date and res.offset_carry_fwd_bal_date:
            res.move_id.write({'invoice_date': str(res.offset_carry_fwd_bal_date)})
        return res

    def write(self, vals):
        res = super(AccountPayment, self).write(vals)
        if 'offset_carry_fwd_bal_date' in vals and vals.get('offset_carry_fwd_bal_date'):
            for obj in self:
                obj.move_id.write({'invoice_date': str(obj.offset_carry_fwd_bal_date)})
        return res