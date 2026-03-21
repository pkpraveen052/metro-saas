from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang, format_date, get_lang


class AccountMove(models.Model):
    _inherit = 'account.move'

    progressive_billing_qt_id = fields.Many2one('progressive.billing.qt', string='Billing Quotation')
    is_progressive_invoice = fields.Boolean('Is Progressive Invoice')
    claim_no = fields.Integer('Claim No.')
    previous_invoice_id = fields.Many2one('account.move', string="Previous Invoice")
    is_posted = fields.Boolean('Is Posted', default=False)
    description = fields.Char(string="Description")
    reference = fields.Char(string="Your Reference")

    def button_cancel(self):
        for move in self:
            if move.is_progressive_invoice:
                last_invoice = self.search([('progressive_billing_qt_id', '=', move.progressive_billing_qt_id.id), ('state', '!=', 'cancel'), ('move_type', 'in', ['out_invoice']), ('payment_state', '!=', 'reversed')], order="id desc", limit=1)
                if last_invoice and last_invoice.id > move.id:
                    raise ValidationError(_("You must cancel the latest invoice '%s' before canceling this one.") % last_invoice.name)
                for line in move.invoice_line_ids:
                    if self.is_posted:
                        line.progressive_billing_qt_line_id.pending_claim_amount += line.price_total
                        line.progressive_billing_qt_line_id.old_progress = line.old_progress
                        line.progressive_billing_qt_line_id.is_paid = False
                        self.progressive_billing_qt_id.is_fully_paid = False
                        self.claim_no = 0
                        if line.progressive_billing_qt_line_id.claimed_total_without_tax > 0:
                            line.progressive_billing_qt_line_id.claimed_total_without_tax = line.progressive_billing_qt_line_id.claimed_total_without_tax - line.price_subtotal
        return super(AccountMove, self).button_cancel()

    def action_post(self):
        # for line in self.invoice_line_ids:
        result = super(AccountMove, self).action_post()
        if self.is_progressive_invoice:
            for line in self.invoice_line_ids:
                if line.progressive_billing_qt_line_id and line.progressive_billing_qt_line_id.is_paid != True:
                    invoiced_amount = line.price_total
                    invoiced_subtotal = line.price_subtotal

                    # if line.progress == 1.0:
                    #     line.progressive_billing_qt_line_id.update_remaining_amount(invoiced_amount, is_final=True)
                    # else:
                    line.progressive_billing_qt_line_id.update_remaining_amount(invoiced_subtotal)
                    line.progressive_billing_qt_line_id.claim_total(invoiced_subtotal)
                    line.progressive_billing_qt_line_id.old_progress = line.progress
                    # if line.progress == 1.0:
                    #     line.update_claimed_amount(is_final=True)
                    # else:
                    line.update_claimed_amount()
                    self.is_posted = True
                    if line.progressive_billing_qt_line_id.old_progress == 1.0 and line.progressive_billing_qt_line_id.progress == 1.0:
                    #     line.progressive_billing_qt_line_id.progress = 1.0
                        line.progressive_billing_qt_line_id.is_paid = True
                        self.progressive_billing_qt_id._is_fully_paid()
        return result

    def button_draft(self):
        for move in self:
            if move.is_progressive_invoice:
                last_invoice = self.search(
                    [('progressive_billing_qt_id', '=', move.progressive_billing_qt_id.id), ('state', 'in', ['posted', 'draft']), ('is_posted', '!=', False), ('move_type', 'in', ['out_invoice']), ('payment_state', '!=', 'reversed')],
                    order="id desc", limit=1)
                if last_invoice and last_invoice.id > move.id:
                    raise ValidationError(
                        _("You must reset the latest invoice '%s' to cancel before resetting this one.") % last_invoice.name)
        return super(AccountMove, self).button_draft()

    def action_reverse(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_view_account_move_reversal")
        if self.is_progressive_invoice:
            last_invoice = self.env['account.move'].search([('progressive_billing_qt_id', '=', self.progressive_billing_qt_id.id)],
                                                           order="id desc", limit=1)
            # only last invoice credit not generated
            if last_invoice and last_invoice.id > self.id:
                raise ValidationError(
                    _("You can only Add credit note for the latest invoice '%s'") % last_invoice.name)
            action_context = {'is_progressive': True, 'default_refund_method': 'cancel'}
            action['context'] = action_context
        if self.is_invoice():
            action['name'] = _('Credit Note')

        return action

    @api.model
    def create(self, vals):
        """
        Update claim no in credit note invoice.
        """
        obj = super(AccountMove, self).create(vals)
        if obj.is_progressive_invoice and obj.move_type == 'out_refund':
            existing_invoices = self.env['account.move'].search_count([('progressive_billing_qt_id', '=', obj.progressive_billing_qt_id.id), ('state', '!=', 'cancel')])
            if existing_invoices > 0:
            # previous_invoice = self.env['account.move'].search(
            #     [('claim_no', '=', existing_invoices), ('progressive_billing_qt_id', '=', self.id)])
            # invoice.previous_invoice_id = previous_invoice.id
                obj.claim_no = existing_invoices
        return obj

    def get_total_amount_untaxed(self):
        """Returns the total claimed amount for the current invoice."""
        self.ensure_one()
        return sum(self.invoice_line_ids.mapped('claimed_total_without_tax'))

#Dhanesh code start from here==================================================


    def get_claim_label(self):
        """Return progress claim label only if more than one invoice exists for the same quotation."""
        self.ensure_one()

        if not self.progressive_billing_qt_id:
            return ""

        # Count all invoices linked to this billing quotation
        total_claims = self.search_count([
            ('progressive_billing_qt_id', '=', self.progressive_billing_qt_id.id),
            ('move_type', '=', self.move_type),  # optional: filter by invoice type
        ])

        if total_claims <= 1:
            return ""  # hide label for single claim

        claim_no = self.claim_no or 1
        if 10 <= claim_no % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(claim_no % 10, "th")

        return f"Being {claim_no}{suffix} Progress Claim"


    def get_less_previous_claim(self):
        """Returns the difference between the current and previous invoice claimed amount."""
        self.ensure_one()

        current_claim_no = self.claim_no
        if current_claim_no <= 1:
            return 0.0  # No previous claim to subtract

        previous_claim_no = current_claim_no - 1
        prev_invoice = self.env['account.move'].search([
            ('progressive_billing_qt_id', '=', self.progressive_billing_qt_id.id),
            ('state', '=', 'posted'),
            '|', ('id', '<', self.id),('claim_no', '<', self.claim_no),
        ], order='id desc', limit=1)

        if not prev_invoice:
            return 0.0  # No valid previous claim found

        previous_claimed_amount = sum(prev_invoice.invoice_line_ids.mapped('claimed_total_without_tax'))
        # current_claimed_amount = self.get_total_claim_amount()

        return previous_claimed_amount
        


    def action_invoice_sent(self):
        """Open a window to compose an email, with the proper invoice template loaded by default."""
        self.ensure_one()

        # Choose template based on whether invoice is progressive
        if self.is_progressive_invoice:
            template = self.env.ref('metroerp_progressive_billing.email_template_edi_progressive_invoice', raise_if_not_found=False)
        else:
            template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)

        lang = False
        if template:
            lang = template._render_lang(self.ids)[self.id]
        if not lang:
            lang = get_lang(self.env).code

        compose_form = self.env.ref('account.account_invoice_send_wizard_form', raise_if_not_found=False)

        ctx = dict(
            default_model='account.move',
            default_res_id=self.id,
            default_res_model='account.move',
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            custom_layout="mail.mail_notification_paynow",
            model_description=self.with_context(lang=lang).type_name,
            force_email=True
        )

        return {
            'name': _('Send Invoice'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.send',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
    
    def action_invoice_print(self):
        """Print the invoice with progressive condition"""
        if any(not move.is_invoice(include_receipts=True) for move in self):
            raise UserError(_("Only invoices could be printed."))

        self.filtered(lambda inv: not inv.is_move_sent).write({'is_move_sent': True})

        #Conditional report logic
        for move in self:
            if move.is_progressive_invoice:
                # Calling custom progressive report
                return self.env.ref('ks_custom_report_layouts.action_progressive_invoice_report').report_action(move)
            
        #Fall back to original logic
        if self.user_has_groups('account.group_account_invoice'):
            return self.env.ref('account.account_invoices').report_action(self)
        else:
            return self.env.ref('account.account_invoices_without_payment').report_action(self)
    
#Dhanesh code end here ===========================================================

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    progress = fields.Float(string='Completed Progress', readonly=True, store=True, digits="Quotation Progressive")
    progressive_billing_qt_line_id = fields.Many2one('progressive.billing.qt.lines', string='Billing Line')
    remaining_amount  = fields.Monetary(string='Remaining Amount', readonly=True, store=True)
    old_progress = fields.Float("Old", groups="base.group_user")
    claimed_amount  = fields.Monetary(string='Completed Claim Amount', readoinly=True, store=True)
    qt_total = fields.Float(string='QT Amount', digits='Product Price')
    claimed_total_without_tax = fields.Monetary(string='Total Claimed', store=True)


    def update_claimed_amount(self):
        # if is_final:
            #self.claimed_amount = self.progressive_billing_qt_line_id.price_unit - self.progressive_billing_qt_line_id.pending_claim_amount
            # self.claimed_amount = self.progressive_billing_qt_line_id.price_unit
        self.claimed_amount = self.progressive_billing_qt_line_id.price_total - self.progressive_billing_qt_line_id.pending_claim_amount
        self.claimed_total_without_tax = self.progressive_billing_qt_line_id.claimed_total_without_tax



    # @api.onchange('quantity', 'discount', 'discount_type', 'price_unit', 'tax_ids')
    # def _onchange_price_subtotal(self):
    #     return super(AccountMoveLine, self)._onchange_price_subtotal()

    # @api.model
    # def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes,
    #                                         move_type):
    #     print("\n OVERIDDEN _get_price_total_and_subtotal_model() >>>>>TTTTTTTTTTTT")
    #     print("self._context ==", self._context)
    #     res = {}
    #     line_discount_price_unit, subtotal = 0.0, 0.0
    #     # Compute 'price_subtotal'.
    #     discount_type = ''
    #     if self._context and self._context.get('wk_vals_list', []):
    #         for vals in self._context.get('wk_vals_list', []):
    #             if price_unit == vals.get('price_unit', 0.0) and quantity == vals.get('quantity',
    #                                                                                   0.0) and discount == vals.get(
    #                 'discount', 0.0) and product.id == vals.get('product_id', False) and partner.id == vals.get(
    #                 'partner_id', False):
    #                 discount_type = vals.get('discount_type', '')
    #     discount_type = self.discount_type or discount_type
    #     if discount_type == 'fixed' and quantity and price_unit:
    #         new_discount = (discount / (quantity * price_unit)) * 100
    #         line_discount_price_unit = price_unit * (1 - (new_discount / 100.0))
    #         subtotal = quantity * line_discount_price_unit
    #         # price_unit_wo_discount = price_unit * quantity - discount
    #         # quantity = 1.0
    #     else:
    #         if self.move_id.is_progressive_invoice:
    #             line_discount_price_unit = price_unit * (1 - (discount / 100.0))
    #             subtotal = quantity * line_discount_price_unit * self.progress
    #         else:
    #             line_discount_price_unit = price_unit * (1 - (discount / 100.0))
    #             subtotal = quantity * line_discount_price_unit
    #
    #     # Compute 'price_total'.
    #     # if price_unit == 0:
    #     # self.tax_ids = False
    #     if taxes:
    #         taxes_res = taxes._origin.with_context(force_sign=1).compute_all(line_discount_price_unit,
    #                                                                          quantity=quantity, currency=currency,
    #                                                                          product=product, partner=partner,
    #                                                                          is_refund=move_type in (
    #                                                                              'out_refund', 'in_refund'))
    #         print("taxes_res ==", taxes_res)
    #         if self.move_id.is_progressive_invoice:
    #             res['price_subtotal'] = taxes_res['total_excluded'] * self.progress
    #             res['price_total'] = taxes_res['total_included'] * self.progress
    #         else:
    #             res['price_subtotal'] = taxes_res['total_excluded']
    #             res['price_total'] = taxes_res['total_included']
    #     else:
    #         res['price_total'] = res['price_subtotal'] = subtotal
    #     # In case of multi currency, round before it's use for computing debit credit
    #     if currency:
    #         res = {k: currency.round(v) for k, v in res.items()}
    #     print("Returning..... res ==", res)
    #     return res

    # @api.model
    # def _get_fields_onchange_balance_model(self, quantity, discount, amount_currency, move_type, currency, taxes,
    #                                        price_subtotal, force_computation=False):
    #     ''' This method is used to recompute the values of 'quantity', 'discount', 'price_unit' due to a change made
    #     in some accounting fields such as 'balance'.
    #
    #     This method is a bit complex as we need to handle some special cases.
    #     For example, setting a positive balance with a 100% discount.
    #
    #     :param quantity:        The current quantity.
    #     :param discount:        The current discount.
    #     :param amount_currency: The new balance in line's currency.
    #     :param move_type:       The type of the move.
    #     :param currency:        The currency.
    #     :param taxes:           The applied taxes.
    #     :param price_subtotal:  The price_subtotal.
    #     :return:                A dictionary containing 'quantity', 'discount', 'price_unit'.
    #     '''
    #     print("\nwwwwwwwwssssggggg   OVERIDDEN _get_fields_onchange_balance_model() >>>>>")
    #     print("self._context ==", self._context)
    #     if move_type in self.move_id.get_outbound_types():
    #         sign = 1
    #     elif move_type in self.move_id.get_inbound_types():
    #         sign = -1
    #     else:
    #         sign = 1
    #     amount_currency *= sign
    #
    #     # Avoid rounding issue when dealing with price included taxes. For example, when the price_unit is 2300.0 and
    #     # a 5.5% price included tax is applied on it, a balance of 2300.0 / 1.055 = 2180.094 ~ 2180.09 is computed.
    #     # However, when triggering the inverse, 2180.09 + (2180.09 * 0.055) = 2180.09 + 119.90 = 2299.99 is computed.
    #     # To avoid that, set the price_subtotal at the balance if the difference between them looks like a rounding
    #     # issue.
    #     if not force_computation and currency.is_zero(amount_currency - price_subtotal):
    #         print("Returning...... {}")
    #         return {}
    #
    #     taxes = taxes.flatten_taxes_hierarchy()
    #     if taxes and any(tax.price_include for tax in taxes):
    #         # Inverse taxes. E.g:
    #         #
    #         # Price Unit    | Taxes         | Originator Tax    |Price Subtotal     | Price Total
    #         # -----------------------------------------------------------------------------------
    #         # 110           | 10% incl, 5%  |                   | 100               | 115
    #         # 10            |               | 10% incl          | 10                | 10
    #         # 5             |               | 5%                | 5                 | 5
    #         #
    #         # When setting the balance to -200, the expected result is:
    #         #
    #         # Price Unit    | Taxes         | Originator Tax    |Price Subtotal     | Price Total
    #         # -----------------------------------------------------------------------------------
    #         # 220           | 10% incl, 5%  |                   | 200               | 230
    #         # 20            |               | 10% incl          | 20                | 20
    #         # 10            |               | 5%                | 10                | 10
    #         force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
    #         taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(amount_currency,
    #                                                                                   currency=currency,
    #                                                                                   handle_price_include=False)
    #         for tax_res in taxes_res['taxes']:
    #             tax = self.env['account.tax'].browse(tax_res['id'])
    #             if tax.price_include:
    #                 amount_currency += tax_res['amount']
    #
    #     discount_type = ''
    #     if self._context and self._context.get('wk_vals_list', []):
    #         for vals in self._context.get('wk_vals_list', []):
    #             if quantity == vals.get('quantity', 0.0) and discount == vals.get('discount', 0.0):
    #                 discount_type = vals.get('discount_type', '')
    #     discount_type = self.discount_type or discount_type
    #     if discount_type == 'fixed':
    #         if amount_currency:
    #             vals = {
    #                 'quantity': quantity or 1.0,
    #                 'price_unit': (amount_currency + discount) / (quantity or 1.0),
    #             }
    #         else:
    #             vals = {}
    #     else:
    #         discount_factor = 1 - (discount / 100.0)
    #         if amount_currency and discount_factor:
    #             # discount != 100%
    #             print("# discount != 100% >>")
    #             print("amount_currency =", amount_currency, ", discount_factor =", discount_factor, ", quantity =",
    #                   quantity)
    #             vals = {
    #                 'quantity': quantity or 1.0,
    #                 'price_unit': amount_currency / discount_factor / (quantity or 1.0),
    #             }
    #         elif amount_currency and not discount_factor:
    #             # discount == 100%
    #             print("# discount == 100% >>")
    #             print("amount_currency =", amount_currency, ", discount_factor =", ", quantity =", quantity)
    #             vals = {
    #                 'quantity': quantity or 1.0,
    #                 'discount': 0.0,
    #                 'price_unit': amount_currency / (quantity or 1.0),
    #             }
    #         elif not discount_factor:
    #             # balance of line is 0, but discount  == 100% so we display the normal unit_price
    #             print("# balance of line is 0, but discount  == 100% so we display the normal unit_price >>")
    #             vals = {}
    #         else:
    #             # balance is 0, so unit price is 0 as well
    #             print("# balance is 0, so unit price is 0 as well >>")
    #             vals = {'price_unit': 0.0}
    #         print("Returning..... vals ==", vals)
    #     return vals









    # @api.model_create_multi
    # def create(self, vals_list):
    #     """ Override create method to update price_subtotal and price_total based on progress. """
    #
    #     lines = super(AccountMoveLine, self).create(vals_list)
    #     print('\n\n\n\n\n\nlinecreateneww??????::::::{{{{{{', lines)
    #     for line in lines:
    #         if line.progress > 0.0 and line.price_subtotal:
    #             line.price_subtotal = line.price_subtotal * line.progress
    #             line.price_total = line.price_subtotal
    #         if line.progress == 0.0 and line.price_subtotal:
    #             line.price_subtotal = line.price_subtotal * line.progress
    #             line.price_total = line.price_subtotal
    #     return lines
