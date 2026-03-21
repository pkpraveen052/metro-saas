from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


class PosPaymentChangeWizard(models.TransientModel):
    _name = "pos.payment.change.wizard"
    _description = "PoS Payment Change Wizard"

    order_id = fields.Many2one("pos.order", string="Order")
    payment_new_line_ids = fields.One2many("pos.payment.change.line", "pos_payment_change_id",string="New Payment Lines")
    amount_total = fields.Float(string="Total", store=True)

    @api.model
    def default_get(self, fields):
        PosOrder = self.env["pos.order"]
        res = super().default_get(fields)
        order = PosOrder.browse(self._context.get("active_id"))
        old_lines_vals = []
        for payment in order.payment_ids:
            old_lines_vals.append(
                (
                    0,
                    0,
                    {
                        "old_payment_method_id": payment.payment_method_id.id,
                        "amount": payment.amount,
                    },
                )
            )
        res.update(
            {
                "order_id": order.id,
                "amount_total": order.amount_total,
                "payment_new_line_ids": old_lines_vals,
            }
        )
        return res

    def button_change_payment(self):
        self.ensure_one()
        order = self.order_id
        for line in self.payment_new_line_ids:
            if not line.new_payment_method_id:
                raise ValidationError("Please select new payment method for all lines.")
        # Change payment
        new_payments = [
            {
                "pos_order_id": order.id,
                "payment_method_id": line.new_payment_method_id.id,
                "amount": self.amount_total,
                "payment_date": fields.Date.context_today(self),
            }
            for line in self.payment_new_line_ids
        ]
        order.change_payment(new_payments)

