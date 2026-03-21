# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import math

from dateutil import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import datetime
import calendar
from datetime import timedelta, date

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_interest_line = fields.Boolean('Is Interest Line')


class AccountMoves(models.Model):
    """ Extending model Invoice model to compute the interest amount for
    overdue invoices based on the chosen payment term configurations."""

    _inherit = "account.move"

    interest_amount = fields.Monetary(string='Interest Amount', readonly=True, copy=False)
    interest_overdue_act = fields.Boolean(related="invoice_payment_term_id"
                                                  ".interest_overdue_act")
    interest_calculated_period = fields.Char(string="Interest calculated date", copy=False)
    interest_type = fields.Selection(related="invoice_payment_term_id"
                                             ".interest_type")
    interest_percentage = fields.Float(related="invoice_payment_term_id"
                                               ".interest_percentage")

    # def get_period_time(self, today_date):
    #     """ Compute period duration based on Interest duration type. """
    #     self.ensure_one()
    #     r_obj = relativedelta. \
    #         relativedelta(today_date, self.invoice_date_due)
    #     print("r_obj =",r_obj)
    #     if self.invoice_payment_term_id.interest_type == 'monthly':
    #         period = (r_obj.years * 12) + r_obj.months
    #         if r_obj and r_obj.days > 0:
    #             period = period + 1
    #     elif self.invoice_payment_term_id.interest_type == 'weekly':
    #         period = math.ceil((today_date - self.invoice_date_due).days / 7)
    #     else: 
    #         period = (today_date - self.invoice_date_due).days
    #     return period

    def get_period_time(self, today_date):
        """ Compute period duration based on Interest duration type. """
        self.ensure_one()

        start_date = self.invoice_date_due
        end_date = today_date

        if self.invoice_payment_term_id.interest_type == 'monthly':
            # Ensure correct order
            if start_date > end_date:
                start_date, end_date = end_date, start_date

            # Exclude boundary dates
            start_date += timedelta(days=1)
            end_date -= timedelta(days=1)

            if start_date > end_date:
                return 0

            total_days = (end_date - start_date).days + 1

            def is_month_end(date_obj):
                """Returns True if date_obj is the last day of its month."""
                next_day = date_obj + timedelta(days=1)
                return next_day.day == 1
            
            month_end_count = sum(
                1 for i in range(total_days)
                if is_month_end(start_date + timedelta(days=i))
            )
            return month_end_count

        elif self.invoice_payment_term_id.interest_type == 'weekly':
            # Ensure start_date is before end_date
            if start_date > end_date:
                start_date, end_date = end_date, start_date

            # Shift the range to exclude the boundary dates
            start_date += timedelta(days=1)
            end_date -= timedelta(days=1)

            if start_date > end_date:
                return False  # No days in between

            total_days = (end_date - start_date).days + 1

            sunday_count = sum(
                1 for i in range(total_days)
                if (start_date + timedelta(days=i)).weekday() == 6
            )
            return sunday_count

        else: 
            period = (today_date - self.invoice_date_due).days
        return period

    def action_interest_compute(self):
        """ Action for computing Interest amount based on the chosen payment
        term configurations"""
        today_date = fields.Date.today()
        # today_date = datetime.date(2025, 8, 22)
        for rec in self:
            if rec.invoice_date_due \
                    and rec.invoice_date_due < today_date \
                    and rec.state == 'draft' \
                    and rec.move_type == 'out_invoice' \
                    and rec.interest_overdue_act \
                    and rec.invoice_payment_term_id.interest_percentage > 0:

                # If Fully Paid, then return back
                total_paid = rec.amount_total - rec.amount_residual
                if total_paid >= rec.amount_total:
                    continue

                period = rec.get_period_time(today_date)
                if not period:
                    continue
                end_date = today_date

                if rec.invoice_payment_term_id.interest_type == 'monthly':
                    if rec.interest_calculated_period and rec.interest_calculated_period == str(period) + "-m":
                        raise ValidationError(_('Your payment term is monthly, and you can update '
                                                'it only once in a month.'))
                     
                    else:
                        # last_day = calendar.monthrange(rec.invoice_date_due.year, rec.invoice_date_due.month)[1]
                        # end_date = date(rec.invoice_date_due.year, rec.invoice_date_due.month, last_day)
                        # if end_date <= today_date:
                        rec.interest_calculated_period = str(period) + "-m"
                elif rec.invoice_payment_term_id.interest_type == 'weekly':
                    if rec.interest_calculated_period and rec.interest_calculated_period == str(period) + "-w":
                        raise ValidationError(_('Your payment term is weekly, and you can update it only '
                                                'once in a week.'))
                    else:
                        # weekday = rec.invoice_date_due.weekday()
                        # days_to_sunday = 6 - weekday
                        # end_date = rec.invoice_date_due + timedelta(days=days_to_sunday)
                        # if end_date <= today_date:
                        rec.interest_calculated_period = str(period) + "-w"
                else:
                    if rec.interest_calculated_period and rec.interest_calculated_period == str(period) + "-d":
                        raise ValidationError(_('Your payment term is daily, and you can update it only '
                                                'once in a day.'))
                    else:                        
                        rec.interest_calculated_period = str(period) + "-d"

                interest_line = rec.invoice_line_ids.search(
                    [('is_interest_line', '=', True),
                     ('move_id', '=', rec.id)],
                    limit=1)
                if interest_line:
                    rec.invoice_line_ids = ([(2, interest_line.id, 0)])
                
                rec.interest_amount = (rec.amount_total) * rec \
                    .invoice_payment_term_id.interest_percentage * period / 100
                vals = {'name': 'Interest Amount for Overdue - ' + end_date.strftime('%d/%B/%Y'),
                        'price_unit': rec.interest_amount,
                        'quantity': 1,
                        'is_interest_line': True
                        }
                if rec.invoice_payment_term_id.interest_account_id:
                    vals.update({
                        'account_id': rec.invoice_payment_term_id
                        .interest_account_id})
                if rec.interest_amount > 0:
                    rec.invoice_line_ids = ([(0, 0, vals)])
            elif rec.interest_amount > 0:
                rec.action_interest_reset()

    def _get_interest_check(self):
        """ Method for Interest computation via scheduled action """

        today_date = fields.Date.today()
        # today_date = datetime.date(2025, 9, 22)

        for rec in self.sudo().search([('state', 'in', ['draft','posted']),('id','>',49)]):
            if rec.invoice_date_due and rec.invoice_date_due < today_date \
                    and rec.move_type == 'out_invoice' \
                    and rec.interest_overdue_act \
                    and rec.invoice_payment_term_id.interest_percentage > 0:

                # If Fully Paid, then return back
                total_paid = rec.amount_total - rec.amount_residual
                if total_paid >= rec.amount_total:
                    continue

                period = rec.get_period_time(today_date)
                if not period:
                    continue
                end_date = today_date

                if rec.invoice_payment_term_id.interest_type == 'monthly':
                    if rec.interest_calculated_period \
                            and rec.interest_calculated_period == str(period) \
                            + "-m":
                        continue
                    else:
                        rec.interest_calculated_period = str(period) + "-m"
                elif rec.invoice_payment_term_id.interest_type == 'weekly':
                    if rec.interest_calculated_period \
                            and rec.interest_calculated_period == str(period) \
                            + "-w":
                        continue
                    else:
                        rec.interest_calculated_period = str(period) + "-w"
                else:
                    if rec.interest_calculated_period \
                            and rec.interest_calculated_period == str(period) \
                            + "-d":
                        continue
                    else:
                       rec.interest_calculated_period = str(period) + "-d"

                repost = False
                interest_line = rec.sudo().invoice_line_ids.search(
                    [('is_interest_line', '=', True),
                     ('move_id', '=', rec.id)], limit=1)

                if interest_line:
                    if rec.state == 'posted':
                        rec.sudo().button_draft()
                        rec.sudo().message_post(body="Invoice reset to draft to update the Interest Amount. This is a system performed action.")
                        repost = True
                    rec.sudo().invoice_line_ids = ([(2, interest_line.id, 0)])

                rec.interest_amount = rec.amount_total * rec \
                    .invoice_payment_term_id.interest_percentage * period / 100

                vals = {'name': 'Interest Amount for Overdue - ' + end_date.strftime('%d/%B/%Y'),
                        'price_unit': rec.interest_amount,
                        'quantity': 1,
                        'is_interest_line': True
                        }
                if rec.invoice_payment_term_id.interest_account_id:
                    vals.update({
                        'account_id': rec.invoice_payment_term_id.interest_account_id})
                if rec.interest_amount > 0:
                    rec.sudo().invoice_line_ids = ([(0, 0, vals)])
                if repost:
                    rec.sudo().action_post()

            elif rec.interest_amount > 0:
                rec.action_interest_reset()

    def action_interest_reset(self):
        """Method for resetting the interest lines and Interest amount in
        Invoice"""
        self.interest_amount = 0
        interest_line = self.invoice_line_ids.search(
            [('is_interest_line', '=', True),
             ('move_id', '=', self.id)], limit=1)
        if interest_line:
            if self.state == 'posted':
                self.sudo().button_draft()
                self.sudo().message_post(body="Invoice reset to draft to delete the Interest Amount. This is a system performed action.")
                repost = True
            self.invoice_line_ids = ([(2, interest_line.id, 0)])
        self.interest_calculated_period = False

    @api.onchange('invoice_payment_term_id', 'invoice_line_ids',
                  'invoice_date_due')
    def _onchange_invoice_payment_term_id(self):
        """Method for removing interest from Invoice when user changes dependent
            values of interest."""
        for rec in self:
            if rec.move_type == 'out_invoice':
                rec.interest_amount = 0
                interest_line = rec.invoice_line_ids.search(
                    [('is_interest_line', '=', True)], limit=1)
                if interest_line:
                    rec.invoice_line_ids = ([(2, interest_line.id, 0)])
                rec.interest_calculated_period = False
            return
