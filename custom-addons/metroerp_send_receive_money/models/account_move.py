from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, date_utils, email_split, email_re, float_is_zero


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def default_get(self, fields):
        res = super(AccountMove, self).default_get(fields)
        if self._context.get('default_transaction_type'):
            journal = self.env['account.journal'].search([
                ('type', 'in', ['bank', 'cash']),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            if journal:
                res['journal_id'] = journal.id
                # res['state'] = 'posted'
        return res

    # is_receive_money = fields.Boolean('Is Receive Money')
    # is_send_money = fields.Boolean('Is Send Money')
    transaction_type = fields.Selection([
        ('send', 'Send Money'),
        ('receive', 'Receive Money')
    ], string="Transaction Type")
    send_receive_money_line_ids = fields.One2many('send.receive.money.line', 'move_id', string='Invoice Line')
    is_reconciliation = fields.Boolean('Reconciliation', default=False)

    def copy_data(self, default=None):
        res = super(AccountMove, self).copy_data(default=default)
        if default is None:
            default = {}

        for values in res:
            if 'partner_id' not in values:
                values['partner_id'] = self.partner_id.id
            else:
                values['partner_id'] = self.partner_id.id
            if 'send_receive_money_line_ids' not in values:
                values['send_receive_money_line_ids'] = [
                    (0, 0, line.copy_data()[0]) for line in self.send_receive_money_line_ids
                ]
        return res

    def _generate_journal_lines(self):
        all_lines = []
        for obj in self:
            if obj.transaction_type:
                if not obj.send_receive_money_line_ids:
                    raise UserError(_('You need to add a line before posting.'))
                journal = obj.journal_id
                bank_account = journal.default_account_id
                if obj.is_reconciliation:
                    # bank default account
                    if not bank_account:
                        raise UserError(_('Please set a default account on the selected journal.'))
                    journal_account = bank_account
                else:
                    # bank Outstanding account
                    if obj.transaction_type == 'receive':
                        journal_account = journal.payment_debit_account_id
                    else:
                        journal_account = journal.payment_credit_account_id
                    if not journal_account:
                        raise UserError(_('Please set the Outstanding %s Account on the selected journal.') %
                                        ('Receipts' if obj.transaction_type == 'receive' else 'Payments'))

                total_amount = sum(
                    obj.send_receive_money_line_ids.filtered(lambda l: not l.display_type).mapped('price_total'))
                bank_line = {
                    'account_id': journal_account.id,
                    'name': self.ref or self.payment_reference,
                    'partner_id': False,
                    'debit': total_amount if obj.transaction_type == 'receive' else 0.0,
                    'credit': total_amount if obj.transaction_type == 'send' else 0.0,
                }
                all_lines.append((0, 0, bank_line))

                for line in obj.send_receive_money_line_ids.filtered(lambda l: not l.display_type):
                    taxes = line.tax_ids.compute_all(
                        line.price_unit,
                        currency=obj.currency_id,
                        quantity=line.quantity,
                        product=line.product_id,
                        partner=obj.partner_id,
                    )

                    # Base line
                    base_line = {
                        'account_id': line.account_id.id,
                        'name': line.name or '/',
                        'partner_id': obj.partner_id.id if obj.partner_id else False,
                        'tax_ids': line.tax_ids.ids,
                        'debit': 0.0,
                        'credit': 0.0,
                    }
                    amount = taxes['total_excluded']
                    if amount >= 0:
                        if obj.transaction_type == 'receive':
                            base_line['credit'] = amount
                        else:
                            base_line['debit'] = amount
                    else:
                        if obj.transaction_type == 'receive':
                            base_line['debit'] = abs(amount)
                        else:
                            base_line['credit'] = abs(amount)

                    all_lines.append((0, 0, base_line))

                    # Tax lines of jurnal items
                    for tax in line.tax_ids:
                        # tax amount get from taxes.
                        amount = 0.0
                        for tax_line in taxes['taxes']:
                            if isinstance(tax_line['id'], int) and tax_line['id'] == tax.id:
                                amount = tax_line['amount']
                                break

                        # Get tax account
                        repartition_lines = tax.invoice_repartition_line_ids.filtered(
                            lambda l: l.repartition_type == 'tax' and l.account_id)
                        if not repartition_lines:
                            raise UserError(_('Tax %s has no account defined.') % tax.name)

                        tax_account_id = repartition_lines[0].account_id.id
                        tag_ids = repartition_lines.mapped('tag_ids').ids
                        repartition_line = repartition_lines[0]  # pick first valid repartition line
                        repartition_line_id = repartition_line.id
                        tax_vals = {
                            'account_id': tax_account_id,
                            'name': tax.name,
                            'partner_id': obj.partner_id.id if obj.partner_id else False,
                            'tax_tag_ids': [(6, 0, tag_ids)],
                            'tax_line_id': tax.id,  # 🔑 marks this as a tax line
                            'tax_repartition_line_id': repartition_line_id,# 🔑 needed in Odoo 14+
                            'tax_base_amount': taxes['total_excluded'],
                            'debit': 0.0,
                            'credit': 0.0,
                        }
                        tax_amount = tax_line['amount']
                        if tax_amount >= 0:
                            if obj.transaction_type == 'receive':
                                tax_vals['credit'] = tax_line['amount']
                            else:
                                tax_vals['debit'] = tax_line['amount']
                        else:
                            if obj.transaction_type == 'receive':
                                tax_vals['debit'] = abs(tax_amount)
                            else:
                                tax_vals['credit'] = abs(tax_amount)

                        all_lines.append((0, 0, tax_vals))
        return all_lines

    @api.model
    def create(self, vals):
        """
        Create Journal Items for receive and send money.
        """
        obj = super(AccountMove, self).create(vals)
        if obj.transaction_type:
            new_lines = obj._generate_journal_lines()
            obj.line_ids = [(5, 0, 0)] + new_lines
        return obj

    @api.onchange('date','send_receive_money_line_ids', 'send_receive_money_line_ids.price_subtotal', 'send_receive_money_line_ids.price_total', 'journal_id')
    def _onchange_generate_journal_lines(self):
        for rec in self:
            if self._origin and self.transaction_type:
                new_lines = rec._generate_journal_lines()
                rec.update({
                    'line_ids': [(5, 0, 0)] + new_lines
                })

    def write(self, vals):
        if 'custom_write_date' not in vals:
            vals['custom_write_date'] = fields.Datetime.now()
        for obj in self:  # For the moves that are created from Manual Payment/Miscellenous entry, when any change made for the Accounting Date (condition that its Payment entry's Adjust Carry fwd is not selected) then modify the invoice_date to its Accounting Date.
            if vals.get('date', False) and obj.move_type == 'entry' and not obj.payment_id.adjust_in_carry_fwd_bal:
                vals['invoice_date'] = vals['date']
        res = super(AccountMove, self).write(vals)

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        ''' override method to not new tax line generated when transaction_type (send,receive)

        Recompute all lines that depend on others.

        For example, tax lines depends on base lines (lines having tax_ids set). This is also the case of cash rounding
        lines that depend on base lines or tax lines depending on the cash rounding strategy. When a payment term is set,
        this method will auto-balance the move with payment term lines.

        :param recompute_all_taxes: Force the computation of taxes. If set to False, the computation will be done
                                    or not depending on the field 'recompute_tax_line' in lines.
        '''
        for invoice in self:
            # Dispatch lines and pre-compute some aggregated values like taxes.
            expected_tax_rep_lines = set()
            current_tax_rep_lines = set()
            inv_recompute_all_taxes = recompute_all_taxes
            has_taxes = False
            for line in invoice.line_ids:
                if line.recompute_tax_line:
                    inv_recompute_all_taxes = True
                    line.recompute_tax_line = False
                if line.tax_repartition_line_id:
                    current_tax_rep_lines.add(line.tax_repartition_line_id._origin)
                elif line.tax_ids:
                    has_taxes = True
                    if invoice.is_invoice(include_receipts=True):
                        is_refund = invoice.move_type in ('out_refund', 'in_refund')
                    else:
                        tax_type = line.tax_ids[0].type_tax_use
                        is_refund = (tax_type == 'sale' and line.debit) or (tax_type == 'purchase' and line.credit)
                    taxes = line.tax_ids._origin.flatten_taxes_hierarchy().filtered(
                        lambda tax: (
                                tax.amount_type == 'fixed' and not invoice.company_id.currency_id.is_zero(tax.amount)
                                or not float_is_zero(tax.amount, precision_digits=4)
                        )
                    )
                    if is_refund:
                        tax_rep_lines = taxes.refund_repartition_line_ids._origin.filtered(lambda x: x.repartition_type == "tax")
                    else:
                        tax_rep_lines = taxes.invoice_repartition_line_ids._origin.filtered(lambda x: x.repartition_type == "tax")
                    for tax_rep_line in tax_rep_lines:
                        expected_tax_rep_lines.add(tax_rep_line)
            delta_tax_rep_lines = expected_tax_rep_lines - current_tax_rep_lines

            # Compute taxes.
            if has_taxes or current_tax_rep_lines:
                if inv_recompute_all_taxes and not invoice.transaction_type:
                    invoice._recompute_tax_lines()
                elif recompute_tax_base_amount and not invoice.transaction_type:
                    invoice._recompute_tax_lines(recompute_tax_base_amount=True)
                elif delta_tax_rep_lines and not self._context.get('move_reverse_cancel') and not invoice.transaction_type:
                    invoice._recompute_tax_lines(tax_rep_lines_to_recompute=delta_tax_rep_lines)

            if invoice.is_invoice(include_receipts=True):

                # Compute cash rounding.
                invoice._recompute_cash_rounding_lines()

                # Compute payment terms.
                invoice._recompute_payment_terms_lines()

                # Only synchronize one2many in onchange.
                if invoice != invoice._origin:
                    invoice.invoice_line_ids = invoice.line_ids.filtered(lambda line: not line.exclude_from_invoice_tab)

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'send_receive_money_line_ids.price_subtotal',
        'send_receive_money_line_ids.price_total',)
    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()
        for move in self:
            if move.transaction_type:
                amount_untaxed = amount_tax = 0.0
                for line in move.send_receive_money_line_ids:
                    amount_untaxed += line.price_subtotal
                    amount_tax += line.price_tax
                move.update({
                    'amount_untaxed': amount_untaxed,
                    'amount_tax': amount_tax,
                    'amount_total': amount_untaxed + amount_tax,
                })
                # move._generate_journal_lines()

    @api.onchange('is_reconciliation')
    def _onchange_is_reconciliation(self):
        for rec in self:
            if rec.line_ids:
                line = rec.line_ids.filtered(
                    lambda l: l.account_id in (
                        rec.journal_id.default_account_id,
                        rec.journal_id.payment_debit_account_id,
                        rec.journal_id.payment_credit_account_id
                    )
                )
                if rec.is_reconciliation:
                    line.update({'account_id': rec.journal_id.default_account_id.id, 'name': rec.ref or rec.payment_reference or ''})
                else:
                    line.update({'account_id': rec.journal_id.payment_debit_account_id.id, 'name': rec.ref or rec.payment_reference or ''}) if rec.transaction_type == 'receive' else line.update({'account_id': rec.journal_id.payment_credit_account_id.id, 'name': rec.ref or rec.payment_reference or ''})

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """
        field view get method to hide action child menu and print menu
        """
        res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if toolbar:
            if self._context.get('default_transaction_type') in ['send', 'receive']:
                toolbar_actions = res['toolbar'].get('action', [])
                xml_ids_to_remove = [
                    'metro_einvoice_datapost.action_move_peppol_send',
                    'account.model_account_move_action_share',
                    'account.action_move_switch_invoice_to_credit_note',
                    'recurring_invoice_app.action_recurring_invoice',
                    'account.action_view_account_move_reversal',
                    'account.action_account_resequence',
                    'account.action_validate_account_move',
                    'account.invoice_send',
                    'account_debit_note.action_view_account_move_debit',
                    'account.action_account_invoice_from_list',
                    'metroerp_customizations.action_account_invoice_xls',
                    'metroerp_ocr.action_upload_invoice_wizard',
                ]
                filtered_actions = [
                    action for action in toolbar_actions
                    if action.get('xml_id') not in xml_ids_to_remove
                ]
                res['toolbar']['action'] = filtered_actions
                res['toolbar']['print'] = []
        return res

    def _auto_compute_invoice_reference(self):
        ''' Hook to be overridden to set custom conditions for auto-computed invoice references.
            :return True if the move should get a auto-computed reference else False
            :rtype bool
        '''
        self.ensure_one()
        return (self.move_type == 'out_invoice' or (self.move_type == 'entry' and self.transaction_type in ('send', 'receive'))) and not self.payment_reference
      

    @api.onchange('payment_reference', 'ref')
    def _onchange_payment_reference(self):
        if self.transaction_type in ('send', 'receive'):
            for rm_sm_line in self.line_ids.filtered(
                lambda line: (
                        line.account_id.id in (
                    self.journal_id.payment_debit_account_id.id,
                    self.journal_id.payment_credit_account_id.id,
                    self.journal_id.default_account_id.id,
                )
                )):
                rm_sm_line.name = self.ref or self.payment_reference or ''
        else:
            for line in self.line_ids.filtered(
                    lambda line: line.account_id.user_type_id.type in ('receivable', 'payable')):
                line.name = self.payment_reference or ''

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        for move in self:
            if move.transaction_type:
                move.write({'posted_before': False, 'name': '/'})
        return res

class SendReceiveMoneyLine(models.Model):
    _name = 'send.receive.money.line'
    _description = "Send Receive Money Line"

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Label', tracking=True, store=True, readonly=False)
    move_id = fields.Many2one('account.move', string='Journal Entry',
                              index=True, required=True, readonly=True, auto_join=True, ondelete="cascade",
                              check_company=True,
                              help="The move of this entry line.")
    date = fields.Date(string='Date')
    journal_id = fields.Many2one(related='move_id.journal_id', store=True, index=True, copy=False)
    company_id = fields.Many2one(related='move_id.company_id', store=True, readonly=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency',
                                          readonly=True, store=True,
                                          help='Utility field to express amount currency')
    account_id = fields.Many2one('account.account', string='Account',
                                 index=True, ondelete="cascade",
                                 domain="[('deprecated', '=', False), ('company_id', '=', 'company_id'),('is_off_balance', '=', False)]",
                                 check_company=True,
                                 tracking=True)
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], default=False, help="Technical field for UX purpose.")
    quantity = fields.Float(string='Quantity',
                            default=lambda self: 0 if self._context.get('default_display_type') else 1.0,
                            digits='Product Unit of Measure',
                            help="The optional quantity expressed by this line, eg: number of product sold. "
                                 "The quantity is not a legal requirement but is very useful for some reports.")
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    price_subtotal = fields.Monetary(string='Subtotal', store=True, readonly=True,
                                     currency_field='currency_id', compute="_compute_totals")
    price_total = fields.Monetary(string='Total', store=True, readonly=True,
                                  currency_field='currency_id', compute="_compute_totals")
    price_tax = fields.Float(compute='_compute_totals', string='Total Tax', readonly=True, store=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure',
                                     domain="[('category_id', '=', product_uom_category_id)]")
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict')
    product_uom_category_id = fields.Many2one('uom.category', related='product_id.uom_id.category_id')
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        context={'active_test': False},
        check_company=True,
        help="Taxes that apply on the base amount")
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], default=False, help="Technical field for UX purpose.")
    narration = fields.Text(string='Terms and Conditions')
    transaction_type = fields.Selection([
        ('send', 'Send Money'),
        ('receive', 'Receive Money')
    ], string="Transaction Type", default=False)


    @api.depends('quantity', 'price_unit', 'tax_ids', 'currency_id', 'product_id')
    def _compute_totals(self):
        for line in self:
            subtotal = line.quantity * line.price_unit
            if line.tax_ids:
                taxes = line.tax_ids._origin.with_context(force_sign=1).compute_all(
                    line.price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.move_id.partner_id,
                )
                line.price_subtotal = taxes['total_excluded']
                line.price_total = taxes['total_included']
                line.price_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
            else:
                line.price_subtotal = subtotal
                line.price_total = subtotal

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends('move_id.payment_reference')
    def _compute_name(self):
        for line in self.filtered(lambda l: not l.name and (l.account_id.user_type_id.type in ('receivable', 'payable') or l.move_id.transaction_type in ('send', 'receive'))):
            line.name = line.move_id.payment_reference
