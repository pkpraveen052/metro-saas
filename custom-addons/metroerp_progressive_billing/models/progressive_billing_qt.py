from docutils.nodes import comment
from reportlab.lib.pdfencrypt import computeO

from odoo import models, fields, api, _,SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from functools import partial
from odoo.tools.misc import formatLang, get_lang
import base64
import logging

_logger = logging.getLogger(__name__)

class ProgressiveBillingQt(models.Model):
    _name = "progressive.billing.qt"
    _description = "Progressive Billing Quotation"
    _order = 'date_order desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin','portal.mixin','utm.mixin']

    def _default_validity_date(self):
        if self.env['ir.config_parameter'].sudo().get_param('sale.use_quotation_validity_days'):
            days = self.env.company.quotation_validity_days
            if days > 0:
                return fields.Date.to_string(datetime.now() + timedelta(days))
        return False

    @api.model
    def _default_note(self):
        return self.env.company.use_sales_tc and self.env.company.sales_tc or ''


    @api.model
    def default_get(self, fields):
        rec = super(ProgressiveBillingQt, self).default_get(fields)
        pricelist_id = self.env['product.pricelist'].sudo().search([('company_id', '=', self.env.company.id)], limit=1)
        if pricelist_id:
            rec['pricelist_id'] = pricelist_id.id
        else:
            rec['pricelist_id'] = False
        return rec
    
#Dhaneswar method added below======================
    def _get_default_require_signature(self):
        return self.env.company.portal_confirmation_sign

    def _get_default_require_payment(self):
        return self.env.company.portal_confirmation_pay
#========================================================

    name = fields.Char(string='Order Reference', required=True, copy=False, default='New')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        required=True, tracking=1, domain = "['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    partner_invoice_id = fields.Many2one(
        'res.partner', string='Invoice Address', required=True, domain = "['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    date_order = fields.Datetime(string='Order Date', required=True, readonly=True, index=True, copy=False,
                                 default=fields.Datetime.now,
                                 help="Creation date of draft/sent orders,\nConfirmation date of confirmed orders.")
    validity_date = fields.Date(string='Expiration', readonly=True, copy=False,
                                states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                                default=_default_validity_date)
    payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Terms', domain = "['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    # domain = "['|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    progressive_billing_lines_ids = fields.One2many('progressive.billing.qt.lines', 'progressive_billing_qt_id',
                                                    string="Progressive Billing Lines")
    invoice_count = fields.Integer(string='Invoice Count', compute='_get_invoiced', readonly=True)
    partner_shipping_id = fields.Many2one(
        'res.partner', string='Delivery Address', readonly=True, required=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'sale': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', check_company=True,  # Unrequired company
        readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=1,
        help="If you change the pricelist, only newly added lines will be affected.")
    currency_id = fields.Many2one(related='pricelist_id.currency_id', depends=["pricelist_id"], store=True)
    sale_order_template_id = fields.Many2one(
        'sale.order.template', 'Quotation Template',
        readonly=True, check_company=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    note = fields.Text('Terms and conditions', default=_default_note)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', tracking=5)
    amount_by_group = fields.Binary(string="Tax amount by group", compute='_amount_by_group', help="type: [(name, amount, base, formated amount, formated base)]")
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', tracking=4)
    total_amount_in_words = fields.Text(string='Total Amount (In Words)', compute="_set_amount_total_in_words")
    is_fully_paid = fields.Boolean('IS Fully Paid', default=False, copy=False)

#Dhaneswar fields added below=========================================================
    description = fields.Char(string="Description")
    reference = fields.Char(string="Your Reference")

    use_assistro = fields.Boolean(related="company_id.use_assistro",string="Use Assistro",readonly=True)

    type_name = fields.Char('Type Name', compute='_compute_type_name')

    validity_date = fields.Date(string='Expiration', readonly=True, copy=False, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                                default=_default_validity_date)

    is_expired = fields.Boolean(compute='_compute_is_expired', string="Is expired")
    require_signature = fields.Boolean('Online Signature', default=_get_default_require_signature, readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        help='Request a online signature to the customer in order to confirm orders automatically.')
    require_payment = fields.Boolean('Online Payment', default=_get_default_require_payment, readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        help='Request an online payment to the customer in order to confirm orders automatically.')
    create_date = fields.Datetime(string='Creation Date', readonly=True, index=True, help="Date on which sales order is created.")

    user_id = fields.Many2one(
        'res.users', string='Salesperson', index=True, tracking=2, default=lambda self: self.env.user,
        domain=lambda self: "[('groups_id', '=', {}), ('share', '=', False), ('company_ids', '=', company_id)]".format(
            self.env.ref("sales_team.group_sale_salesman").id
        ),)
    
    signature = fields.Image('Signature', help='Signature received through the portal.', copy=False, attachment=True, max_width=1024, max_height=1024)
    signed_by = fields.Char('Signed By', help='Name of the person that signed the SO.', copy=False)
    signed_on = fields.Datetime('Signed On', help='Date of the signature.', copy=False)
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Analytic Account',
        compute='_compute_analytic_account_id', store=True,
        readonly=False, copy=False, check_company=True,  # Unrequired company
        states={'sale': [('readonly', True)], 'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="The analytic account related to a sales order.")
    
    #has doubts on this fields, this fields used in customer portal
    transaction_ids = fields.Many2many(
        'payment.transaction',
        'progressive_billing_transaction_rel',
        'pbilling_id',  
        'transaction_id',  
        string='Transactions',
        copy=False,
        readonly=True
    )
    authorized_transaction_ids = fields.Many2many('payment.transaction', compute='_compute_authorized_transaction_ids',
                                                  string='Authorized Transactions', copy=False, readonly=True)

    #has doubts on this fields, used in portal templates
    invoice_ids = fields.Many2many("account.move", string='Invoices', readonly=True, copy=False)
    pending_claim_total  = fields.Monetary(string='Total Pending Claim', readonly=True, store=True, compute='_compute_total_pending_claim', copy=False)
    pending_claim_note = fields.Char(string="Pending Claim Note", compute="_compute_pending_claim_note")


    def copy_data(self, default=None):
        if default is None:
            default = {}
        if 'order_line' not in default:
            default['progressive_billing_lines_ids'] = [(0, 0, line.copy_data()[0]) for line in
                                     self.progressive_billing_lines_ids]
        return super(ProgressiveBillingQt, self).copy_data(default)

    def _amount_by_group(self):
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            fmt = partial(formatLang, self.with_context(lang=order.partner_id.lang).env, currency_obj=currency)
            res = {}
            for line in order.progressive_billing_lines_ids:
                price_reduce = line.price_unit * (1.0 - line.discount / 100.0)
                taxes = line.tax_id.compute_all(price_reduce, quantity=line.product_uom_qty, product=line.product_id, partner=order.partner_shipping_id)['taxes']
                for tax in line.tax_id:
                    group = tax.tax_group_id
                    res.setdefault(group, {'amount': 0.0, 'base': 0.0})
                    for t in taxes:
                        if t['id'] == tax.id or t['id'] in tax.children_tax_ids.ids:
                            res[group]['amount'] += t['amount']
                            res[group]['base'] += t['base']
            res = sorted(res.items(), key=lambda l: l[0].sequence)

            # round amount and prevent -0.00
            for group_data in res:
                group_data[1]['amount'] = currency.round(group_data[1]['amount']) + 0.0
                group_data[1]['base'] = currency.round(group_data[1]['base']) + 0.0

            order.amount_by_group = [(
                l[0].name, l[1]['amount'], l[1]['base'],
                fmt(l[1]['amount']), fmt(l[1]['base']),
                len(res),
            ) for l in res]


    @api.depends('progressive_billing_lines_ids.price_subtotal', 'progressive_billing_lines_ids.pending_claim_amount')
    def _compute_total_pending_claim(self):
        for order in self:
            order.pending_claim_total = sum(order.progressive_billing_lines_ids.mapped('pending_claim_amount'))

    @api.depends('pending_claim_total')
    def _compute_pending_claim_note(self):
        for order in self:
            has_issue = any(
                (line.pending_claim_amount < 0.0 or line.pending_claim_amount > 0.0)  # Less than or greater than 0.0
                and line.progress == 1.0
                and line.is_paid
                for line in order.progressive_billing_lines_ids
            )
            if has_issue:
                order.pending_claim_note = f"Note: The pending claim amount has a minor difference.Please review before finalizing."
            else:
                order.pending_claim_note = ""

    @api.depends('partner_id', 'date_order')
    def _compute_analytic_account_id(self):
        for order in self:
            if not order.analytic_account_id:
                default_analytic_account = order.env['account.analytic.default'].sudo().account_get(
                    partner_id=order.partner_id.id,
                    user_id=order.env.uid,
                    date=order.date_order,
                    company_id=order.company_id.id,
                )
                order.analytic_account_id = default_analytic_account.analytic_id

    @api.depends('transaction_ids')
    def _compute_authorized_transaction_ids(self):
        for trans in self:
            trans.authorized_transaction_ids = trans.transaction_ids.filtered(lambda t: t.state == 'authorized')

    @api.depends('state')
    def _compute_type_name(self):
        for record in self:
            record.type_name = _('Progressive Billing Quotation') if record.state in ('draft', 'sent', 'cancel') else _('Progressive Billing Sales Order')

    def _compute_amount_undiscounted(self):
        for order in self:
            total = 0.0
            for line in order.progressive_billing_lines_ids:
                total += (line.price_subtotal * 100)/(100-line.discount) if line.discount != 100 else (line.price_unit * line.product_uom_qty)
            order.amount_undiscounted = total

    #has doubts on this fields, used in portal templates
    amount_undiscounted = fields.Float('Amount Before Discount', compute='_compute_amount_undiscounted', digits=0)

    def _is_fully_paid(self):
        for rec in self:
            billing_line = all(line.is_paid for line in rec.progressive_billing_lines_ids)
            if billing_line:
                rec.is_fully_paid = True
            else:
                rec.is_fully_paid = False

    @api.depends('amount_total')
    def _set_amount_total_in_words(self):
        for rec in self:
            if rec.currency_id:
                rec.total_amount_in_words = rec.currency_id.amount_to_text(rec.amount_total, rec.partner_id.lang)
            else:
                rec.total_amount_in_words = ''

    @api.depends('progressive_billing_lines_ids.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.progressive_billing_lines_ids:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

    def _get_invoiced(self):
        for rec in self:
            order_responses_count = self.env['account.move'].search_count(
                [('progressive_billing_qt_id', '=', rec.id)])
            rec.invoice_count = order_responses_count

    def action_view_invoice(self):
        invoices = self.env['account.move'].search([('progressive_billing_qt_id', '=', self.id)])
        action = {
            'name': 'Progressive Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', invoices.ids)],
            'views': [(self.env.ref('metroerp_progressive_billing.view_progressive_invoice_tree').id, 'tree'),
                      (self.env.ref('account.view_move_form').id, 'form')],
        }
        if len(invoices) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': invoices.id,
            })
        return action

    @api.model
    def create(self, vals):
        if vals.get('name', ('New')) == ('New'):
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code('progressive.billing.qt') or ('New')
        return super(ProgressiveBillingQt, self).create(vals)

    # prakash comment
    # def action_confirm(self):
    #     for order in self:
    #         order.order_line.write({'is_confirm': True})
    #         self.write({
    #             'state': 'sale',
    #             'date_order': fields.Datetime.now()
    #         })

    def action_create_invoice(self):
        last_invoice = self.env['account.move'].search([('progressive_billing_qt_id', '=', self.id)], order="id desc", limit=1)
        if last_invoice and last_invoice.is_posted != True and last_invoice.state == 'draft':
            raise ValidationError(_("The previous invoice (Invoice No: %s) must be confirmed before creating a new one.") % last_invoice.claim_no)
        elif last_invoice and last_invoice.state == 'draft' and last_invoice.is_posted != False:
            raise ValidationError(_("The previous invoice (Invoice No: %s) must be canceled before creating a new one.") % last_invoice.claim_no)

        lines = self.progressive_billing_lines_ids
        zero_progress_lines = [line for line in lines if line.progress == 0 and line.old_progress == 0]
        fully_paid_lines = [line for line in lines if line.is_paid]
        in_progress_lines = [line for line in lines if line.progress != 0 and not line.is_paid]

        if len(zero_progress_lines) == len(lines) and len(lines) > 1:
            raise ValidationError(_("Please set progress before proceeding."))
        if len(lines) == 1 and zero_progress_lines:
            raise ValidationError(_("Please set progress before proceeding."))
        if fully_paid_lines and zero_progress_lines and not in_progress_lines:
            raise ValidationError(_("Please set progress before proceeding."))


        narration = False
        company = self.env.company

        if company.use_sales_invoice_tc:
            if company.sales_invoice_tc:
                narration = company.sales_invoice_tc
            else:
                narration = self.note 

        invoice_vals = {
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.context_today(self),
            'is_progressive_invoice': True,
            'partner_shipping_id': self.partner_shipping_id.id,
            'invoice_line_ids': [],
            'description': self.description,
            'reference': self.reference,
            'narration': narration,
        }
        for line in self.progressive_billing_lines_ids:
            if line.progress < line.old_progress:
                raise ValidationError(_("The Progress must be above %s%%") % int(line.old_progress * 100))
            if line.old_progress > 0.0 and line.progress > 0.0:
                price_unit = (line.progress - line.old_progress) * line.price_unit
            else:
                price_unit = line.price_unit * line.progress
            dict = {
                'product_id': line.product_id.id,
                'quantity': line.product_uom_qty,
                'price_unit': price_unit,
                'product_uom_id': line.product_uom.id,
                'name': line.name,
                'display_type': line.display_type,
                'progress': line.progress,
                'old_progress': line.old_progress,
                'progressive_billing_qt_line_id': line.id,
                # 'remaining_amount': total_remaining_amount,
                'tax_ids': [(6, 0, line.tax_id.ids)],
                'qt_total': line.price_subtotal,
            }
            invoice_vals['invoice_line_ids'].append((0, 0, dict))
        invoice = self.env['account.move'].create(invoice_vals)
        existing_invoices = self.env['account.move'].search_count([('progressive_billing_qt_id', '=', self.id), ('state', '!=', 'cancel')])
        if existing_invoices > 0:
            previous_invoice = self.env['account.move'].search([('claim_no', '=', existing_invoices), ('progressive_billing_qt_id', '=', self.id)])
            invoice.previous_invoice_id = previous_invoice.id
        new_claim_no = existing_invoices + 1
        invoice.claim_no = new_claim_no
        invoice.progressive_billing_qt_id = self.id
        return {
            'name': 'Invoice',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'type': 'ir.actions.act_window',
        }
    #dhaneswar commented thsi method
    # def action_cancel(self):
    #     print('\n\n\n\nself', self)



    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
            })
            return
        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        self.update(values)

    def unlink(self):
        for order in self:
            if order.state not in ('draft', 'cancel'):
                raise UserError(
                    _('You can not delete a sent quotation or a confirmed order. You must first cancel it.'))
        return super(ProgressiveBillingQt, self).unlink()

    def _compute_line_data_for_template_change(self, line):
        return {
            'display_type': line.display_type,
            'name': line.name,
            # 'state': 'draft',
        }

    @api.onchange('sale_order_template_id')
    def onchange_sale_order_template_id(self):
        template = self.sale_order_template_id.with_context(lang=self.partner_id.lang)
        if template:
            order_lines = [(5, 0, 0)]
            for line in template.sale_order_template_line_ids:
                data = self._compute_line_data_for_template_change(line)

                if line.product_id:
                    price = line.product_id.list_price
                    data.update({
                        'price_unit': price,
                        # 'discount': discount,
                        'product_uom_qty': line.product_uom_qty,
                        'product_id': line.product_id.id,
                        'product_uom': line.product_uom_id.id,
                        # 'customer_lead': self._get_customer_lead(line.product_id.product_tmpl_id),
                    })

                order_lines.append((0, 0, data))
            self.progressive_billing_lines_ids = order_lines

#=============================Dhaneswar code start here================================================================================

    def action_cancel(self):
        cancel_warning = self._show_cancel_wizard()
        if cancel_warning:
            return {
                'name': _('Cancel Progressive Billing Sales Order'),
                'view_mode': 'form',
                'res_model': 'progressive.billing.cancel',
                'view_id': self.env.ref('metroerp_progressive_billing.progressive_billing_cancel_view_form').id,
                'type': 'ir.actions.act_window',
                'context': {'default_order_id': self.id},
                'target': 'new'
            }
        return self._action_cancel()

    def _action_cancel(self):
        inv = self.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        inv.button_cancel()
        return self.write({'state': 'cancel'})

    def _show_cancel_wizard(self):
        for order in self:
            if order.invoice_ids.filtered(lambda inv: inv.state == 'draft') and not order._context.get('disable_cancel_warning'):
                return True
        return False

    def _prepare_confirmation_values(self):
        return {
            'state': 'sale',
            'date_order': fields.Datetime.now()
        }
    
    def _prepare_analytic_account_data(self, prefix=None):
        """
        Prepare method for analytic account data

        :param prefix: The prefix of the to-be-created analytic account name
        :type prefix: string
        :return: dictionary of value for new analytic account creation
        """
        name = self.name
        if prefix:
            name = prefix + ": " + self.name
        return {
            'name': name,
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id
        }
    
    def _create_analytic_account(self, prefix=None):
        for order in self:
            analytic = self.env['account.analytic.account'].create(order._prepare_analytic_account_data(prefix))
            order.analytic_account_id = analytic

    def _action_confirm(self):
        """ Implementation of additionnal mecanism of Sales Order confirmation.
            This method should be extended when the confirmation should generated
            other documents. In this method, the SO are in 'sale' state (not yet 'done').
        """
        # create an analytic account if at least an expense product
        for order in self:
            if any(expense_policy not in [False, 'no'] for expense_policy in order.progressive_billing_lines_ids.mapped('product_id.expense_policy')):
                if not order.analytic_account_id:
                    order._create_analytic_account()

        return True


    def action_confirm(self):
        if self._get_forbidden_state_confirm() & set(self.mapped('state')):
            raise UserError(_(
                'It is not allowed to confirm an order in the following states: %s'
            ) % (', '.join(self._get_forbidden_state_confirm())))

        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])
        self.write(self._prepare_confirmation_values())
        self.progressive_billing_lines_ids.write({'is_confirm': True})

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)

        self.with_context(context)._action_confirm()
        if self.env.user.has_group('sale.group_auto_done_setting'):
            self.action_done()
        return True
    
    def _get_forbidden_state_confirm(self):
        return {'done', 'cancel'}

    def _find_mail_template(self, force_confirmation_template=False):
        self.ensure_one()
        template_id = False

        if force_confirmation_template or (self.state == 'sale'):
            template_id = int(self.env['ir.config_parameter'].sudo().get_param('metroerp_progressive_billing.default_progressive_billing_confirmation_template'))
            template_id = self.env['mail.template'].search([('id', '=', template_id)]).id
            if not template_id:
                template_id = self.env['ir.model.data'].xmlid_to_res_id('metroerp_progressive_billing.mail_template_progressive_billing_confirmation', raise_if_not_found=False)
        if not template_id:
            template_id = self.env['ir.model.data'].xmlid_to_res_id('metroerp_progressive_billing.email_template_edi_progressive_billing', raise_if_not_found=False)

        return template_id

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        """Override to change state to 'sent' when sending an email."""
        if self.env.context.get('mark_so_as_sent'):
            self.filtered(lambda o: o.state == 'draft').with_context(tracking_disable=True).write({'state': 'sent'})
        return super(ProgressiveBillingQt, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)

    
    def action_billing_quotation_send(self):
        ''' Opens a wizard to compose an email, with relevant mail template loaded by default '''
        self.ensure_one()
        template_id = self._find_mail_template()
        lang = self.env.context.get('lang')
        template = self.env['mail.template'].browse(template_id)
        if template.lang:
            lang = template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'progressive.billing.qt',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "mail.mail_notification_paynow",
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': self.with_context(lang=lang).type_name,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }
    

    REPORT_MAPPING = {
        "progressive.billing.qt": "ks_custom_report_layouts.action_ks_pro_billl_quotation_report",
    }

    def action_open_whatsapp_composer(self):
        """Opens the WhatsApp message composer wizard and attaches the PDF."""
        self.ensure_one()
        
        pdf_attachment = None
        if self._name in self.REPORT_MAPPING:
            try:
                report_action = self.env.ref(self.REPORT_MAPPING[self._name])
                pdf_content, _ = report_action._render_qweb_pdf(self.id)
                pdf_base64 = base64.b64encode(pdf_content)
                file_name = f"{self.name.replace('/', '_')}.pdf"
        
                # ✅ Create the attachment
                pdf_attachment = self.env['ir.attachment'].create({
                    'name': file_name,
                    'type': 'binary',
                    'datas': pdf_base64,
                    'res_model': self._name,
                    'res_id': self.id,
                    'mimetype': 'application/pdf',
                })
        
                _logger.info(f"✅ PDF attachment created: {pdf_attachment.name} (ID: {pdf_attachment.id})")
        
            except Exception as e:
                _logger.error(f"❌ Failed to generate PDF for {self._name} ({self.id}): {str(e)}")

        # ✅ Open the wizard and link the attachment
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send WhatsApp Message',
            'res_model': 'whatsapp.composer',
            'view_mode': 'form',
            'view_id': False,
            'target': 'new',
            'context': {
                'default_active_model': self._name,
                'default_active_id': self.id,
                'default_attachment_ids': [(6, 0, [pdf_attachment.id])] if pdf_attachment else False,
                'default_template_id': self.env['assistro.whatsapp.template'].search([('is_default', '=', True)], limit=1).id,
            },
        }
        

    def action_open_web_whatsapp_composer(self):
        """Opens the Web WhatsApp message composer wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send WhatsApp Message',
            'res_model': 'portal.share',
            'view_mode': 'form',
            'view_id': False,
            'target': 'new',
            'context': {
                'default_active_model': self._name,
                'default_active_id': self.id,
            },
        }





#dhaneswar Customer Preview code start from here================================================

    def preview_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }
    
    def action_done(self):
        for order in self:
            tx = order.sudo().transaction_ids.get_last_transaction()
            if tx and tx.state == 'pending' and tx.acquirer_id.provider == 'transfer':
                tx._set_transaction_done()
                tx.write({'is_processed': True})
        return self.write({'state': 'done'})
    
    def get_portal_last_transaction(self):
        self.ensure_one()
        return self.transaction_ids.get_last_transaction()
    

    def has_to_be_paid(self, include_draft=False):
        transaction = self.get_portal_last_transaction()
        return (self.state == 'sent' or (self.state == 'draft' and include_draft)) and not self.is_expired and self.require_payment and transaction.state != 'done' and self.amount_total
    
    def has_to_be_signed(self, include_draft=False):
        return (self.state == 'sent' or (self.state == 'draft' and include_draft)) and not self.is_expired and self.require_signature and not self.signature

    def _compute_access_url(self):
        super(ProgressiveBillingQt, self)._compute_access_url()
        for order in self:
            order.access_url = '/my/billing_orders/%s' % (order.id)


    def _compute_is_expired(self):
        today = fields.Date.today()
        for order in self:
            order.is_expired = order.state == 'sent' and order.validity_date and order.validity_date < today
    
    def _get_portal_return_action(self):
        """ Return the action used to display orders when returning from customer portal. """
        self.ensure_one()
        return self.env.ref('metroerp_progressive_billing.progressive_billing_action_window')
    

    def _send_order_confirmation_mail(self):
        if self.env.su:
            # sending mail in sudo was meant for it being sent from superuser
            self = self.with_user(SUPERUSER_ID)
        for order in self:
            template_id = order._find_mail_template(force_confirmation_template=True)
            if template_id:
                order.with_context(force_send=True).message_post_with_template(template_id, composition_mode='comment', email_layout_xmlid="mail.mail_notification_paynow")


    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s %s' % (self.type_name, self.name)
