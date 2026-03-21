from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError
import calendar
from odoo.exceptions import UserError, ValidationError


from odoo import api, fields, models

class CustomerMonthlyStatementWizard(models.TransientModel):
    _name = 'customer.monthly.statement.wizard'
    _description = 'Customer Monthly Statement Wizard'

    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    partner_id = fields.Many2one('res.partner', 'Partner')

    @api.constrains('date_from')
    def _onchange_date(self):
        date_from = fields.Date.from_string(self.date_from)
        if not date_from.day == 1:
            raise ValidationError("You can set only 1 day for any Month!")

    def generate_report(self):
        account_invoice_obj = self.env['account.move']
        account_payment_obj = self.env['account.payment']
        statement_line_obj = self.env['monthly.statement.line']
        month_name = calendar.month_name[self.date_from.month] or False
        self.partner_id.write({'month_start_date': self.date_from, 'month_end_date': self.date_to, 'month_name': month_name})
        # domain = [('move_type', 'in', ['out_invoice','out_refund']), ('state', 'in', ['posted'])] 
        # if self.date_from:
        #     domain.append(('invoice_date', '>=', self.date_from))
        # if self.date_to:
        #     domain.append(('invoice_date', '<=', self.date_to))
        # lines_to_be_delete = statement_line_obj.search([('partner_id', '=', self.partner_id.id)]).unlink()
        
        # invoices = account_invoice_obj.search(domain)
        # for invoice in invoices.sorted(key=lambda r: (r.invoice_date, r.name)):
        #     vals = {
        #         'partner_id': invoice.partner_id.id or False,
        #         'state': invoice.state or False,
        #         'invoice_date': invoice.invoice_date,
        #         'invoice_date_due': invoice.invoice_date_due,
        #         'result': invoice.result or 0.0,
        #         'name': invoice.name or '',
        #         'amount_total': invoice.amount_total or 0.0,
        #         'credit_amount': invoice.credit_amount or 0.0,
        #         'invoice_id': invoice.id,
        #     }
        #     ob = statement_line_obj.create(vals)
        if self.date_from and self.date_to:
            return self.env.ref('account_statement.report_customer_monthly_print').report_action(self.partner_id)

    #TODO
    def generate_report_supplier(self):
        pass
        
    @api.onchange('date_from')
    def _onchange_date_from_date_to(self):
        date_from = fields.Date.from_string(self.date_from)
        year = date_from.year
        month = date_from.month
        if date_from:
            last_day = calendar.monthrange(year, month)[1]
            self.date_to = fields.Date.to_string(date_from.replace(day=last_day))
