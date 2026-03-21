from odoo import api, fields, models, _

class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = ['account.payment','portal.mixin']

    
    partner_type = fields.Selection([
        ('customer', 'Payer'),
        ('supplier', 'Payee'),
    ], default='customer', tracking=True, required=True)

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Payer/Payee",
        tracking=True,
        store=True, readonly=False, ondelete='restrict',
        compute='_compute_partner_id',
        domain="['|', ('parent_id','=', False), ('is_company','=', True)]",
        check_company=True)
    
    payment_type = fields.Selection([
        ('outbound', 'Send Money'),
        ('inbound', 'Receive Money'),
    ], string='Payment Type',tracking=True, default='inbound', required=True)

    is_internal_transfer = fields.Boolean(string="Is Internal Transfer",
        readonly=False, store=True,tracking=True,
        compute="_compute_is_internal_transfer")
    
    destination_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Destination Account',
        store=True, readonly=False,
        tracking=True,
        compute='_compute_destination_account_id',
        domain="[('user_type_id.type', 'in', ('receivable', 'payable')), ('company_id', '=', company_id)]",
        check_company=True)
    
    amount = fields.Monetary(currency_field='currency_id',tracking=True)

    partner_bank_id = fields.Many2one('res.partner.bank', string="Recipient Bank Account",
        readonly=False, store=True,
        compute='_compute_partner_bank_id',
        domain="[('id', 'in', available_partner_bank_ids)]",
        check_company=True,tracking=True)

    currency_id = fields.Many2one('res.currency', string='Currency', store=True, readonly=False,
        compute='_compute_currency_id', tracking=True,
        help="The payment's currency.")

    old_state =  fields.Char(string="Old State (Technical)", help="This field stores the old state of the form and this field application is defined in the account.move.py of this module.")


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    payment_date = fields.Date(
        string='Payment Date',
        default=lambda self: self._get_default_payment_date()
    )

    @api.model
    def _get_default_payment_date(self):
        # Context should provide the active_ids which are the invoices selected
        active_ids = self._context.get('active_ids', [])
        invoices = self.env['account.move'].browse(active_ids)

        # If there are invoices, set the payment date to the first invoice date
        if invoices and invoices.journal_id.type == 'sale' and invoices.company_id.order_date_same_as_quotation_date:
            return invoices[0].invoice_date
        elif invoices and invoices.journal_id.type == 'purchase' and invoices.company_id.confirmation_date_same_as_order_deadline:
            return invoices[0].invoice_date

        return fields.Date.context_today(self)
