# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError,UserError, AccessError
from datetime import datetime
from odoo.tools.misc import formatLang, format_date, get_lang
from collections import defaultdict
from odoo.tools import float_compare, date_utils, email_split, email_re, float_is_zero



class AccountMove(models.Model):
    _inherit = 'account.move'
    _order = 'invoice_date desc,name desc'

    #def _get_default_journal(self):
        #''' Retrieve the default journal for the account.payment.
        #/!\ This method will not override the method in 'account.move' because the ORM
        #doesn't allow overriding methods using _inherits. Then, this method will be called
        #manually in 'create' and 'new'.
        #:return: An account.journal record.
        #'''
        #return self.env['account.move']._search_default_journal(('bank', 'cash'))
        
    create_date_tmp = fields.Datetime('Creation Date', copy=False)
    custom_write_date = fields.Datetime(string='Last Modified', copy=False)
    order_reference = fields.Char(compute='_compute_order_reference', string='Order Reference')
    amount_total_signed = fields.Monetary(string='Total', store=True, readonly=True,
        compute='_compute_amount', currency_field='company_currency_id')
    invoice_partner_display_name = fields.Char(compute='_compute_invoice_partner_display_info', store=True, string='Customer')
    narration = fields.Text(string='Terms and Conditions', tracking=True)

    

    date = fields.Date(
        string='Date',
        required=True,
        tracking=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False,
        default=fields.Date.context_today
    )

    #journal_id = fields.Many2one('account.journal', string='Journal', required=True, readonly=True,
    #    states={'draft': [('readonly', False)]},tracking=True,
    #    check_company=True, domain="[('id', 'in', suitable_journal_ids)]",
    #    default=_get_default_journal)

    # 10Apr2025. Specially overidden to make the 'check_company' as False so to overide the validation check during the base import. 
    partner_id = fields.Many2one('res.partner', readonly=True, tracking=True,
        states={'draft': [('readonly', False)]},
        check_company=False, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        string='Partner', change_default=True, ondelete='restrict') 


    auto_post = fields.Selection([
        ('no', 'No'),
        ('at_date', 'At Date')
    ], string='Auto-post', default='no',required=True,copy=False,
       help='If set to "At Date", this entry will be automatically posted on its invoice date. '
            'If set to "No", it will be posted immediately even if the invoice date is in the future.')

    hide_post_button = fields.Boolean(compute='_compute_hide_post_button', readonly=True)

    @api.depends('date', 'auto_post')
    def _compute_hide_post_button(self):
        for record in self:
            record.hide_post_button = record.state != 'draft' \
                or record.auto_post != 'no' and record.date > fields.Date.context_today(record)       
    
    @api.model
    def default_get(self, fields):
        defaults = super(AccountMove, self).default_get(fields)
        current_date = datetime.today().date()
        # Set the current date as the default invoice date
        defaults['invoice_date'] = current_date
        return defaults


    def _compute_order_reference(self):
        for obj in self:
            obj.order_reference = obj.name

    # Method overridden
    def _get_name_invoice_report(self):
        """ This method need to be inherit by the localizations if they want to print a custom invoice report instead of
        the default one. For example please review the l10n_ar module """
        self.ensure_one()
        return 'metroerp_customizations.report_invoice_inherit_document'

    # Custom Terms and Conditions
    @api.onchange('move_type')
    def _onchange_type(self):
        ''' Onchange made to filter the partners depending of the type. '''
        if self.is_sale_document(include_receipts=True):
            if self.company_id.use_sales_invoice_tc:
                self.narration = self.company_id.sales_invoice_tc or self.env.company.sales_invoice_tc
        if self.is_purchase_document(include_receipts=True):
            if self.company_id.use_purchase_invoice_tc:
                self.narration = self.company_id.purchase_invoice_tc or self.env.company.purchase_invoice_tc

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        res = super(AccountMove, self)._onchange_partner_id()
        if self.is_sale_document(include_receipts=True) and self.partner_id:
            self.narration = self.company_id.with_context(lang=self.partner_id.lang or self.env.lang).sales_invoice_tc
        if self.is_purchase_document(include_receipts=True) and self.partner_id:
            self.narration = self.company_id.with_context(lang=self.partner_id.lang or self.env.lang).purchase_invoice_tc
        if self.partner_id:
            self.ref = self.partner_id.ref
        return res

    @api.model
    def create(self, vals):
        # if vals.get('narration'):
        #     if vals.get('move_type') and vals.get('move_type') in ['out_invoice', 'out_refund'] and self.env['ir.config_parameter'].sudo().get_param('use_sales_invoice_tc'):
        #         vals['narration'] = self.env.company.sales_invoice_tc or ''
        #     elif vals.get('move_type') and vals.get('move_type') in ['in_invoice', 'in_refund'] and self.env.company.use_purchase_invoice_tc:
        #         vals['narration'] = self.env.company.purchase_invoice_tc or ''
        res = super().create(vals)
        if vals.get('create_date_tmp'):
            self.env.cr.execute("UPDATE account_move set create_date = %s where id = %s", (vals.get('create_date_tmp'), res.id))
        else:
            res.create_date_tmp = res.create_date
        if vals.get('custom_write_date'):
            res.write({'write_date': vals['custom_write_date']})
        else:
            res.write({'custom_write_date': fields.Datetime.now()})
        if res.move_type == 'entry': # For the moves that are created from Manual Payment/Miscellenous entry, we are setting its value to be of Accounting Date's.
            res.write({'invoice_date': str(res.date)})
            if res.payment_id and res.payment_id.adjust_in_carry_fwd_bal: # If the move's Payment is selected with 'Adjust Carry Fwd' then overide the nivoice_date with 'Offset ADjust Cry Fwd' date'
                res.write({'invoice_date': str(res.payment_id.offset_carry_fwd_bal_date)})

        return res

    def write(self, vals):
        # Store the old state of each record before the write operation
        old_states = {record.id: record.state for record in self}
        
        if 'custom_write_date' not in vals:
            vals['custom_write_date'] = fields.Datetime.now()
        for obj in self: # For the moves that are created from Manual Payment/Miscellenous entry, when any change made for the Accounting Date (condition that its Payment entry's Adjust Carry fwd is not selected) then modify the invoice_date to its Accounting Date.
            if vals.get('date', False) and obj.move_type == 'entry' and not obj.payment_id.adjust_in_carry_fwd_bal:
                vals['invoice_date'] = vals['date']
        res = super(AccountMove, self).write(vals)
        # Check if the state has changed
        if 'state' in vals:
            new_state = vals['state']
            for record in self:
                old_state = old_states.get(record.id)
                payment_obj = record.payment_id
                if payment_obj:
                    if not payment_obj.old_state or payment_obj.old_state != old_state:
                        old_state_name = old_state.capitalize()
                        new_state_name = new_state.capitalize()
                        # Log message in the payment's chatter
                        message_body = _("Status: %(old_state)s -> %(new_state)s",
                                         old_state=old_state_name,
                                         new_state=new_state_name)
                        payment_obj.message_post(body=message_body, message_type='notification')

                        # Update the old_state in account.payment
                        payment_obj.write({'old_state': old_state})

        return res        
        
    def generate_xlsx_customized_report(self):
        return {
           'type': 'ir.actions.act_url',
           'url': '/invoicing/excel_report/%s' % (str(self.ids)),
           'target': 'new',
        }
    

    #Overriden the existing method to add the new field
    def _post(self, soft=True):
        if soft:
            # Filter moves that should auto-post later based on selection field
            future_moves = self.filtered(lambda move: move.date > fields.Date.context_today(self) and move.auto_post == 'at_date')
            future_moves.write({'auto_post': 'at_date'})
            for move in future_moves:
                msg = _('This move will be posted at the accounting date: %(date)s', date=format_date(self.env, move.date))
                move.message_post(body=msg)
            to_post = self - future_moves
        else:
            to_post = self

            
        installed = self.env['ir.module.module'].sudo().search([
            ('name', '=', 'metro_invoice_user'),
            ('state', '=', 'installed')
        ], limit=1)

        if installed:
            if not self.env.su and not (
                self.env.user.has_group('account.group_account_invoice') or
                self.env.user.has_group('metro_invoice_user.group_account_invoice_user'),
                self.env.user.has_group('metro_invoice_user.group_invoice_own_only'),
            ):
                raise AccessError(_("You don't have the access rights to post an invoice."))
        else:
            if not self.env.su and not self.env.user.has_group('account.group_account_invoice'):
                raise AccessError(_("You don't have the access rights to post an invoice."))

        for move in to_post:
            if move.partner_bank_id and not move.partner_bank_id.active:
                raise UserError(_("The recipient bank account link to this invoice is archived.\nSo you cannot confirm the invoice."))
            if move.state == 'posted':
                raise UserError(_('The entry %s (id %s) is already posted.') % (move.name, move.id))
            if not move.line_ids.filtered(lambda line: not line.display_type):
                raise UserError(_('You need to add a line before posting.'))
            
            # 🔁 Changed from auto_post == True to auto_post == 'at_date'
            if move.auto_post == 'at_date' and move.date > fields.Date.context_today(self):
                date_msg = move.date.strftime(get_lang(self.env).date_format)
                raise UserError(_("This move is configured to be auto-posted on %s", date_msg))

            if not move.partner_id:
                if move.is_sale_document():
                    raise UserError(_("The field 'Customer' is required, please complete it to validate the Customer Invoice."))
                elif move.is_purchase_document():
                    raise UserError(_("The field 'Vendor' is required, please complete it to validate the Vendor Bill."))

            if move.is_invoice(include_receipts=True) and float_compare(move.amount_total, 0.0, precision_rounding=move.currency_id.rounding) < 0:
                raise UserError(_("You cannot validate an invoice with a negative total amount. You should create a credit note instead. Use the action menu to transform it into a credit note or refund."))

            if move.line_ids.account_id.filtered(lambda account: account.deprecated):
                raise UserError(_("A line of this move is using a deprecated account, you cannot post it."))

            if not move.invoice_date:
                if move.is_sale_document(include_receipts=True):
                    move.invoice_date = fields.Date.context_today(self)
                    move.with_context(check_move_validity=False)._onchange_invoice_date()
                elif move.is_purchase_document(include_receipts=True):
                    raise UserError(_("The Bill/Refund date is required to validate this document."))

            if (move.company_id.tax_lock_date and move.date <= move.company_id.tax_lock_date) and (move.line_ids.tax_ids or move.line_ids.tax_tag_ids):
                move.date = move._get_accounting_date(move.invoice_date or move.date, True)
                move.with_context(check_move_validity=False)._onchange_currency()

        for move in to_post:
            wrong_lines = move.is_invoice() and move.line_ids.filtered(lambda aml: aml.partner_id != move.commercial_partner_id and not aml.display_type)
            if wrong_lines:
                wrong_lines.partner_id = move.commercial_partner_id.id

        to_post.mapped('line_ids').create_analytic_lines()
        to_post.write({
            'state': 'posted',
            'posted_before': True,
        })

        for move in to_post:
            move.message_subscribe([p.id for p in [move.partner_id] if p not in move.sudo().message_partner_ids])

        for move in to_post:
            if move.is_sale_document() \
                    and move.journal_id.sale_activity_type_id \
                    and (move.journal_id.sale_activity_user_id or move.invoice_user_id).id not in (self.env.ref('base.user_root').id, False):
                move.activity_schedule(
                    date_deadline=min((date for date in move.line_ids.mapped('date_maturity') if date), default=move.date),
                    activity_type_id=move.journal_id.sale_activity_type_id.id,
                    summary=move.journal_id.sale_activity_note,
                    user_id=move.journal_id.sale_activity_user_id.id or move.invoice_user_id.id,
                )

        customer_count, supplier_count = defaultdict(int), defaultdict(int)
        for move in to_post:
            if move.is_sale_document():
                customer_count[move.partner_id] += 1
            elif move.is_purchase_document():
                supplier_count[move.partner_id] += 1
        for partner, count in customer_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('customer_rank', count)
        for partner, count in supplier_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('supplier_rank', count)

        to_post.filtered(
            lambda m: m.is_invoice(include_receipts=True) and m.currency_id.is_zero(m.amount_total)
        ).action_invoice_paid()

        to_post._check_balanced()
        return to_post
    
    #Overriden the existing method to add the new field
    def button_cancel(self):
        # Set auto_post to 'no' when canceling the move, and change the state to 'cancel'
        self.write({'auto_post': 'no', 'state': 'cancel'})

    #Overriden the existing method to add the new field
    @api.model
    def _autopost_draft_entries(self):
        ''' This method is called from a cron job.
        It is used to post entries such as those created by the module
        account_asset.
        '''
        records = self.search([
            ('state', '=', 'draft'),
            ('date', '<=', fields.Date.context_today(self)),
            ('auto_post', '!=', 'no'),  # Modify this condition to check for 'at_date'
        ])

        for ids in self._cr.split_for_in_conditions(records.ids, size=100):
            moves = self.browse(ids)
            try:  # Try posting in batch
                with self.env.cr.savepoint():
                    moves._post()
            except UserError:  # If at least one move cannot be posted, handle moves one by one
                for move in moves:
                    try:
                        with self.env.cr.savepoint():
                            move._post()
                    except UserError as e:
                        move.to_check = True
                        msg = _('The move could not be posted for the following reason: %(error_message)s', error_message=e)
                        move.message_post(body=msg,
                                        message_type='comment',
                                        author_id=self.env.ref('base.partner_root').id)

            if not self.env.registry.in_test_mode():
                self._cr.commit()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    tax_amount_custom = fields.Monetary(
        string="Tax Amount",
        currency_field='company_currency_id',
        compute="_compute_tax_amount_custom",
        store=False   # keep it dynamic, or True if you want to store
    )

    @api.depends('price_total', 'price_subtotal')
    def _compute_tax_amount_custom(self):
        """
        On invoice lines, tax = price_total - price_subtotal
        On tax lines, tax = debit - credit
        """
        for line in self:
            tax_amount = 0.0
            if line.move_id and line.tax_ids:
                # get the taxes applied on this line
                tax_ids = line.tax_ids.ids
                # find matching tax lines inside move
                tax_lines = line.move_id.line_ids.filtered(
                    lambda l: l.tax_line_id and l.tax_line_id.id in tax_ids
                )
                if tax_lines:
                    # usually one tax per line, but could be multiple
                    tax_amount = sum(tax_lines.mapped('balance'))
            line.tax_amount_custom = abs(tax_amount)  # abs to make always positive
            
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """ Inherited Method """
        result = super(AccountMoveLine, self)._onchange_product_id()
        ctx = self._context

        valid_values = self.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids

        # WHEN Created the Invoice/Bill/Creditnotes/refunds manually/directly.
        if ctx.get('default_move_type') in ['out_invoice','out_refund']:
            if valid_values and (self.product_id.product_tmpl_id.product_variant_count > 1):
                return result
            if not self.product_id.description_sale:
                self.name = " "
            elif self.product_id.description_sale:
                description_sale = self.product_id.description_sale.strip()
                if not description_sale:
                    description_sale = " "
                self.name = description_sale
            return result
        elif ctx.get('default_move_type') in ['in_invoice','in_refund']:
            if valid_values and (self.product_id.product_tmpl_id.product_variant_count > 1):
                return result
            if not self.product_id.description_purchase:
                self.name = " "
            elif self.product_id.description_purchase:
                description_purchase = self.product_id.description_purchase.strip()
                if not description_purchase:
                    description_purchase = " "
                self.name = description_purchase
            return result

    #Existing method overriden to remove the currency empty error.
    @api.onchange('amount_currency')
    def _onchange_amount_currency(self):
        for line in self:
            company = line.move_id.company_id

            if line.currency_id and line.currency_id != company.currency_id:
                balance = line.currency_id._convert(
                    line.amount_currency,
                    company.currency_id,
                    company,
                    line.move_id.date or fields.Date.context_today(line)
                )
            else:
                balance = line.amount_currency

            line.debit = balance if balance > 0.0 else 0.0
            line.credit = -balance if balance < 0.0 else 0.0

            if not line.move_id.is_invoice(include_receipts=True):
                continue

            line.update(line._get_fields_onchange_balance())
            line.update(line._get_price_total_and_subtotal())






