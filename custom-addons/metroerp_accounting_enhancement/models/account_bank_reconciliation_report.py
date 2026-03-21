# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import ast

from odoo import models, fields, api, _
from odoo.tools.misc import format_date
import ast
import copy
import json
import io
import logging
import lxml.html
import datetime
import ast
from collections import defaultdict
from math import copysign

from dateutil.relativedelta import relativedelta

from odoo.tools.misc import xlsxwriter
from odoo import models, fields, api, _
from odoo.tools import config, date_utils, get_lang
from odoo.osv import expression
from babel.dates import get_quarter_names
from odoo.tools.misc import formatLang, format_date
from odoo.addons.web.controllers.main import clean_action


_logger = logging.getLogger(__name__)

class AccountReportManager(models.Model):
    _name = 'account.report.manager'
    _description = 'Manage Summary and Footnotes of Reports'

    # must work with multi-company, in case of multi company, no company_id defined
    report_name = fields.Char(required=True, help='name of the model of the report')
    summary = fields.Char()
    footnotes_ids = fields.One2many('account.report.footnote', 'manager_id')
    company_id = fields.Many2one('res.company')
    financial_report_id = fields.Many2one('account.financial.html.report')

    def add_footnote(self, text, line):
        return self.env['account.report.footnote'].create({'line': line, 'text': text, 'manager_id': self.id})

class AccountReportFootnote(models.Model):
    _name = 'account.report.footnote'
    _description = 'Account Report Footnote'

    text = fields.Char()
    line = fields.Char(index=True)
    manager_id = fields.Many2one('account.report.manager')


class AccountReport(models.AbstractModel):
    _name = 'account.report'
    _description = 'Account Report'

    MAX_LINES = 80
    filter_multi_company = True
    filter_date = None
    filter_all_entries = None
    filter_comparison = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = None
    filter_hierarchy = None
    filter_partner = None
    order_selected_column = None

    ####################################################
    # OPTIONS: journals
    ####################################################

    @api.model
    def _get_filter_journals(self):
        return self.env['account.journal'].with_context(active_test=False).search([
            ('company_id', 'in', self.env.user.company_ids.ids or [self.env.company.id])
        ], order="company_id, name")

    @api.model
    def _get_filter_journal_groups(self):
        journals = self._get_filter_journals()
        groups = self.env['account.journal.group'].search([], order='sequence')
        ret = self.env['account.journal.group']
        for journal_group in groups:
            # Only display the group if it doesn't exclude every journal
            if journals - journal_group.excluded_journal_ids:
                ret += journal_group
        return ret

    @api.model
    def _init_filter_journals(self, options, previous_options=None):
        if self.filter_journals is None:
            return

        previous_company = False
        if previous_options and previous_options.get('journals'):
            journal_map = dict((opt['id'], opt['selected']) for opt in previous_options['journals'] if opt['id'] != 'divider' and 'selected' in opt)
        else:
            journal_map = {}
        options['journals'] = []

        group_header_displayed = False
        default_group_ids = []
        for group in self._get_filter_journal_groups():
            journal_ids = (self._get_filter_journals() - group.excluded_journal_ids).ids
            if len(journal_ids):
                if not group_header_displayed:
                    group_header_displayed = True
                    options['journals'].append({'id': 'divider', 'name': _('Journal Groups')})
                    default_group_ids = journal_ids
                options['journals'].append({'id': 'group', 'name': group.name, 'ids': journal_ids})

        for j in self._get_filter_journals():
            if j.company_id != previous_company:
                options['journals'].append({'id': 'divider', 'name': j.company_id.name})
                previous_company = j.company_id
            options['journals'].append({
                'id': j.id,
                'name': j.name,
                'code': j.code,
                'type': j.type,
                'selected': journal_map.get(j.id, j.id in default_group_ids),
            })

    @api.model
    def _get_options_journals(self, options):
        return [
            journal for journal in options.get('journals', []) if
            not journal['id'] in ('divider', 'group') and journal['selected']
        ]

    @api.model
    def _get_options_journals_domain(self, options):
        # Make sure to return an empty array when nothing selected to handle archived journals.
        selected_journals = self._get_options_journals(options)
        return selected_journals and [('journal_id', 'in', [j['id'] for j in selected_journals])] or []

    ####################################################
    # OPTIONS: date + comparison
    ####################################################

    @api.model
    def _get_options_periods_list(self, options):
        ''' Get periods as a list of options, one per impacted period.
        The first element is the range of dates requested in the report, others are the comparisons.

        :param options: The report options.
        :return:        A list of options having size 1 + len(options['comparison']['periods']).
        '''
        periods_options_list = []
        if options.get('date'):
            periods_options_list.append(options)
        if options.get('comparison') and options['comparison'].get('periods'):
            for period in options['comparison']['periods']:
                period_options = options.copy()
                period_options['date'] = period
                periods_options_list.append(period_options)
        return periods_options_list

    @api.model
    def _get_dates_period(self, options, date_from, date_to, mode, period_type=None, strict_range=False):
        '''Compute some information about the period:
        * The name to display on the report.
        * The period type (e.g. quarter) if not specified explicitly.
        :param date_from:   The starting date of the period.
        :param date_to:     The ending date of the period.
        :param period_type: The type of the interval date_from -> date_to.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type * mode *
        '''
        def match(dt_from, dt_to):
            return (dt_from, dt_to) == (date_from, date_to)

        string = None
        # If no date_from or not date_to, we are unable to determine a period
        if not period_type or period_type == 'custom':
            date = date_to or date_from
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date)
            if match(company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to']):
                period_type = 'fiscalyear'
                if company_fiscalyear_dates.get('record'):
                    string = company_fiscalyear_dates['record'].name
            elif match(*date_utils.get_month(date)):
                period_type = 'month'
            elif match(*date_utils.get_quarter(date)):
                period_type = 'quarter'
            elif match(*date_utils.get_fiscal_year(date)):
                period_type = 'year'
            elif match(date_utils.get_month(date)[0], fields.Date.today()):
                period_type = 'today'
            else:
                period_type = 'custom'
        elif period_type == 'fiscalyear':
            date = date_to or date_from
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date)
            record = company_fiscalyear_dates.get('record')
            string = record and record.name

        if not string:
            fy_day = self.env.company.fiscalyear_last_day
            fy_month = int(self.env.company.fiscalyear_last_month)
            if mode == 'single':
                string = _('As of %s') % (format_date(self.env, fields.Date.to_string(date_to)))
            elif period_type == 'year' or (
                    period_type == 'fiscalyear' and (date_from, date_to) == date_utils.get_fiscal_year(date_to)):
                string = date_to.strftime('%Y')
            elif period_type == 'fiscalyear' and (date_from, date_to) == date_utils.get_fiscal_year(date_to, day=fy_day, month=fy_month):
                string = '%s - %s' % (date_to.year - 1, date_to.year)
            elif period_type == 'month':
                string = format_date(self.env, fields.Date.to_string(date_to), date_format='MMM yyyy')
            elif period_type == 'quarter':
                quarter_names = get_quarter_names('abbreviated', locale=get_lang(self.env).code)
                string = u'%s\N{NO-BREAK SPACE}%s' % (
                    quarter_names[date_utils.get_quarter_number(date_to)], date_to.year)
            else:
                dt_from_str = format_date(self.env, fields.Date.to_string(date_from))
                dt_to_str = format_date(self.env, fields.Date.to_string(date_to))
                string = _('From %s\nto  %s') % (dt_from_str, dt_to_str)

        return {
            'string': string,
            'period_type': period_type,
            'mode': mode,
            'strict_range': strict_range,
            'date_from': date_from and fields.Date.to_string(date_from) or False,
            'date_to': fields.Date.to_string(date_to),
        }

    @api.model
    def _get_dates_previous_period(self, options, period_vals):
        '''Shift the period to the previous one.
        :param period_vals: A dictionary generated by the _get_dates_period method.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type *
        '''
        period_type = period_vals['period_type']
        mode = period_vals['mode']
        strict_range = period_vals.get('strict_range', False)
        date_from = fields.Date.from_string(period_vals['date_from'])
        date_to = date_from - datetime.timedelta(days=1)

        if period_type in ('fiscalyear', 'today'):
            # Don't pass the period_type to _get_dates_period to be able to retrieve the account.fiscal.year record if
            # necessary.
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date_to)
            return self._get_dates_period(options, company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to'], mode, strict_range=strict_range)
        if period_type in ('month', 'custom'):
            return self._get_dates_period(options, *date_utils.get_month(date_to), mode, period_type='month', strict_range=strict_range)
        if period_type == 'quarter':
            return self._get_dates_period(options, *date_utils.get_quarter(date_to), mode, period_type='quarter', strict_range=strict_range)
        if period_type == 'year':
            return self._get_dates_period(options, *date_utils.get_fiscal_year(date_to), mode, period_type='year', strict_range=strict_range)
        return None

    @api.model
    def _get_dates_previous_year(self, options, period_vals):
        '''Shift the period to the previous year.
        :param options:     The report options.
        :param period_vals: A dictionary generated by the _get_dates_period method.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type *
        '''
        period_type = period_vals['period_type']
        mode = period_vals['mode']
        strict_range = period_vals.get('strict_range', False)
        date_from = fields.Date.from_string(period_vals['date_from'])
        date_from = date_from - relativedelta(years=1)
        date_to = fields.Date.from_string(period_vals['date_to'])
        date_to = date_to - relativedelta(years=1)

        if period_type == 'month':
            date_from, date_to = date_utils.get_month(date_to)
        return self._get_dates_period(options, date_from, date_to, mode, period_type=period_type, strict_range=strict_range)

    @api.model
    def _init_filter_date(self, options, previous_options=None):
        """ Initialize the 'date' options key.

        :param options:             The current report options to build.
        :param previous_options:    The previous options coming from another report.
        """
        if self.filter_date is None:
            return

        previous_date = (previous_options or {}).get('date', {})
        previous_date_to = previous_date.get('date_to')
        previous_date_from = previous_date.get('date_from')
        previous_mode = previous_date.get('mode')
        previous_filter = previous_date.get('filter', 'custom')

        default_filter = self.filter_date['filter']
        options_mode = self.filter_date['mode']
        options_strict_range = self.filter_date.get('strict_range', False)
        date_from = date_to = period_type = False

        if previous_mode == 'single' and options_mode == 'range':
            # 'single' date mode to 'range'.

            if previous_filter:
                date_to = fields.Date.from_string(previous_date_to or previous_date_from)
                date_from = self.env.company.compute_fiscalyear_dates(date_to)['date_from']
                options_filter = 'custom'
            else:
                options_filter = default_filter

        elif previous_mode == 'range' and options_mode == 'single':
            # 'range' date mode to 'single'.

            if previous_filter == 'custom':
                date_to = fields.Date.from_string(previous_date_to or previous_date_from)
                date_from = date_utils.get_month(date_to)[0]
                options_filter = 'custom'
            elif previous_filter:
                options_filter = previous_filter
            else:
                options_filter = default_filter

        elif previous_mode == options_mode:
            # Same date mode.

            if previous_filter == 'custom':
                if options_mode == 'range':
                    date_from = fields.Date.from_string(previous_date_from)
                    date_to = fields.Date.from_string(previous_date_to)
                else:
                    date_to = fields.Date.from_string(previous_date_to or previous_date_from)
                    date_from = date_utils.get_month(date_to)[0]
                options_filter = 'custom'
            else:
                options_filter = previous_filter

        else:
            # Default.
            options_filter = default_filter

        # Compute 'date_from' / 'date_to'.
        if not date_from or not date_to:
            if options_filter == 'today':
                date_to = fields.Date.context_today(self)
                date_from = self.env.company.compute_fiscalyear_dates(date_to)['date_from']
                period_type = 'today'
            elif 'month' in options_filter:
                date_from, date_to = date_utils.get_month(fields.Date.context_today(self))
                period_type = 'month'
            elif 'quarter' in options_filter:
                date_from, date_to = date_utils.get_quarter(fields.Date.context_today(self))
                period_type = 'quarter'
            elif 'year' in options_filter:
                company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(fields.Date.context_today(self))
                date_from = company_fiscalyear_dates['date_from']
                date_to = company_fiscalyear_dates['date_to']
            elif options_filter == 'custom':
                custom_date_from = self.filter_date.get('date_from')
                custom_date_to = self.filter_date.get('date_to')
                date_to = fields.Date.from_string(custom_date_to or custom_date_from)
                date_from = fields.Date.from_string(custom_date_from) if custom_date_from else date_utils.get_month(date_to)[0]

        options['date'] = self._get_dates_period(
            options,
            date_from,
            date_to,
            options_mode,
            period_type=period_type,
            strict_range=options_strict_range,
        )
        if 'last' in options_filter:
            options['date'] = self._get_dates_previous_period(options, options['date'])
        options['date']['filter'] = options_filter

    @api.model
    def _init_filter_comparison(self, options, previous_options=None):
        """ Initialize the 'comparison' options key.

        /!\ This filter must be loaded after the 'date' filter.

        :param options:             The current report options to build.
        :param previous_options:    The previous options coming from another report.
        """
        if self.filter_comparison is None or not options.get('date'):
            return

        previous_comparison = (previous_options or {}).get('comparison', {})
        previous_filter = previous_comparison.get('filter')

        default_filter = self.filter_comparison.get('filter', 'no_comparison')
        strict_range = options['date']['strict_range']

        if previous_filter == 'custom':
            # Try to adapt the previous 'custom' filter.
            date_from = previous_comparison.get('date_from')
            date_to = previous_comparison.get('date_to')
            number_period = 1
            options_filter = 'custom'
        elif default_filter == 'custom':
            # Retrieve custom dates given by the user.
            if options['date']['mode'] == 'range':
                date_from = self.filter_comparison['date_from']
                date_to = self.filter_comparison['date_to']
            else:
                date_from = False
                date_to = self.filter_comparison.get('date_to') or self.filter_comparison.get('date_from')
            number_period = 1
            options_filter = 'custom'
        else:
            # Use the 'date' options.
            date_from = options['date']['date_from']
            date_to = options['date']['date_to']
            number_period = previous_comparison.get('number_period') or self.filter_comparison.get('number_period', 1)
            options_filter = previous_filter or default_filter

        options['comparison'] = {
            'filter': options_filter,
            'number_period': number_period,
            'date_from': date_from,
            'date_to': date_to,
            'periods': [],
        }

        date_from_obj = fields.Date.from_string(date_from)
        date_to_obj = fields.Date.from_string(date_to)

        if options_filter == 'custom':
            options['comparison']['periods'].append(self._get_dates_period(
                options,
                date_from_obj,
                date_to_obj,
                options['date']['mode'],
                strict_range=strict_range,
            ))
        elif options_filter in ('previous_period', 'same_last_year'):
            previous_period = options['date']
            for index in range(0, number_period):
                if options_filter == 'previous_period':
                    period_vals = self._get_dates_previous_period(options, previous_period)
                elif options_filter == 'same_last_year':
                    period_vals = self._get_dates_previous_year(options, previous_period)
                else:
                    date_from_obj = fields.Date.from_string(date_from)
                    date_to_obj = fields.Date.from_string(date_to)
                    strict_range = previous_period.get('strict_range', False)
                    period_vals = self._get_dates_period(options, date_from_obj, date_to_obj, previous_period['mode'], strict_range=strict_range)
                options['comparison']['periods'].append(period_vals)
                previous_period = period_vals

        if len(options['comparison']['periods']) > 0:
            options['comparison'].update(options['comparison']['periods'][0])

    @api.model
    def _get_options_date_domain(self, options):
        def create_date_domain(options_date):
            date_field = options_date.get('date_field', 'date')
            domain = [(date_field, '<=', options_date['date_to'])]
            if options_date['mode'] == 'range' and options_date['date_from']:
                strict_range = options_date.get('strict_range')
                if not strict_range:
                    domain += [
                        '|',
                        (date_field, '>=', options_date['date_from']),
                        ('account_id.user_type_id.include_initial_balance', '=', True)
                    ]
                else:
                    domain += [(date_field, '>=', options_date['date_from'])]
            return domain

        if not options.get('date'):
            return []
        return create_date_domain(options['date'])

    ####################################################
    # OPTIONS: analytic
    ####################################################

    @api.model
    def _init_filter_analytic(self, options, previous_options=None):
        if not self.filter_analytic:
            return

        enable_analytic_accounts = self.user_has_groups('analytic.group_analytic_accounting')
        enable_analytic_tags = self.user_has_groups('analytic.group_analytic_tags')
        if not enable_analytic_accounts and not enable_analytic_tags:
            return

        if enable_analytic_accounts:
            previous_analytic_accounts = (previous_options or {}).get('analytic_accounts', [])
            analytic_account_ids = [int(x) for x in previous_analytic_accounts]
            selected_analytic_accounts = self.env['account.analytic.account'].search([('id', 'in', analytic_account_ids)])
            options['analytic_accounts'] = selected_analytic_accounts.ids
            options['selected_analytic_account_names'] = selected_analytic_accounts.mapped('name')

        if enable_analytic_tags:
            previous_analytic_tags = (previous_options or {}).get('analytic_tags', [])
            analytic_tag_ids = [int(x) for x in previous_analytic_tags]
            selected_analytic_tags = self.env['account.analytic.tag'].search([('id', 'in', analytic_tag_ids)])
            options['analytic_tags'] = selected_analytic_tags.ids
            options['selected_analytic_tag_names'] = selected_analytic_tags.mapped('name')

    @api.model
    def _get_options_analytic_domain(self, options):
        domain = []
        if options.get('analytic_accounts'):
            analytic_account_ids = [int(acc) for acc in options['analytic_accounts']]
            domain.append(('analytic_account_id', 'in', analytic_account_ids))
        if options.get('analytic_tags'):
            analytic_tag_ids = [int(tag) for tag in options['analytic_tags']]
            domain.append(('analytic_tag_ids', 'in', analytic_tag_ids))
        return domain

    ####################################################
    # OPTIONS: partners
    ####################################################

    @api.model
    def _init_filter_partner(self, options, previous_options=None):
        if not self.filter_partner:
            return

        options['partner'] = True
        previous_partner_ids = previous_options and previous_options.get('partner_ids') or []
        options['partner_categories'] = previous_options and previous_options.get('partner_categories') or []

        selected_partner_ids = [int(partner) for partner in previous_partner_ids]
        # search instead of browse so that record rules apply and filter out the ones the user does not have access to
        selected_partners = selected_partner_ids and self.env['res.partner'].search([('id', 'in', selected_partner_ids)]) or self.env['res.partner']
        options['selected_partner_ids'] = selected_partners.mapped('name')
        options['partner_ids'] = selected_partners.ids

        selected_partner_category_ids = [int(category) for category in options['partner_categories']]
        selected_partner_categories = selected_partner_category_ids and self.env['res.partner.category'].browse(selected_partner_category_ids) or self.env['res.partner.category']
        options['selected_partner_categories'] = selected_partner_categories.mapped('name')

    @api.model
    def _get_options_partner_domain(self, options):
        domain = []
        if options.get('partner_ids'):
            partner_ids = [int(partner) for partner in options['partner_ids']]
            domain.append(('partner_id', 'in', partner_ids))
        if options.get('partner_categories'):
            partner_category_ids = [int(category) for category in options['partner_categories']]
            domain.append(('partner_id.category_id', 'in', partner_category_ids))
        return domain

    ####################################################
    # OPTIONS: all_entries
    ####################################################

    @api.model
    def _get_options_all_entries_domain(self, options):
        if not options.get('all_entries'):
            return [('parent_state', '=', 'posted')]
        else:
            return [('parent_state', '!=', 'cancel')]

    ####################################################
    # OPTIONS: order column
    ####################################################

    @api.model
    def _init_order_selected_column(self, options, previous_options=None):
        if self.order_selected_column is not None:
            options['selected_column'] = previous_options and previous_options.get('selected_column') or self.order_selected_column['default']

    ####################################################
    # OPTIONS: hierarchy
    ####################################################

    @api.model
    def _init_filter_hierarchy(self, options, previous_options=None):
        # Only propose the option if there are groups
        if self.filter_hierarchy is not None and self.env['account.group'].search([('company_id', 'in', self.env.companies.ids)], limit=1):
            if previous_options and 'hierarchy' in previous_options:
                options['hierarchy'] = previous_options['hierarchy']
            else:
                options['hierarchy'] = self.filter_hierarchy

    # Create codes path in the hierarchy based on account.
    def get_account_codes(self, account):
        # A code is tuple(id, name)
        codes = []
        if account.group_id:
            group = account.group_id
            while group:
                codes.append((group.id, group.display_name))
                group = group.parent_id
        else:
            codes.append((0, _('(No Group)')))
        return list(reversed(codes))

    @api.model
    def _create_hierarchy(self, lines, options):
        """Compute the hierarchy based on account groups when the option is activated.

        The option is available only when there are account.group for the company.
        It should be called when before returning the lines to the client/templater.
        The lines are the result of _get_lines(). If there is a hierarchy, it is left
        untouched, only the lines related to an account.account are put in a hierarchy
        according to the account.group's and their prefixes.
        """
        unfold_all = self.env.context.get('print_mode') and len(options.get('unfolded_lines')) == 0 or options.get('unfold_all')

        def add_to_hierarchy(lines, key, level, parent_id, hierarchy):
            val_dict = hierarchy[key]
            unfolded = val_dict['id'] in options.get('unfolded_lines') or unfold_all
            # add the group totals
            lines.append({
                'id': val_dict['id'],
                'name': val_dict['name'],
                'title_hover': val_dict['name'],
                'unfoldable': True,
                'unfolded': unfolded,
                'level': level,
                'parent_id': parent_id,
                'columns': [{'name': self.format_value(c) if isinstance(c, (int, float)) else c, 'no_format_name': c} for c in val_dict['totals']],
                'name_class': 'o_account_report_name_ellipsis top-vertical-align'
            })
            if not self._context.get('print_mode') or unfolded:
                for i in val_dict['children_codes']:
                    hierarchy[i]['parent_code'] = i
                all_lines = [hierarchy[id] for id in val_dict["children_codes"]] + val_dict["lines"]
                for line in sorted(all_lines, key=lambda k: k.get('account_code', '') + k['name']):
                    if 'children_codes' in line:
                        children = []
                        # if the line is a child group, add it recursively
                        add_to_hierarchy(children, line['parent_code'], level + 1, val_dict['id'], hierarchy)
                        lines.extend(children)
                    else:
                        # add lines that are in this group but not in one of this group's children groups
                        line['level'] = level + 1
                        line['parent_id'] = val_dict['id']
                        lines.append(line)

        def compute_hierarchy(lines, level, parent_id):
            # put every line in each of its parents (from less global to more global) and compute the totals
            hierarchy = defaultdict(lambda: {'totals': [None] * len(lines[0]['columns']), 'lines': [], 'children_codes': set(), 'name': '', 'parent_id': None, 'id': ''})
            for line in lines:
                account = self.env['account.account'].browse(line.get('account_id', self._get_caret_option_target_id(line.get('id'))))
                codes = self.get_account_codes(account)  # id, name
                for code in codes:
                    hierarchy[code[0]]['id'] = f'hierarchy_{parent_id}_{code[0]}'
                    hierarchy[code[0]]['name'] = code[1]
                    for i, column in enumerate(line['columns']):
                        if 'no_format_name' in column:
                            no_format = column['no_format_name']
                        elif 'no_format' in column:
                            no_format = column['no_format']
                        else:
                            no_format = None
                        if isinstance(no_format, (int, float)):
                            if hierarchy[code[0]]['totals'][i] is None:
                                hierarchy[code[0]]['totals'][i] = no_format
                            else:
                                hierarchy[code[0]]['totals'][i] += no_format
                for code, child in zip(codes[:-1], codes[1:]):
                    hierarchy[code[0]]['children_codes'].add(child[0])
                    hierarchy[child[0]]['parent_id'] = hierarchy[code[0]]['id']
                hierarchy[codes[-1][0]]['lines'] += [line]
            # compute the tree-like structure by starting at the roots (being groups without parents)
            hierarchy_lines = []
            for root in [k for k, v in hierarchy.items() if not v['parent_id']]:
                add_to_hierarchy(hierarchy_lines, root, level, parent_id, hierarchy)
            return hierarchy_lines

        new_lines = []
        account_lines = []
        current_level = 0
        parent_id = 'root'
        for line in lines:
            if not (line.get('caret_options') == 'account.account' or line.get('account_id')):
                # make the hierarchy with the lines we gathered, append it to the new lines and restart the gathering
                if account_lines:
                    new_lines.extend(compute_hierarchy(account_lines, current_level + 1, parent_id))
                account_lines = []
                new_lines.append(line)
                current_level = line['level']
                parent_id = line['id']
            else:
                # gather all the lines we can create a hierarchy on
                account_lines.append(line)
        # do it one last time for the gathered lines remaining
        if account_lines:
            new_lines.extend(compute_hierarchy(account_lines, current_level + 1, parent_id))
        return new_lines

    ####################################################
    # OPTIONS: CORE
    ####################################################

    @api.model
    def _get_options(self, previous_options=None):
        # Create default options.
        options = {
            'unfolded_lines': previous_options and previous_options.get('unfolded_lines') or [],
        }

        # Multi-company is there for security purpose and can't be disabled by a filter.
        if self.filter_multi_company:
            if self._context.get('allowed_company_ids'):
                # Retrieve the companies through the multi-companies widget.
                companies = self.env['res.company'].browse(self._context['allowed_company_ids'])
            else:
                # When called from testing files, 'allowed_company_ids' is missing.
                # Then, give access to all user's companies.
                companies = self.env.companies
            if len(companies) > 1:
                options['multi_company'] = [
                    {'id': c.id, 'name': c.name} for c in companies
                ]

        # Call _init_filter_date/_init_filter_comparison because the second one must be called after the first one.
        if self.filter_date:
            self._init_filter_date(options, previous_options=previous_options)
        if self.filter_comparison:
            self._init_filter_comparison(options, previous_options=previous_options)
        if self.filter_analytic:
            options['analytic'] = self.filter_analytic

        filter_list = [attr
                       for attr in dir(self)
                       if (attr.startswith('filter_') or attr.startswith('order_'))
                       and attr not in ('filter_date', 'filter_comparison', 'filter_multi_company')
                       and len(attr) > 7
                       and not callable(getattr(self, attr))]
        for filter_key in filter_list:
            options_key = filter_key[7:]
            init_func = getattr(self, '_init_%s' % filter_key, None)
            if init_func:
                init_func(options, previous_options=previous_options)
            else:
                filter_opt = getattr(self, filter_key, None)
                if filter_opt is not None:
                    if previous_options and options_key in previous_options:
                        options[options_key] = previous_options[options_key]
                    else:
                        options[options_key] = filter_opt
        return options

    @api.model
    def _get_options_domain(self, options):
        domain = [
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('parent_state', '!=', 'cancel'),
        ]

        if options.get('multi_company', False):
            domain += [('company_id', 'in', self.env.companies.ids)]
        else:
            domain += [('company_id', '=', self.env.company.id)]
        domain += self._get_options_journals_domain(options)
        domain += self._get_options_date_domain(options)
        domain += self._get_options_analytic_domain(options)
        domain += self._get_options_partner_domain(options)
        domain += self._get_options_all_entries_domain(options)
        return domain

    ####################################################
    # QUERIES
    ####################################################

    def _cr_execute(self, options, query, params=None):
        ''' Similar to self._cr.execute but allowing some custom behavior like shadowing the account_move_line table
        to another one like account_reports_cash_basis does.
        :param options: The report options.
        :param query:   The query to be executed by the report.
        :param params:  The optional params of the _cr.execute method.
        '''
        return self._cr.execute(query, params)

    @api.model
    def _query_get(self, options, domain=None):
        domain = self._get_options_domain(options) + (domain or [])
        self.env['account.move.line'].check_access_rights('read')

        query = self.env['account.move.line']._where_calc(domain)

        # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
        self.env['account.move.line']._apply_ir_rules(query)

        return query.get_sql()

    ####################################################
    # MISC
    ####################################################

    def get_header(self, options):
        columns = self._get_columns(options)
        if 'selected_column' in options and self.order_selected_column:
            selected_column = columns[0][abs(options['selected_column']) - 1]
            if 'sortable' in selected_column.get('class', ''):
                selected_column['class'] = (options['selected_column'] > 0 and 'up ' or 'down ') + selected_column['class']
        return columns

    # TO BE OVERWRITTEN
    def _get_columns(self, options):
        return [self._get_columns_name(options)]

    # TO BE OVERWRITTEN
    def _get_columns_name(self, options):
        return []

    #TO BE OVERWRITTEN
    def _get_lines(self, options, line_id=None):
        return []

    #TO BE OVERWRITTEN
    def _get_table(self, options):
        return self.get_header(options), self._get_lines(options)

    #TO BE OVERWRITTEN
    def _get_templates(self):
        return {
                'main_template': 'metroerp_accounting_enhancement.main_template',
                'main_table_header_template': 'metroerp_accounting_enhancement.main_table_header',
                'line_template': 'metroerp_accounting_enhancement.line_template',
                'footnotes_template': 'metroerp_accounting_enhancement.footnotes_template',
                'search_template': 'metroerp_accounting_enhancement.search_template',
        }

    #TO BE OVERWRITTEN
    def _get_report_name(self):
        return _('General Report')

    def get_report_filename(self, options):
        """The name that will be used for the file when downloading pdf,xlsx,..."""
        return self._get_report_name().lower().replace(' ', '_')

    def execute_action(self, options, params=None):
        action_id = int(params.get('actionId'))
        action = self.env['ir.actions.actions'].sudo().browse([action_id])
        action_type = action.type
        action = self.env[action.type].sudo().browse([action_id])
        action_read = clean_action(action.read()[0], env=action.env)
        if action_type == 'ir.actions.client':
            # Check if we are opening another report and if yes, pass options and ignore_session
            if action.tag == 'account_report':
                options['unfolded_lines'] = []
                options['unfold_all'] = False
                action_read.update({'params': {'options': options, 'ignore_session': 'read'}})
        if params.get('id'):
            # Add the id of the account.financial.html.report.line in the action's context
            context = action_read.get('context') and ast.literal_eval(action_read['context']) or {}
            context.setdefault('active_id', int(params['id']))
            action_read['context'] = context
        return action_read

    @api.model
    def _resolve_caret_option_document(self, model, res_id, document):
        '''Retrieve the target record of the caret option.

        :param model:       The source model of the report line, 'account.move.line' by default.
        :param res_id:      The source id of the report line.
        :param document:    The target model of the redirection.
        :return: The target record.
        '''
        if model == document:
            return self.env[model].browse(res_id)

        if model == 'account.move':
            if document == 'res.partner':
                return self.env[model].browse(res_id).partner_id.commercial_partner_id
        elif model == 'account.bank.statement.line':
            if document == 'account.bank.statement':
                return self.env[model].browse(res_id).statement_id

        # model == 'account.move.line' by default.
        if document == 'account.move':
            return self.env[model].browse(res_id).move_id
        if document == 'account.payment':
            return self.env[model].browse(res_id).payment_id
        if document == 'account.bank.statement':
            return self.env[model].browse(res_id).statement_id

        return self.env[model].browse(res_id)

    @api.model
    def _resolve_caret_option_view(self, target):
        '''Retrieve the target view name of the caret option.

        :param target:  The target record of the redirection.
        :return: The target view name as a string.
        '''
        if target._name == 'account.payment':
            return 'account.view_account_payment_form'
        if target._name == 'res.partner':
            return 'base.view_partner_form'
        if target._name == 'account.bank.statement':
            return 'account.view_bank_statement_form'

        # document == 'account.move' by default.
        return 'view_move_form'

    def open_document(self, options, params=None):
        if not params:
            params = {}

        ctx = self.env.context.copy()
        ctx.pop('id', '')

        # Decode params
        model = params.get('model', 'account.move.line')
        id_param = params.get('id')
        # Reconciliation report may append the model to the id to ensure unique ids
        res_id = isinstance(id_param, int) and id_param or int(id_param.split('-')[-1])
        document = params.get('object', 'account.move')

        # Redirection data
        target = self._resolve_caret_option_document(model, res_id, document)
        view_name = self._resolve_caret_option_view(target)
        module = 'account'
        if '.' in view_name:
            module, view_name = view_name.split('.')

        # Redirect
        view_id = self.env['ir.model.data'].get_object_reference(module, view_name)[1]
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'res_model': document,
            'view_id': view_id,
            'res_id': target.id,
            'context': ctx,
        }

    def open_action(self, options, domain):
        assert isinstance(domain, (list, tuple))
        domain += [('date', '>=', options.get('date').get('date_from')),
                   ('date', '<=', options.get('date').get('date_to'))]
        if not options.get('all_entries'):
            domain += [('parent_state', '=', 'posted')]

        ctx = self.env.context.copy()
        ctx.update({'search_default_account': 1, 'search_default_groupby_date': 1})

        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Items for Tax Audit'),
            'res_model': 'account.move.line',
            'views': [[self.env.ref('account.view_move_line_tax_audit_tree').id, 'list'], [False, 'form']],
            'domain': domain,
            'context': ctx,
        }

    def open_tax(self, options, params=None):
        active_id = int(str(params.get('id')).split('_')[0])
        tax = self.env['account.tax'].browse(active_id)
        domain = ['|', ('tax_ids', 'in', [active_id]),
                       ('tax_line_id', 'in', [active_id])]
        if tax.tax_exigibility == 'on_payment':
            domain += [('tax_exigible', '=', True)]
        return self.open_action(options, domain)

    def tax_tag_template_open_aml(self, options, params=None):
        active_id = int(str(params.get('id')).split('_')[0])
        tag_template = self.env['account.tax.report.line'].browse(active_id)
        company_ids = [comp_opt['id'] for comp_opt in options.get('multi_company', [])] or self.env.company.ids
        domain = [('tax_tag_ids', 'in', tag_template.tag_ids.ids), ('tax_exigible', '=', True), ('company_id', 'in', company_ids)]
        return self.open_action(options, domain)

    def open_tax_report_line(self, options, params=None):
        active_id = int(str(params.get('id')).split('_')[0])
        line = self.env['account.financial.html.report.line'].browse(active_id)
        domain = ast.literal_eval(line.domain)
        action = self.open_action(options, domain)
        action['display_name'] = _('Journal Items (%s)', line.name)
        return action

    def open_general_ledger(self, options, params=None):
        if params.get('id'):
            account_id = self._get_caret_option_target_id(params.get('id', 0))
            options = dict(options)
            options['unfolded_lines'] = ['account_%s' % account_id]
        action_vals = self.env['ir.actions.actions']._for_xml_id('metroerp_accounting_enhancement.action_account_report_general_ledger')
        action_vals['params'] = {
            'options': options,
            'ignore_session': 'read',
        }
        return action_vals

    def _get_caret_option_target_id(self, line_id):
        """ Retrieve the target model's id for lines obtained from a financial
        report groupby. These lines have a string as id to ensure it is unique,
        in case some accounts appear multiple times in the same report

        TODO CLEANME: a better id handling in a common caret options function
        would be nice in master, instead of local hardcoded patches like here.
        """
        if isinstance(line_id, str):
            return int(line_id.split('_')[-1])
        else:
            return line_id

    def open_unposted_moves(self, options, params=None):
        ''' Open the list of draft journal entries that might impact the reporting'''
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action = clean_action(action, env=self.env)
        domain = [('state', '=', 'draft')]
        if options.get('date'):
            #there's no condition on the date from, as a draft entry might change the initial balance of a line
            date_to = options['date'].get('date_to') or options['date'].get('date') or fields.Date.today()
            domain += [('date', '<=', date_to)]
        action['domain'] = domain
        #overwrite the context to avoid default filtering on 'misc' journals
        action['context'] = {}
        return action

    def periodic_tva_entries(self, options):
        # Return action to open form view of newly entry created
        ctx = self._set_context(options)
        ctx['strict_range'] = True
        self = self.with_context(ctx)
        move = self.env['account.generic.tax.report']._generate_tax_closing_entry(options)
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action = clean_action(action, env=self.env)
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = move.id
        return action

    def _get_vat_report_attachments(self, options):
        # Fetch pdf
        pdf = self.get_pdf(options)
        return [('vat_report.pdf', pdf)]

    # def action_partner_reconcile(self, options, params):
    #     form = self.env.ref('account_accountant.action_manual_reconciliation', False).sudo()
    #     ctx = self.env.context.copy()
    #     ctx['partner_ids'] = ctx['active_id'] = [params.get('partner_id')]
    #     ctx['all_entries'] = True
    #     return {
    #         'type': 'ir.actions.client',
    #         'view_id': form.id,
    #         'tag': form.tag,
    #         'context': ctx,
    #     }

    def open_journal_items(self, options, params):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_line_select")
        action = clean_action(action, env=self.env)
        ctx = self.env.context.copy()
        if params and 'id' in params:
            active_id = self._get_caret_option_target_id(params['id'])
            ctx.update({
                    'active_id': active_id,
                    'search_default_account_id': [active_id],
            })

        if options:
            domain = expression.normalize_domain(ast.literal_eval(action.get('domain') or '[]'))
            if options.get('journals'):
                selected_journals = [journal['id'] for journal in options['journals'] if journal.get('selected')]
                if len(selected_journals) == 1:
                    ctx['search_default_journal_id'] = selected_journals
                elif selected_journals:  # Otherwise, nothing is selected, so we want to display everything
                    domain = expression.AND([domain, [('journal_id', 'in', selected_journals)]])

            if options.get('analytic_accounts'):
                analytic_ids = [int(r) for r in options['analytic_accounts']]
                domain = expression.AND([domain, [('analytic_account_id', 'in', analytic_ids)]])
            if options.get('date'):
                opt_date = options['date']
                domain = expression.AND([domain, self._get_options_date_domain(options)])
            # In case the line has been generated for a "group by" financial line, append the parent line's domain to the one we created
            if params.get('financial_group_line_id'):
                # In case the hierarchy is enabled, 'financial_group_line_id' might be a string such
                # as 'hierarchy_xxx'. This will obviously cause a crash at domain evaluation.
                if not (isinstance(params['financial_group_line_id'], str) and 'hierarchy_' in params['financial_group_line_id']):
                    parent_financial_report_line = self.env['account.financial.html.report.line'].browse(params['financial_group_line_id'])
                    domain = expression.AND([domain, ast.literal_eval(parent_financial_report_line.domain)])

            if not options.get('all_entries'):
                ctx['search_default_posted'] = True

            action['domain'] = domain
        action['context'] = ctx
        return action

    def reverse(self, values):
        """Utility method used to reverse a list, this method is used during template generation in order to reverse periods for example"""
        if not isinstance(values, list):
            return values
        else:
            inv_values = copy.deepcopy(values)
            inv_values.reverse()
        return inv_values

    @api.model
    def _sort_lines(self, lines, options):
        ''' Sort report lines based on the 'selected_column' key inside the options.
        The value of options['selected_column'] is an integer, positive or negative, indicating on which column
        to sort and also if it must be an ascending sort (positive value) or a descending sort (negative value).
        If this key is missing or falsy, lines is returned directly.

        This method has some limitations:
        - The selected_column must have 'sortable' in its classes.
        - All lines are sorted expect those having the 'total' class.
        - This only works when each line has an unique id.
        - All lines inside the selected_column must have a 'no_format' value.

        Example:

        parent_line_1           no_format=11
            child_line_1        no_format=1
            child_line_2        no_format=3
            child_line_3        no_format=2
            child_line_4        no_format=7
            child_line_5        no_format=4
            child_line_6        (total line)
        parent_line_2           no_format=10
            child_line_7        no_format=5
            child_line_8        no_format=6
            child_line_9        (total line)


        The resulting lines will be:

        parent_line_2           no_format=10
            child_line_7        no_format=5
            child_line_8        no_format=6
            child_line_9        (total line)
        parent_line_1           no_format=11
            child_line_1        no_format=1
            child_line_3        no_format=2
            child_line_2        no_format=3
            child_line_5        no_format=4
            child_line_4        no_format=7
            child_line_6        (total line)

        :param lines:   The report lines.
        :param options: The report options.
        :return:        Lines sorted by the selected column.
        '''
        def merge_tree(line):
            sorted_list.append(line)
            for l in sorted(tree[line['id']], key=lambda k: selected_sign * k['columns'][selected_column - k.get('colspan', 1)]['no_format']):
                merge_tree(l)

        sorted_list = []
        selected_column = abs(options['selected_column']) - 1
        selected_sign = -copysign(1, options['selected_column'])
        tree = defaultdict(list)
        if 'sortable' not in self._get_columns_name(options)[selected_column].get('class', ''):
            return lines  # Nothing to do here
        for line in lines:
            tree[line.get('parent_id') or None].append(line)
        for line in sorted(tree[None], key=lambda k: ('total' in k.get('class', ''), selected_sign * k['columns'][selected_column - k.get('colspan', 1)]['no_format'])):
            merge_tree(line)

        return sorted_list

    def _set_context(self, options):
        """This method will set information inside the context based on the options dict as some options need to be in context for the query_get method defined in account_move_line"""
        ctx = self.env.context.copy()
        if options.get('date') and options['date'].get('date_from'):
            ctx['date_from'] = options['date']['date_from']
        if options.get('date'):
            ctx['date_to'] = options['date'].get('date_to') or options['date'].get('date')
        if options.get('all_entries') is not None:
            ctx['state'] = options.get('all_entries') and 'all' or 'posted'
        if options.get('journals'):
            ctx['journal_ids'] = [j.get('id') for j in options.get('journals') if j.get('selected')]
        if options.get('analytic_accounts'):
            ctx['analytic_account_ids'] = self.env['account.analytic.account'].browse([int(acc) for acc in options['analytic_accounts']])
        if options.get('analytic_tags'):
            ctx['analytic_tag_ids'] = self.env['account.analytic.tag'].browse([int(t) for t in options['analytic_tags']])
        if options.get('partner_ids'):
            ctx['partner_ids'] = self.env['res.partner'].browse([int(partner) for partner in options['partner_ids']])
        if options.get('partner_categories'):
            ctx['partner_categories'] = self.env['res.partner.category'].browse([int(category) for category in options['partner_categories']])
        if not ctx.get('allowed_company_ids') or not options.get('multi_company'):
            """Contrary to the generic multi_company strategy,
            If we have not specified multiple companies, we only use
            the user company for account reports.

            To do so, we set the allowed_company_ids to only the main current company
            so that self.env.company == self.env.companies
            """
            ctx['allowed_company_ids'] = self.env.company.ids
        return ctx

    def get_report_informations(self, options):
        '''
        return a dictionary of informations that will be needed by the js widget, manager_id, footnotes, html of report and searchview, ...
        '''
        options = self._get_options(options)

        searchview_dict = {'options': options, 'context': self.env.context}
        # Check if report needs analytic
        if options.get('analytic_accounts') is not None:
            options['selected_analytic_account_names'] = [self.env['account.analytic.account'].browse(int(account)).name for account in options['analytic_accounts']]
        if options.get('analytic_tags') is not None:
            options['selected_analytic_tag_names'] = [self.env['account.analytic.tag'].browse(int(tag)).name for tag in options['analytic_tags']]
        if options.get('partner'):
            options['selected_partner_ids'] = [self.env['res.partner'].browse(int(partner)).name for partner in options['partner_ids']]
            options['selected_partner_categories'] = [self.env['res.partner.category'].browse(int(category)).name for category in (options.get('partner_categories') or [])]

        # Check whether there are unposted entries for the selected period or not (if the report allows it)
        if options.get('date') and options.get('all_entries') is not None:
            date_to = options['date'].get('date_to') or options['date'].get('date') or fields.Date.today()
            period_domain = [('state', '=', 'draft'), ('date', '<=', date_to)]
            options['unposted_in_period'] = bool(self.env['account.move'].search_count(period_domain))

        if options.get('journals'):
            journals_selected = set(journal['id'] for journal in options['journals'] if journal.get('selected'))
            for journal_group in self.env['account.journal.group'].search([('company_id', '=', self.env.company.id)]):
                if journals_selected and journals_selected == set(self._get_filter_journals().ids) - set(journal_group.excluded_journal_ids.ids):
                    options['name_journal_group'] = journal_group.name
                    break

        report_manager = self._get_report_manager(options)
        info = {'options': options,
                'context': self.env.context,
                'report_manager_id': report_manager.id,
                'footnotes': [{'id': f.id, 'line': f.line, 'text': f.text} for f in report_manager.footnotes_ids],
                'buttons': self._get_reports_buttons_in_sequence(),
                'main_html': self.get_html(options),
                'searchview_html': self.env['ir.ui.view']._render_template(self._get_templates().get('search_template', 'metroerp_accounting_enhancement.search_template'), values=searchview_dict),
                }
        return info


    def get_html(self, options, line_id=None, additional_context=None):
        '''
        return the html value of report, or html value of unfolded line
        * if line_id is set, the template used will be the line_template
        otherwise it uses the main_template. Reason is for efficiency, when unfolding a line in the report
        we don't want to reload all lines, just get the one we unfolded.
        '''
        # Prevent inconsistency between options and context.
        self = self.with_context(self._set_context(options))

        templates = self._get_templates()
        report_manager = self._get_report_manager(options)

        render_values = {
            'report': {
                'name': self._get_report_name(),
                'summary': report_manager.summary,
                'company_name': self.env.company.name,
            },
            'options': options,
            'context': self.env.context,
            'model': self,
        }
        if additional_context:
            render_values.update(additional_context)

        # Create lines/headers.
        if line_id:
            headers = options['headers']
            lines = self._get_lines(options, line_id=line_id)
            template = templates['line_template']
        else:
            headers, lines = self._get_table(options)
            options['headers'] = headers
            template = templates['main_template']
        if options.get('hierarchy'):
            lines = self._create_hierarchy(lines, options)
        if options.get('selected_column'):
            lines = self._sort_lines(lines, options)
        render_values['lines'] = {'columns_header': headers, 'lines': lines}

        # Manage footnotes.
        footnotes_to_render = []
        if self.env.context.get('print_mode', False):
            # we are in print mode, so compute footnote number and include them in lines values, otherwise, let the js compute the number correctly as
            # we don't know all the visible lines.
            footnotes = dict([(str(f.line), f) for f in report_manager.footnotes_ids])
            number = 0
            for line in lines:
                f = footnotes.get(str(line.get('id')))
                if f:
                    number += 1
                    line['footnote'] = str(number)
                    footnotes_to_render.append({'id': f.id, 'number': number, 'text': f.text})

        # Render.
        html = self.env.ref(template)._render(render_values)
        if self.env.context.get('print_mode', False):
            for k,v in self._replace_class().items():
                html = html.replace(k, v)
            # append footnote as well
            html = html.replace(b'<div class="js_account_report_footnotes"></div>', self.get_html_footnotes(footnotes_to_render))
        return html

    def get_html_footnotes(self, footnotes):
        template = self._get_templates().get('footnotes_template', 'metroerp_accounting_enhancement.footnotes_template')
        rcontext = {'footnotes': footnotes, 'context': self.env.context}
        html = self.env['ir.ui.view']._render_template(template, values=dict(rcontext))
        return html

    def _get_reports_buttons_in_sequence(self):
        return sorted(self._get_reports_buttons(), key=lambda x: x.get('sequence', 9))

    def _get_reports_buttons(self):
        return [
            #{'name': _('Print Preview'), 'sequence': 1,'invisible':1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
            {'name': _('Export (XLSX)'), 'sequence': 1, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
            # {'name':_('Save'), 'sequence': 10, 'action': 'open_report_export_wizard'},
        ]

    def open_report_export_wizard(self, options):
        """ Creates a new export wizard for this report and returns an act_window
        opening it. A new account_report_generation_options key is also added to
        the context, containing the current options selected on this report
        (which must hence be taken into account when exporting it to a file).
        """
        new_wizard = self.env['metroerp_accounting_enhancement.export.wizard'].create({'report_model': self._name,'report_id': self.id})
        view_id = self.env.ref('metroerp_accounting_enhancement.view_report_export_wizard').id
        new_context = self.env.context.copy()
        new_context['account_report_generation_options'] = options
        return {
            'type': 'ir.actions.act_window',
            'name': _('Export'),
            'view_mode': 'form',
            'res_model': 'metroerp_accounting_enhancement.export.wizard',
            'target': 'new',
            'res_id': new_wizard.id,
            'views': [[view_id, 'form']],
            'context': new_context,
        }

    @api.model
    def get_export_mime_type(self, file_type):
        """ Returns the MIME type associated with a report export file type,
        for attachment generation.
        """
        type_mapping = {
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'pdf': 'application/pdf',
            'xml': 'application/xml',
            'xaf': 'application/vnd.sun.xml.writer',
            'txt': 'text/plain',
            'csv': 'text/csv',
            'zip': 'application/zip',
        }
        return type_mapping.get(file_type, False)

    def _get_report_manager(self, options):
        domain = [('report_name', '=', self._name)]
        domain = (domain + [('financial_report_id', '=', self.id)]) if 'id' in dir(self) else domain
        multi_company_report = options.get('multi_company', False)
        if not multi_company_report:
            domain += [('company_id', '=', self.env.company.id)]
        else:
            domain += [('company_id', '=', False)]
        existing_manager = self.env['account.report.manager'].search(domain, limit=1)
        if not existing_manager:
            existing_manager = self.env['account.report.manager'].create({
                'report_name': self._name,
                'company_id': self.env.company.id if not multi_company_report else False,
                'financial_report_id': self.id if 'id' in dir(self) else False,
            })
        return existing_manager

    @api.model
    def format_value(self, amount, currency=False, blank_if_zero=False):
        ''' Format amount to have a monetary display (with a currency symbol).
        E.g: 1000 => 1000.0 $

        :param amount:          A number.
        :param currency:        An optional res.currency record.
        :param blank_if_zero:   An optional flag forcing the string to be empty if amount is zero.
        :return:                The formatted amount as a string.
        '''
        currency_id = currency or self.env.company.currency_id
        if currency_id.is_zero(amount):
            if blank_if_zero:
                return ''
            # don't print -0.0 in reports
            amount = abs(amount)

        if self.env.context.get('no_format'):
            return amount
        return formatLang(self.env, amount, currency_obj=currency_id)

    @api.model
    def _format_aml_name(self, line_name, move_ref, move_name):
        ''' Format the display of an account.move.line record. As its very costly to fetch the account.move.line
        records, only line_name, move_ref, move_name are passed as parameters to deal with sql-queries more easily.

        :param line_name:   The name of the account.move.line record.
        :param move_ref:    The reference of the account.move record.
        :param move_name:   The name of the account.move record.
        :return:            The formatted name of the account.move.line record.
        '''
        names = []
        if move_name and move_name != '/':
            names.append(move_name)
        if move_ref and move_ref != '/':
            names.append(move_ref)
        if line_name and line_name != move_name and line_name != '/':
            names.append(line_name)
        name = '-'.join(names)
        return name

    @api.model
    def format_report_date(self, date, lang_code=False, date_format=False):
        if self.env.context.get('no_format') and isinstance(date, (datetime.date, datetime.datetime)):
            return date
        return format_date(self.env, date, lang_code, date_format)

    def format_date(self, options, dt_filter='date'):
        date_from = fields.Date.from_string(options[dt_filter]['date_from'])
        date_to = fields.Date.from_string(options[dt_filter]['date_to'])
        strict_range = options['date'].get('strict_range', False)
        return self._get_dates_period(options, date_from, date_to, options['date']['mode'], strict_range=strict_range)['string']

    def print_pdf(self, options):
        return {
                'type': 'ir_actions_account_report_download1',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'pdf',
                         'financial_id': self.env.context.get('id'),
                         'allowed_company_ids': self.env.context.get('allowed_company_ids'),
                         }
                }

    def _replace_class(self):
        """When printing pdf, we sometime want to remove/add/replace class for the report to look a bit different on paper
        this method is used for this, it will replace occurence of value key by the dict value in the generated pdf
        """
        return {b'o_account_reports_no_print': b'', b'table-responsive': b'', b'<a': b'<span', b'</a>': b'</span>'}

    def get_pdf(self, options, minimal_layout=True):
        # As the assets are generated during the same transaction as the rendering of the
        # templates calling them, there is a scenario where the assets are unreachable: when
        # you make a request to read the assets while the transaction creating them is not done.
        # Indeed, when you make an asset request, the controller has to read the `ir.attachment`
        # table.
        # This scenario happens when you want to print a PDF report for the first time, as the
        # assets are not in cache and must be generated. To workaround this issue, we manually
        # commit the writes in the `ir.attachment` table. It is done thanks to a key in the context.
        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)

        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
        }

        body = self.env['ir.ui.view']._render_template(
            "metroerp_accounting_enhancement.print_template",
            values=dict(rcontext),
        )
        body_html = self.with_context(print_mode=True).get_html(options)

        body = body.replace(b'<body class="o_account_reports_body_print">', b'<body class="o_account_reports_body_print">' + body_html)
        if minimal_layout:
            header = ''
            footer = self.env['ir.actions.report']._render_template("web.internal_layout", values=rcontext)
            spec_paperformat_args = {'data-report-margin-top': 10, 'data-report-header-spacing': 10}
            footer = self.env['ir.actions.report']._render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=footer))
        else:
            rcontext.update({
                    'css': '',
                    'o': self.env.user,
                    'res_company': self.env.company,
                })
            header = self.env['ir.actions.report']._render_template("web.external_layout", values=rcontext)
            header = header.decode('utf-8') # Ensure that headers and footer are correctly encoded
            spec_paperformat_args = {}
            # Default header and footer in case the user customized web.external_layout and removed the header/footer
            headers = header.encode()
            footer = b''
            # parse header as new header contains header, body and footer
            try:
                root = lxml.html.fromstring(header)
                match_klass = "//div[contains(concat(' ', normalize-space(@class), ' '), ' {} ')]"

                for node in root.xpath(match_klass.format('header')):
                    headers = lxml.html.tostring(node)
                    headers = self.env['ir.actions.report']._render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=headers))

                for node in root.xpath(match_klass.format('footer')):
                    footer = lxml.html.tostring(node)
                    footer = self.env['ir.actions.report']._render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=footer))

            except lxml.etree.XMLSyntaxError:
                headers = header.encode()
                footer = b''
            header = headers

        landscape = False
        if len(self.with_context(print_mode=True).get_header(options)[-1]) > 5:
            landscape = True

        return self.env['ir.actions.report']._run_wkhtmltopdf(
            [body],
            header=header, footer=footer,
            landscape=landscape,
            specific_paperformat_args=spec_paperformat_args
        )

    def print_xlsx(self, options, dummy=None):
        return {
                'type': 'ir_actions_account_report_download1',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'xlsx',
                         'financial_id': self.env.context.get('id'),
                         'allowed_company_ids': self.env.context.get('allowed_company_ids'),
                         }
                }

    def get_xlsx(self, options, response=None):
        self = self.with_context(self._set_context(options))
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        sheet = workbook.add_worksheet(self._get_report_name()[:31])

        date_default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'num_format': 'yyyy-mm-dd'})
        date_default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'num_format': 'yyyy-mm-dd'})
        default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 6, 'font_color': '#666666'})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1, 'font_color': '#666666'})
        level_2_col1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_2_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_3_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        level_3_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_3_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})

        #Set the first column width to 50
        sheet.set_column(0, 0, 50)

        y_offset = 0
        headers, lines = self.with_context(no_format=True, print_mode=True, prefetch_fields=False)._get_table(options)

        # Add company name as the first header
        company_name = self.env.company.name
        #sheet.write(y_offset, 0, company_name, title_style)

        # Add headers.
        for header in headers:
            x_offset = 0
            for column in header:
                column_name_formated = column.get('name', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
                if column_name_formated == '':
                    column_name_formated = company_name
                colspan = column.get('colspan', 1)
                if colspan == 1:
                    sheet.write(y_offset, x_offset, column_name_formated, title_style)
                else:
                    sheet.merge_range(y_offset, x_offset, y_offset, x_offset + colspan - 1, column_name_formated, title_style)
                x_offset += colspan
            y_offset += 1

        if options.get('hierarchy'):
            lines = self.with_context(no_format=True)._create_hierarchy(lines, options)
        if options.get('selected_column'):
            lines = self._sort_lines(lines, options)

        # Add lines.
        for y in range(0, len(lines)):
            level = lines[y].get('level')
            if lines[y].get('caret_options'):
                style = level_3_style
                col1_style = level_3_col1_style
            elif level == 0:
                y_offset += 1
                style = level_0_style
                col1_style = style
            elif level == 1:
                style = level_1_style
                col1_style = style
            elif level == 2:
                style = level_2_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') and level_2_col1_total_style or level_2_col1_style
            elif level == 3:
                style = level_3_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') and level_3_col1_total_style or level_3_col1_style
            else:
                style = default_style
                col1_style = default_col1_style

            #write the first column, with a specific style to manage the indentation
            cell_type, cell_value = self._get_cell_type_value(lines[y])
            if cell_type == 'date':
                sheet.write_datetime(y + y_offset, 0, cell_value, date_default_col1_style)
            else:
                sheet.write(y + y_offset, 0, cell_value, col1_style)

            #write all the remaining cells
            for x in range(1, len(lines[y]['columns']) + 1):
                cell_type, cell_value = self._get_cell_type_value(lines[y]['columns'][x - 1])
                if cell_type == 'date':
                    sheet.write_datetime(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, date_default_style)
                else:
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, style)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return generated_file

    def _get_cell_type_value(self, cell):
        if 'date' not in cell.get('class', '') or not cell.get('name'):
            # cell is not a date
            return ('text', cell.get('name', ''))
        if isinstance(cell['name'], (float, datetime.date, datetime.datetime)):
            # the date is xlsx compatible
            return ('date', cell['name'])
        try:
            # the date is parsable to a xlsx compatible date
            lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
            return ('date', datetime.datetime.strptime(cell['name'], lg.date_format))
        except:
            # the date is not parsable thus is returned as text
            return ('text', cell['name'])

    def print_xml(self, options):
        return {
                'type': 'ir_actions_account_report_download1',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'xml',
                         'financial_id': self.env.context.get('id'),
                         'allowed_company_ids': self.env.context.get('allowed_company_ids'),
                         }
                }

    def get_xml(self, options):
        return False

    def print_txt(self, options):
        return {
                'type': 'ir_actions_account_report_download1',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'txt',
                         'financial_id': self.env.context.get('id'),
                         'allowed_company_ids': self.env.context.get('allowed_company_ids'),
                         }
                }

    def get_txt(self, options):
        return False

    ####################################################
    # HOOKS
    ####################################################

    def _get_account_groups_for_asset_report(self):
        """ Get the groups of account code
        return: dict whose keys are the 2 first digits of an account (xx) or a
                range of 2 first digits (xx-yy). If it is not a range, the value
                for that key shouldbe a dict containeing the key 'name'. If it
                is a range, it should also contain a dict for the key 'children'
                that is defined the same way as this return value.
        """
        return {}

class AccountBankReconciliationReport(models.AbstractModel):
    _name = 'account.bank.reconciliation.report'
    _description = 'Bank Reconciliation Report'
    _inherit = "account.report"

    filter_date = {'mode': 'single', 'filter': 'today'}
    filter_all_entries = False

    def _apply_groups(self, columns):
        if self.user_has_groups('base.group_multi_currency') and self.user_has_groups('base.group_no_one'):
            return columns

        return columns[:2] + columns[4:]

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _get_unconsistent_statements(self, options, journal):
        ''' Retrieve the account.bank.statements records on the range of the options date having different starting
        balance regarding its previous statement.
        :param options: The report options.
        :param journal: The account.journal from which this report has been opened.
        :return:        An account.bank.statements recordset.
        '''
        return self.env['account.bank.statement'].search([
            ('journal_id', '=', journal.id),
            ('date', '<=', options['date']['date_to']),
            ('is_valid_balance_start', '=', False),
            ('previous_statement_id', '!=', False),
        ])

    @api.model
    def _get_bank_miscellaneous_move_lines_domain(self, options, journal):
        ''' Get the domain to be used to retrieve the journal items affecting the bank accounts but not linked to
        a statement line.
        :param options: The report options.
        :param journal: The account.journal from which this report has been opened.
        :return:        A domain to search on the account.move.line model.
        '''

        if not journal.default_account_id:
            return None

        domain = [
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('parent_state', '!=', 'cancel'),
            ('account_id', '=', journal.default_account_id.id),
            ('statement_line_id', '=', False),
            ('date', '<=', options['date']['date_to']),
        ]

        if journal.company_id.fiscalyear_lock_date:
            domain.append(('date', '>', journal.company_id.fiscalyear_lock_date))

        if not options['all_entries']:
            domain.append(('parent_state', '=', 'posted'))

        if journal.company_id.account_opening_move_id:
            domain.append(('move_id', '!=', journal.company_id.account_opening_move_id.id))

        return domain

    def open_unconsistent_statements(self, options, params=None):
        ''' An action opening the account.bank.statement view (form or list) depending the 'unconsistent_statement_ids'
        key set on the options.
        :param options: The report options.
        :param params:  -Not used-.
        :return:        An action redirecting to a view of statements.
        '''
        unconsistent_statement_ids = options.get('unconsistent_statement_ids', [])

        action = {
            'name': _("Inconsistent Statements"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement',
        }
        if len(unconsistent_statement_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': unconsistent_statement_ids[0],
                'views': [(False, 'form')],
            })
        else:
            action.update({
                'view_mode': 'list',
                'domain': [('id', 'in', unconsistent_statement_ids)],
                'views': [(False, 'list')],
            })
        return action

    def open_bank_miscellaneous_move_lines(self, options, params):
        ''' An action opening the account.move.line tree view affecting the bank account balance but not linked to
        a bank statement line.
        :param options: The report options.
        :param params:  -Not used-.
        :return:        An action redirecting to the tree view of journal items.
        '''
        journal = self.env['account.journal'].browse(options['active_id'])

        return {
            'name': _('Journal Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_type': 'list',
            'view_mode': 'list',
            'target': 'current',
            'views': [(self.env.ref('account.view_move_line_tree').id, 'list')],
            'domain': self._get_bank_miscellaneous_move_lines_domain(options, journal),
        }

    def action_redirect_to_bank_statement_form(self, options, params):
        ''' Redirect the user to the last bank statement found.
        :param options:     The report options.
        :param params:      The action params containing at least 'statement_id'.
        :return:            A dictionary representing an ir.actions.act_window.
        '''
        last_statement = self.env['account.bank.statement'].browse(params['statement_id'])

        return {
            'name': last_statement.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement',
            'context': {'create': False},
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_id': last_statement.id,
        }

    # -------------------------------------------------------------------------
    # REPORT
    # -------------------------------------------------------------------------

    @api.model
    def _get_templates(self):
        # OVERRIDE
        # - Add a custom main template to add a warning on top about unconsistent bank statements.
        # - Add a custom search template to get a not-editable date filter.
        templates = super()._get_templates()
        templates['main_template'] = 'metroerp_accounting_enhancement.bank_reconciliation_report_main_template'
        return templates

    @api.model
    def _get_report_name(self):
        journal_id = self._context.get('active_id')
        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
            return _("Bank Reconciliation: %s", journal.name)
        return _("Bank Reconciliation")

    # -------------------------------------------------------------------------
    # COLUMNS / LINES
    # -------------------------------------------------------------------------

    @api.model
    def _get_columns_name(self, options):
        return [
            {'name': ''}
        ] + self._apply_groups([
            {'name': _("Date"), 'class': 'date'},
            {'name': _("Label"), 'class': 'whitespace_print o_account_report_line_ellipsis'},
            {'name': _("Amount Currency"), 'class': 'number'},
            {'name': _("Currency"), 'class': 'number'},
            {'name': _("Amount"), 'class': 'number'},
        ])

    @api.model
    def _build_section_report_lines(self, options, journal, unfolded_lines, total, title, title_hover):
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id if journal.currency_id and journal.currency_id != company_currency else False
        report_currency = journal_currency or company_currency
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])
        report_lines = []
        
        if not unfolded_lines:
            return report_lines
        
        line_id = unfolded_lines[0]['parent_id']
        is_unfolded = unfold_all or line_id in options['unfolded_lines']

        section_report_line = {
            'id': line_id,
            'name': title,
            'title_hover': title_hover,
            'columns': self._apply_groups([
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {
                    'name': self.format_value(total, report_currency),
                    'no_format': total,
                },
            ]),
            'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
            'level': 1,
            'unfolded': is_unfolded,
            'unfoldable': True,
        }
        report_lines += [section_report_line] + unfolded_lines
        
        if self.env.company.totals_below_sections:
            report_lines.append({
                'id': '%s_total' % line_id,
                'name': _("Total %s", section_report_line['name']),
                'columns': section_report_line['columns'],
                'class': 'total',
                'level': 3,
                'parent_id': line_id,
            })
        return report_lines

    @api.model
    def _get_statement_report_lines(self, options, journal):
        ''' Retrieve the journal items used by the statement lines that are not yet reconciled and then, need to be
        displayed inside the report.
        :param options: The report options.
        :param journal: The journal as an account.journal record.
        :return:        The report lines for sections about statement lines.
        '''
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id if journal.currency_id and journal.currency_id != company_currency else False
        report_currency = journal_currency or company_currency
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        if not journal.default_account_id:
            return [], []

        # Compute the percentage corresponding of the remaining amount to reconcile.

        tables, where_clause, where_params = self.with_company(journal.company_id)._query_get(options, domain=[
            ('journal_id', '=', journal.id),
            ('account_id', '!=', journal.default_account_id.id),
        ])

        self._cr.execute('''
            SELECT
                st_line.id,
                move.name,
                move.ref,
                move.date,
                st_line.payment_ref,
                st_line.amount,
                st_line.amount_currency,
                st_line.foreign_currency_id,
                COALESCE(SUM(CASE WHEN account_move_line.account_id = %s THEN account_move_line.balance ELSE 0.0 END), 0.0) AS suspense_balance,
                COALESCE(SUM(CASE WHEN account_move_line.account_id = %s THEN 0.0 ELSE account_move_line.balance END), 0.0) AS other_balance
            FROM ''' + tables + '''
            JOIN account_bank_statement_line st_line ON st_line.move_id = account_move_line.move_id
            JOIN account_move move ON move.id = st_line.move_id
            WHERE ''' + where_clause + '''
                AND NOT st_line.is_reconciled
            GROUP BY
                st_line.id,
                move.name,
                move.ref,
                move.date,
                st_line.amount,
                st_line.amount_currency,
                st_line.foreign_currency_id
            ORDER BY st_line.statement_id DESC, move.date, st_line.sequence, st_line.id DESC
        ''', [journal.suspense_account_id.id, journal.suspense_account_id.id] + where_params)

        plus_report_lines = []
        less_report_lines = []
        plus_total = 0.0
        less_total = 0.0

        for res in self._cr.dictfetchall():

            # Rate representing the remaining percentage to be reconciled with something.
            reconcile_rate = abs(res['suspense_balance']) / (abs(res['suspense_balance']) + abs(res['other_balance']))

            amount = res['amount'] * reconcile_rate

            if res['foreign_currency_id']:
                # Foreign currency.

                amount_currency = res['amount_currency'] * reconcile_rate
                foreign_currency = self.env['res.currency'].browse(res['foreign_currency_id'])

                monetary_columns = [
                    {
                        'name': self.format_value(amount_currency, foreign_currency),
                        'no_format': amount_currency,
                    },
                    {'name': foreign_currency.name},
                    {
                        'name': self.format_value(amount, report_currency),
                        'no_format': amount,
                    },
                ]
            else:
                # Single currency.

                monetary_columns = [
                    {'name': ''},
                    {'name': ''},
                    {
                        'name': self.format_value(amount, report_currency),
                        'no_format': amount,
                    },
                ]

            st_report_line = {
                'id': res['id'],
                'name': res['name'],
                'columns': self._apply_groups([
                    {'name': self.format_report_date(res['date']), 'class': 'date'},
                    {'name': self._format_aml_name(res['payment_ref'], res['ref'], '/')},
                ] + monetary_columns),
                'model': 'account.bank.statement.line',
                'caret_options': 'account.bank.statement',
                'level': 3,
            }
            
            residual_amount = monetary_columns[2]['no_format']
            if residual_amount > 0.0:
                st_report_line['parent_id'] = 'plus_unreconciled_statement_lines'
                plus_total += residual_amount
                plus_report_lines.append(st_report_line)
            else:
                st_report_line['parent_id'] = 'less_unreconciled_statement_lines'
                less_total += residual_amount
                less_report_lines.append(st_report_line)

            is_parent_unfolded = unfold_all or st_report_line['parent_id'] in options['unfolded_lines']
            if not is_parent_unfolded:
                st_report_line['style'] = 'display: none;'
        
        return (
            self._build_section_report_lines(options, journal, plus_report_lines, plus_total,
                _("Including Unreconciled Bank Statement Receipts"),
                _("%s for Transactions(+) imported from your online bank account (dated today) that "
                  "are not yet reconciled in Odoo (Waiting the final reconciliation allowing finding the right "
                  "account)") % journal.suspense_account_id.display_name,
            ),
            self._build_section_report_lines(options, journal, less_report_lines, less_total,
                _("Including Unreconciled Bank Statement Payments"),
                _("%s for Transactions(-) imported from your online bank account (dated today) that "
                  "are not yet reconciled in Odoo (Waiting the final reconciliation allowing finding the right "
                  "account)") % journal.suspense_account_id.display_name,
            ),
        )

    @api.model
    def _get_payment_report_lines(self, options, journal):
        ''' Retrieve the journal items used by the payment lines that are not yet reconciled and then, need to be
        displayed inside the report.
        :param options: The report options.
        :param journal: The journal as an account.journal record.
        :return:        The report lines for sections about statement lines.
        '''
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id if journal.currency_id and journal.currency_id != company_currency else False
        report_currency = journal_currency or company_currency
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        accounts = journal.payment_debit_account_id + journal.payment_credit_account_id
        if not accounts:
            return [], []

        # Allow user managing payments without any statement lines.
        # In that case, the user manages transactions only using the register payment wizard.
        if journal.default_account_id in accounts:
            return [], []

        current_date = fields.Date.from_string(options['date']['date_to'])
        if current_date < fields.Date.context_today(self):
            # If the user selected a date in the past, filter payments as well.
            new_options = options
        else:
            # Include payments made in the future.
            new_options = {**options, 'date': None}

        tables, where_clause, where_params = self.with_company(journal.company_id)._query_get(new_options, domain=[
            ('journal_id', '=', journal.id),
            ('account_id', 'in', accounts.ids),
            ('full_reconcile_id', '=', False),
            ('amount_residual_currency', '!=', 0.0)
        ])

        self._cr.execute('''
            SELECT
                account_move_line.account_id,
                account_move_line.payment_id,
                account_move_line.move_id,
                account_move_line.currency_id,
                account_move_line.move_name AS name,
                account_move_line.ref,
                account_move_line.date,
                account.reconcile AS is_account_reconcile,
                SUM(account_move_line.amount_residual) AS amount_residual,
                SUM(account_move_line.balance) AS balance,
                SUM(account_move_line.amount_residual_currency) AS amount_residual_currency,
                SUM(account_move_line.amount_currency) AS amount_currency
            FROM ''' + tables + '''
            JOIN account_account account ON account.id = account_move_line.account_id
            WHERE ''' + where_clause + '''
            GROUP BY 
                account_move_line.account_id,
                account_move_line.payment_id,
                account_move_line.move_id,
                account_move_line.currency_id,
                account_move_line.move_name,
                account_move_line.ref,
                account_move_line.date,
                account.reconcile
            ORDER BY account_move_line.date DESC, account_move_line.payment_id DESC
        ''', where_params)

        plus_report_lines = []
        less_report_lines = []
        plus_total = 0.0
        less_total = 0.0

        for res in self._cr.dictfetchall():
            amount_currency = res['amount_residual_currency'] if res['is_account_reconcile'] else res['amount_currency']
            balance = res['amount_residual'] if res['is_account_reconcile'] else res['balance']

            if res['currency_id'] and journal_currency and res['currency_id'] == journal_currency.id:
                # Foreign currency, same as the journal one.

                if journal_currency.is_zero(amount_currency):
                    continue

                monetary_columns = [
                    {'name': ''},
                    {'name': ''},
                    {
                        'name': self.format_value(amount_currency, journal_currency),
                        'no_format': amount_currency,
                    },
                ]

            elif res['currency_id']:
                # Payment using a foreign currency that needs to be converted to the report's currency.

                foreign_currency = self.env['res.currency'].browse(res['currency_id'])
                journal_balance = company_currency._convert(balance, report_currency, journal.company_id, options['date']['date_to'])

                if foreign_currency.is_zero(amount_currency) and company_currency.is_zero(balance):
                    continue

                monetary_columns = [
                    {
                        'name': self.format_value(amount_currency, foreign_currency),
                        'no_format': amount_currency,
                    },
                    {'name': foreign_currency.name},
                    {
                        'name': self.format_value(journal_balance, report_currency),
                        'no_format': journal_balance,
                    },
                ]

            elif not res['currency_id'] and journal_currency:
                # Single currency in the payment but a foreign currency on the journal.

                journal_balance = company_currency._convert(balance, journal_currency, journal.company_id, options['date']['date_to'])

                if company_currency.is_zero(balance):
                    continue

                monetary_columns = [
                    {
                        'name': self.format_value(balance, company_currency),
                        'no_format': balance,
                    },
                    {'name': company_currency.name},
                    {
                        'name': self.format_value(journal_balance, journal_currency),
                        'no_format': journal_balance,
                    },
                ]

            else:
                # Single currency.

                if company_currency.is_zero(balance):
                    continue

                monetary_columns = [
                    {'name': ''},
                    {'name': ''},
                    {
                        'name': self.format_value(balance, journal_currency),
                        'no_format': balance,
                    },
                ]

            model = 'account.payment' if res['payment_id'] else 'account.move'
            pay_report_line = {
                'id': f"{model}-{res['payment_id'] or res['move_id']}",
                'name': res['name'],
                'columns': self._apply_groups([
                    {'name': self.format_report_date(res['date']), 'class': 'date'},
                    {'name': res['ref']},
                ] + monetary_columns),
                'model': model,
                'caret_options': model,
                'level': 3,
            }

            residual_amount = monetary_columns[2]['no_format']
            if res['account_id'] == journal.payment_debit_account_id.id:
                pay_report_line['parent_id'] = 'plus_unreconciled_payment_lines'
                plus_total += residual_amount
                plus_report_lines.append(pay_report_line)
            else:
                pay_report_line['parent_id'] = 'less_unreconciled_payment_lines'
                less_total += residual_amount
                less_report_lines.append(pay_report_line)

            is_parent_unfolded = unfold_all or pay_report_line['parent_id'] in options['unfolded_lines']
            if not is_parent_unfolded:
                pay_report_line['style'] = 'display: none;'

        return (
            self._build_section_report_lines(options, journal, plus_report_lines, plus_total,
                _("(+) Outstanding Receipts"),
                _("Transactions(+) that were entered into Odoo (%s), but not yet reconciled (Payments triggered by "
                  "invoices/refunds or manually)") % journal.payment_debit_account_id.display_name,
            ),
            self._build_section_report_lines(options, journal, less_report_lines, less_total,
                _("(-) Outstanding Payments"),
                _("Transactions(-) that were entered into Odoo (%s), but not yet reconciled (Payments triggered by "
                  "bills/credit notes or manually)") % journal.payment_credit_account_id.display_name,
            ),
        )

    @api.model
    def _get_lines(self, options, line_id=None):
        print_mode = self._context.get('print_mode')
        journal_id = self._context.get('active_id') or options.get('active_id')
        journal = self.env['account.journal'].browse(journal_id)

        if not journal:
            return []

        # Make sure to keep the 'active_id' inside the options to don't depend of the context when printing the report.
        options['active_id'] = journal_id

        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id if journal.currency_id and journal.currency_id != company_currency else False
        report_currency = journal_currency or company_currency

        last_statement_domain = [('date', '<=', options['date']['date_to'])]
        if not options['all_entries']:
            last_statement_domain.append(('state', 'in', ['posted', 'confirm']))
        last_statement = journal._get_last_bank_statement(domain=last_statement_domain)

        # === Warnings ====

        # Unconsistent statements.
        options['unconsistent_statement_ids'] = self._get_unconsistent_statements(options, journal).ids

        # Strange miscellaneous journal items affecting the bank accounts.
        domain = self._get_bank_miscellaneous_move_lines_domain(options, journal)
        if domain:
            options['has_bank_miscellaneous_move_lines'] = bool(self.env['account.move.line'].search_count(domain))
        else:
            options['has_bank_miscellaneous_move_lines'] = False
        options['account_names'] = journal.default_account_id.display_name

        # ==== Build sub-sections about journal items ====

        plus_st_lines, less_st_lines = self._get_statement_report_lines(options, journal)
        plus_pay_lines, less_pay_lines = self._get_payment_report_lines(options, journal)

        # ==== Build section block about statement lines ====

        domain = self._get_options_domain(options)
        balance_gl = journal._get_journal_bank_account_balance(domain=domain)[0]

        # Compute the 'Reference' cell.
        if last_statement and not print_mode:
            reference_cell = {
                'last_statement_name': last_statement.display_name,
                'last_statement_id': last_statement.id,
                'template': 'metroerp_accounting_enhancement.bank_reconciliation_report_cell_template_link_last_statement',
            }
        else:
            reference_cell = {'name': ''}

        # Compute the 'Amount' cell.
        balance_cell = {
            'name': self.format_value(balance_gl, report_currency),
            'no_format': balance_gl,
        }
        if last_statement:
            report_date = fields.Date.from_string(options['date']['date_to'])
            lines_before_date_to = last_statement.line_ids.filtered(lambda line: line.date <= report_date)
            balance_end = last_statement.balance_start + sum(lines_before_date_to.mapped('amount'))
            difference = balance_gl - balance_end

            if not report_currency.is_zero(difference):
                balance_cell.update({
                    'template': 'metroerp_accounting_enhancement.bank_reconciliation_report_cell_template_unexplained_difference',
                    'style': 'color:orange;',
                    'title': _("The current balance in the General Ledger %s doesn't match the balance of your last "
                               "bank statement %s leading to an unexplained difference of %s.") % (
                        balance_cell['name'],
                        self.format_value(balance_end, report_currency),
                        self.format_value(difference, report_currency),
                    ),
                })

        balance_gl_report_line = {
            'id': 'balance_gl_line',
            'name': _("Balance of %s", options['account_names']),
            'title_hover': _("The Book balance dated today"),
            'columns': self._apply_groups([
                {'name': format_date(self.env, options['date']['date_to']), 'class': 'date'},
                reference_cell,
                {'name': ''},
                {'name': ''},
                balance_cell,
            ]),
            'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
            'level': 0,
            'unfolded': True,
            'unfoldable': False,
        }

        section_st_report_lines = [balance_gl_report_line] + plus_st_lines + less_st_lines

        if self.env.company.totals_below_sections:
            section_st_report_lines.append({
                'id': '%s_total' % balance_gl_report_line,
                'name': _("Total %s", balance_gl_report_line['name']),
                'columns': balance_gl_report_line['columns'],
                'class': 'total',
                'level': balance_gl_report_line['level'] + 1,
            })

        # ==== Build section block about payments ====

        section_pay_report_lines = []

        if plus_pay_lines or less_pay_lines:

            # Compute total to display for this section.
            total = 0.0
            if plus_pay_lines:
                total += plus_pay_lines[0]['columns'][-1]['no_format']
            if less_pay_lines:
                total += less_pay_lines[0]['columns'][-1]['no_format']

            outstanding_payments_report_line = {
                'id': 'outstanding_payments',
                'name': _("Outstanding Payments/Receipts"),
                'title_hover': _("Transactions that were entered into Odoo, but not yet reconciled (Payments triggered by invoices/bills or manually)"),
                'columns': self._apply_groups([
                    {'name': ''},
                    {'name': ''},
                    {'name': ''},
                    {'name': ''},
                    {
                        'name': self.format_value(total, report_currency),
                        'no_format': total,
                    },
                ]),
                'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
                'level': 0,
                'unfolded': True,
                'unfoldable': False,
            }
            section_pay_report_lines += [outstanding_payments_report_line] + plus_pay_lines + less_pay_lines

            if self.env.company.totals_below_sections:
                section_pay_report_lines.append({
                    'id': '%s_total' % outstanding_payments_report_line['id'],
                    'name': _("Total %s", outstanding_payments_report_line['name']),
                    'columns': outstanding_payments_report_line['columns'],
                    'class': 'total',
                    'level': outstanding_payments_report_line['level'] + 1,
                })

        # ==== Build trailing section block ====

        return section_st_report_lines + section_pay_report_lines
