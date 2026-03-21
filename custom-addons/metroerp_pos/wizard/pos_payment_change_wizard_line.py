from odoo import api, fields, models


class PosPaymentChangeLine(models.TransientModel):
    _name = "pos.payment.change.line"
    _description = "PoS Payment Change Line"

    pos_payment_change_id = fields.Many2one("pos.payment.change.wizard",required=True)
    old_payment_method_id = fields.Many2one("pos.payment.method", string="Old Payment Method",readonly=True)
    new_payment_method_id = fields.Many2one("pos.payment.method", string="New Payment Method",
                                            domain=lambda s: s._domain_new_payment_method_id())
    company_currency_id = fields.Many2one("res.currency",
                                          store=True,
                                          related="new_payment_method_id.company_id.currency_id",
                                          string="Company Currency",
                                          readonly=True)
    amount = fields.Monetary(string="Amount", default=0.0, currency_field="company_currency_id")

    @api.model
    def _domain_new_payment_method_id(self):
        """
        session regarding payment_methods_ids only filtered
        """
        PosOrder = self.env["pos.order"]
        order = PosOrder.browse(self.env.context.get("active_id"))
        return [("id", "in", order.mapped("session_id.payment_method_ids").ids)]