from email.policy import default
from string import digits

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError

class ProgressiveBillingQtLines(models.Model):
    _name = "progressive.billing.qt.lines"
    _description = "Progressive Billing Qt Lines"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the Progressive line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.progressive_billing_qt_id.partner_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })


    name = fields.Text(string='Description', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    # product_id = fields.Many2one(
    #     'product.product', string='Product', domain="[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    #     change_default=True, ondelete='restrict', check_company=True)  # Unrequired company
    product_id = fields.Many2one(
        'product.product', string='Product', domain=[('sale_ok', '=', True)])
    progressive_billing_qt_id = fields.Many2one('progressive.billing.qt', string='Progressive Billing')
    company_id = fields.Many2one(related='progressive_billing_qt_id.company_id', string='Company', store=True, readonly=True, index=True)
    currency_id = fields.Many2one('res.currency', string="Currency",related="company_id.currency_id")
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)
    tax_id = fields.Many2many('account.tax', string='Taxes', context={'active_test': False})
    price_subtotal = fields.Monetary(string='Subtotal', readonly=True, store=True, compute='_compute_amount')
    price_tax = fields.Float(compute='_compute_amount', string='Total Tax', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    pending_claim_amount  = fields.Monetary(string="Pending Claim Amount With %", readonly=True, copy=False)
    progress = fields.Float(string="Current Progress", groups="base.group_user", required=True, digits="Quotation Progressive")
    old_progress = fields.Float(string="Previous Claimed", groups="base.group_user", copy=False)
    is_paid = fields.Boolean('Is Paid', default=False, copy=False)
    is_confirm = fields.Boolean('IS Confirm', default=False, copy=False)
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")
    claimed_total_without_tax = fields.Monetary(string='Total Claimed', readoinly=True, store=True, copy=False)


    @api.onchange('product_id')
    def onchange_product_id(self):
        """ uom set on product """
        if self.product_id:
            if self.product_id.uom_id:
                self.product_uom = self.product_id.uom_id.id
            if self.product_id.description_sale:
                self.name = self.product_id.description_sale
            if self.product_id.list_price:
                self.price_unit = self.product_id.list_price


    def update_remaining_amount(self, invoiced_amount):
        for record in self:
            if record.pending_claim_amount == 0.0 and record.progress > 0.0 and record.progress != record.old_progress:
                record.pending_claim_amount = record.price_subtotal
            record.pending_claim_amount =  record.pending_claim_amount - invoiced_amount
            # record.pending_claim_amount = round(record.pending_claim_amount, 2) - invoiced_amount
        # if is_final:
        #     for record in self:
        #         if record.pending_claim_amount == 0.0 and record.progress > 0.0 and record.progress != record.old_progress:
        #            record.pending_claim_amount = record.price_total
        #         record.pending_claim_amount -= invoiced_amount #o/p = 0.01
        #
        #         if abs(round(record.pending_claim_amount)) == 0: # 0 == 0
        #             record.pending_claim_amount = 0
        # else:

    @api.onchange('progress')
    def _onchange_progress_value(self):
        for line in self:
            if line.progress > 1.0:
                raise ValidationError(_("The progress value cannot be more than 100%."))

    def claim_total(self, invoiced_subtotal):
        for record in self:
            record.claimed_total_without_tax += invoiced_subtotal


