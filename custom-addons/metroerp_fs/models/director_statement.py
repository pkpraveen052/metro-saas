# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import datetime
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
import random
import string

class DirectorStatement(models.Model):
    _name = 'director.statement'
    _description = 'Account Financial Statement'
    _inherit = "mail.thread"
    _rec_name = 'year'

    @api.model
    def default_get(self, fields):
        res = super(DirectorStatement, self).default_get(fields)
        template_obj = self.env['director.statement.template'].sudo().search([('company_id','=',self.env.company.id)])
        if template_obj:
            res['template_id'] = template_obj[0].id
        else:
            raise UserError("Define atleast one FS Report Style.")
        config_obj = self.env['director.statement.config'].sudo().search([('company_id','=',self.env.company.id)])
        if config_obj:
            res['config_id'] = config_obj.id
        year = datetime.now().year
        res['year'] = str(year)

        pl_lines = [
            (0,0,{'name':'Profit and Loss'}),
            (0,0,{'name': 'Total Income', 'level':2}),
            (0,0,{'name': 'Operating Income', 'level': 3}),
            (0,0,{'name': 'Cost Of Good Sold', 'level': 2}),
            (0,0,{'name': 'Gross Profit', 'level': 2}),
            (0,0,{'name': 'Expense', 'level': 2}),
            (0,0,{'name': 'Expenses', 'level': 3}),
            (0,0,{'name': 'Depreciation', 'level': 3}),
            (0,0,{'name': 'Operating Profit', 'level': 2}),
            (0,0,{'name': 'Other Income', 'level': 2}),
            (0,0,{'name': 'Other Expenses', 'level': 2}),
            (0,0,{'name': 'Net Profit', 'level': 2})
        ]
        res.update({
            'pl_ids': pl_lines
            })
        bs_lines = [
            (0,0,{'name':'Balance Sheet'}),
            (0,0,{'name': 'Assets', 'level':2}),
            (0,0,{'name': 'Fixed Assets', 'level':3}),
            (0,0,{'name': 'Non-current Assets', 'level':3}),
            (0,0,{'name': 'Current Assets', 'level':3}),
            (0,0,{'name': 'Bank and Cash Accounts', 'level':4}),
            (0,0,{'name': 'Receivables', 'level':4}),
            (0,0,{'name': 'Short Term Borrowings', 'level':4}),
            (0,0,{'name': 'Prepayments', 'level':4}),
            (0,0,{'name': 'LIABILITIES', 'level':2}),
            (0,0,{'name': 'Current Liabilities', 'level':3}),
            (0,0,{'name': 'Payables', 'level':4}),
            (0,0,{'name': 'Non Current Liabilities', 'level':3}),
            (0,0,{'name': 'Net Assets', 'level':2}),
            (0,0,{'name': 'EQUITY + LIABILITIES', 'level':2}),
            (0,0,{'name': 'EQUITY', 'level':2}),
            (0,0,{'name': 'Shares', 'level':3}),
            (0,0,{'name': 'Retained Earnings', 'level':3}),
            (0,0,{'name': 'Current Year Earnings', 'level':4}),
            (0,0,{'name': 'Previous Years Earnings', 'level':4}),
        ]
        res.update({
            'bs_ids': bs_lines
            })


        cf_ids = []
        cash_flow_config_obj = self.env.ref('ks_dynamic_financial_report.ks_df_report_cash_flow0')
        result = cash_flow_config_obj.ks_get_dynamic_fin_info(False, {})
        for dic in result['ks_report_lines']:
            if dic['style_type'] != 'sub':
                cf_ids.append(
                    (0,0,{'name': dic['ks_name'], 'level': dic['ks_level']})
                    )
        res.update({
            'cf_ids': cf_ids
        })
        curr_year = int(res.get('year'))
        # prev_year = int(res.get('year')) - 1

        fiscal_year = self.env['account.fiscal.year'].sudo().search(
            [('company_id', '=', res.get('company_id')), ('name', '=', curr_year)], limit=1)
        fiscal_year_date_from = ''
        fiscal_year_date_to = ''
        if fiscal_year.date_from:
            fiscal_year_date_from = datetime.strptime(str(fiscal_year.date_from), '%Y-%m-%d').strftime('%d/%m/%Y')
        if fiscal_year.date_to:
            fiscal_year_date_to = datetime.strptime(str(fiscal_year.date_to), '%Y-%m-%d').strftime('%d/%m/%Y')

        # fiscal_year_date_to = str(fiscal_year.date_from)
        # fiscal_year_date_to = str(fiscal_year.date_to)
        cost_lines = [
            (0, 0, {'name': 'At ' + fiscal_year_date_from}),
            (0, 0, {'name': 'Addition'}),
            (0, 0, {'name': 'Disposals'}),
            (0, 0, {'name': 'At ' + fiscal_year_date_to}),
        ]
        depreciation_lines = [
            (0, 0, {'name': 'At ' + fiscal_year_date_from}),
            (0, 0, {'name': 'Charge for the year'}),
            (0, 0, {'name': 'Disposals'}),
            (0, 0, {'name': 'At ' + fiscal_year_date_to}),
        ]
        carry_amount_lines = [
            (0, 0, {'name': 'At ' + fiscal_year_date_from}),
            (0, 0, {'name': 'At ' + fiscal_year_date_to}),
        ]

        res.update({
            'plant_equipment_cost_ids': cost_lines,
            'plant_equipment_depreciation_ids': depreciation_lines,
            'plant_equipment_carryingamount_ids': carry_amount_lines
        })
        return res

    def _get_year(self):
        lst = []
        year = datetime.now().year
        for ya in range(year - 4, year + 1):
            lst.append((str(ya), str(ya)))
        return lst

    @api.depends('year')
    def _get_previous_year(self):
        self.previous_year = int(self.year) - 1

    @api.depends('year')
    def _get_current_year(self):
        self.current_year = int(self.year)

    year = fields.Selection(_get_year, string="Year", required=True, tracking=True, default=datetime.now().year)
    current_year = fields.Char(compute=_get_current_year, store=True, string='Current Year')
    previous_year = fields.Char(compute=_get_previous_year, store=True, string='Previous Year')
    fyear_end_date = fields.Date('Current Financial Year End Date')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    config_id = fields.Many2one('director.statement.config', string='Default Configuration', tracking=True, required=False)
    template_id = fields.Many2one('director.statement.template', string='Select Style', tracking=True)
    director_statement_opinion1 = fields.Text('Director statement opinion 1', required=True)
    director_statement_opinion2 = fields.Text('Director statement opinion 2', required=True)
    director_statement_arrangements = fields.Text('Director Statement Arrangement', required=True)
    director_statement_interests = fields.Text('Director Statement Interests', required=True)
    director_statement_share_options = fields.Text('Director Statement Share Options', required=True)
    random_docid = fields.Char('DocID')
    ordinary_shares_ids = fields.One2many('ordinary.shares.lines', 'statement_id', 'Ordinary Shares')
    pl_ids = fields.One2many('pl.lines', 'statement_id', 'ProftLoss Lines')
    bs_ids = fields.One2many('bs.lines', 'statement_id', 'BalanceSheet Lines')
    cf_ids = fields.One2many('cf.lines', 'statement_id', 'CashFlow Lines')

    eq_changes_prev_year_start_date = fields.Char('Equity Changes - Previous Year - Start Date')
    eq_changes_prev_year_end_date = fields.Char('Equity Changes - Previous Year - End Date')
    eq_changes_curr_year_start_date = fields.Char('Equity Changes - Current Year - Start Date')
    eq_changes_curr_year_end_date = fields.Char('Equity Changes - Current Year - End Date')

    eq_changes_prev_year_start_date_share_capital = fields.Integer('Equity Changes - Previous Year - Start Date - Share Capital')
    eq_changes_prev_year_start_date_retained_earning = fields.Integer('Equity Changes - Previous Year - Start Date - Retained Earnings')
    eq_changes_prev_year_start_date_total = fields.Integer('Equity Changes - Previous Year - Start Date - Total')

    eq_changes_tot_compre_income_prev_year_retained_earning = fields.Integer('Equity Changes - Previous Year - Total Comprehensive Income - Retained Earning')
    eq_changes_tot_compre_income_prev_year_total = fields.Integer('Equity Changes - Previous Year - Total Comprehensive Income - Total')

    eq_changes_prev_year_end_date_share_capital = fields.Integer('Equity Changes - Previous Year - Start Date - Share Capital')
    eq_changes_prev_year_end_date_retained_earning = fields.Integer('Equity Changes - Previous Year - Start Date - Retained Earnings')
    eq_changes_prev_year_end_date_total = fields.Integer('Equity Changes - Previous Year - Start Date - Total')
    # --
    eq_changes_curr_year_start_date_share_capital = fields.Integer('Equity Changes - Current Year - Start Date - Share Capital')
    eq_changes_curr_year_start_date_retained_earning = fields.Integer('Equity Changes - Current Year - Start Date - Retained Earnings')
    eq_changes_curr_year_start_date_total = fields.Integer('Equity Changes - Current Year - Start Date - Total')

    eq_changes_tot_compre_income_curr_year_retained_earning = fields.Integer('Equity Changes - Current Year - Total Comprehensive Income - Retained Earning')
    eq_changes_tot_compre_income_curr_year_total = fields.Integer('Equity Changes - Current Year - Total Comprehensive Income - Total')

    eq_changes_curr_year_end_date_share_capital = fields.Integer('Equity Changes - Current Year - Start Date - Share Capital')
    eq_changes_curr_year_end_date_retained_earning = fields.Integer('Equity Changes - Current Year - Start Date - Retained Earnings')
    eq_changes_curr_year_end_date_total = fields.Integer('Equity Changes - Current Year - Start Date - Total')

    current_accounting = fields.Boolean('Current Accounting')

    plant_equipment_cost_ids = fields.One2many('plant.equipment.cost', 'statement_id', 'Cost')
    plant_equipment_depreciation_ids = fields.One2many('plant.equipment.depreciation', 'statement_id', 'Depreciation')
    plant_equipment_carryingamount_ids = fields.One2many('plant.equipment.carrying.amount', 'statement_id', 'Carrying Amount')

    @api.model
    def create(self, vals):
        obj = super(DirectorStatement, self).create(vals)

        curr_year = int(obj.year)
        prev_year = int(obj.year) -1

        fiscal_o = self.env['account.fiscal.year'].sudo().search([('company_id','=',obj.company_id.id),('name','=',curr_year)], limit=1)
        if not fiscal_o:
            raise ValidationError("Fiscal Year " + str(curr_year) + " is not configured.")

        fiscal_o = self.env['account.fiscal.year'].sudo().search([('company_id','=',obj.company_id.id),('name','=',prev_year)], limit=1)
        if not fiscal_o:
            raise ValidationError("Fiscal Year " + str(prev_year) + " is not configured.")
        obj.generate_docid()
        return obj

    def generate_docid(self):
        def generate_random_string(length=30):
            characters = string.ascii_letters + string.digits
            random_string = ''.join(random.choices(characters, k=length))
            return random_string
        self.write({'random_docid': generate_random_string()})

    def action_print_report(self):
        print("\n\n\n",self)
        print(self._context)
        ctx = self._context or {}
        ctx = dict(ctx)
        if 'params' in ctx:
            ctx.pop('params')
        if 'active_model' in ctx:
            ctx.pop('active_model')
        if 'active_id' in ctx:
            ctx.pop('active_id')
        if 'active_ids' in ctx:
            ctx.pop('active_ids')
        print(ctx)
        return self.with_context(ctx).template_id.report_id.report_action(self)

    def equity_changes_format_fields(self, val):
        def format_float_custom(value):
            if value == 0:
                return '-'
            elif value < 0:
                formatted_value = f"({abs(value):,})"
            else:
                formatted_value = f"{value:,}"
            return formatted_value
        return format_float_custom(val)

    @api.onchange('company_id', 'year')
    def onchange_company(self):
        curr_year = int(self.year)
        prev_year = int(self.year) -1

        fiscal_o = self.env['account.fiscal.year'].sudo().search([('company_id','=',self.company_id.id),('name','=',curr_year)], limit=1)
        if not fiscal_o:
            raise ValidationError("Fiscal Year " + str(curr_year) + " is not configured.")
        fiscal_o = self.env['account.fiscal.year'].sudo().search([('company_id','=',self.company_id.id),('name','=',prev_year)], limit=1)
        if not fiscal_o:
            raise ValidationError("Fiscal Year " + str(prev_year) + " is not configured.")

        fiscal_o = self.env['account.fiscal.year'].sudo().search([('company_id','=',self.company_id.id),('name','=',curr_year)], limit=1)
        curr_year_date_from = fiscal_o.date_from
        curr_year_date_to = fiscal_o.date_to

        fiscal_o = self.env['account.fiscal.year'].sudo().search([('company_id','=',self.company_id.id),('name','=',prev_year)], limit=1)
        prev_year_date_from = fiscal_o.date_from
        prev_year_date_to = fiscal_o.date_to

        self.eq_changes_prev_year_start_date = 'At ' + prev_year_date_from.strftime('%d %B %Y')
        self.eq_changes_prev_year_end_date = 'At ' + prev_year_date_to.strftime('%d %B %Y')
        self.eq_changes_curr_year_start_date = 'At ' + curr_year_date_from.strftime('%d %B %Y')
        self.eq_changes_curr_year_end_date = 'At ' + curr_year_date_to.strftime('%d %B %Y')

    @api.onchange('config_id', 'year')
    def onchange_config_id(self):
        if not self.config_id:
            return

        self.template_id = self.config_id.template_id     

        fyear_end_date, formatted_date = False, False
        fiscal_o = self.env['account.fiscal.year'].sudo().search([('company_id','=',self.company_id.id),('name','=',self.year)], limit=1)
        if fiscal_o:
            self.fyear_end_date = fiscal_o.date_to
            formatted_date = fiscal_o.date_to.strftime("%d %B %Y").upper()
            print("formatted_date ====",formatted_date)
        else:
            raise UserError("Please configure the Fiscal Years properly for this company.")

        placeholder = "{{fy_end_year}}"
        replacement = formatted_date
        updated_statement = self.config_id.director_statement_opinion1.replace(placeholder, replacement)
        self.director_statement_opinion1 = updated_statement

        self.director_statement_opinion2 = self.config_id.director_statement_opinion2
        self.director_statement_arrangements = self.config_id.director_statement_arrangements
        self.director_statement_interests = self.config_id.director_statement_interests
        self.director_statement_share_options = self.config_id.director_statement_share_options

        ord_shares_lis = []
        for obj in self.config_id.director_ids:
            ord_shares_lis.append((0,0,{'director_name': obj.name}))
        if ord_shares_lis:
            self.ordinary_shares_ids = [(5,)] + ord_shares_lis

    def fetch(self):
        if self.current_accounting:
            self.populate_profit_loss()
            self.populate_balance_sheet()        
            self.populate_cash_flow()
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

    def populate_profit_loss(self):
        print("\n\n\n\n\n\n >>>>>>>>>>>>>>>>>>>>>>>>>>>      populate_profit_loss() >>>>>")

        year_dic2 = {
            int(self.year): 'this_year', 
            int(self.year) -1: 'last_year'}

        curr_vals = []
        pl_lines = []

        curr_year = int(self.year)
        prev_year = int(self.year) -1

        fiscal_o = self.env['account.fiscal.year'].sudo().search([('company_id','=',self.company_id.id),('name','=',curr_year)], limit=1)
        curr_year_date_from = str(fiscal_o.date_from)
        curr_year_date_to = str(fiscal_o.date_to)

        fiscal_o = self.env['account.fiscal.year'].sudo().search([('company_id','=',self.company_id.id),('name','=',prev_year)], limit=1)
        prev_year_date_from = str(fiscal_o.date_from)
        prev_year_date_to = str(fiscal_o.date_to)

        result = self.env.ref('ks_dynamic_financial_report.ks_df_pnl0').with_context({
                'external_call_pl': {
                    'date': {'ks_string': str(curr_year), 
                        'ks_interval_type': 'year', 
                        'ks_process': 'range', 
                        'ks_range_constrain': False, 
                        'ks_start_date': curr_year_date_from, 
                        'ks_end_date': curr_year_date_to, 
                        'ks_filter': year_dic2[curr_year]},                        
                    'ks_differ': {
                        'ks_differentiate_filter': 'earlier_interval', 
                        'ks_no_of_interval': 1, 
                        'ks_start_date': prev_year_date_from, 
                        'ks_end_date': prev_year_date_to, 
                        'ks_intervals': 
                            [{'ks_string': str(prev_year), 
                            'ks_interval_type': 'year', 
                            'ks_process': 'range', 
                            'ks_range_constrain': False, 
                            'ks_start_date': prev_year_date_from, 
                            'ks_end_date': prev_year_date_to}], 
                        'ks_string': str(prev_year), 
                        'ks_interval_type': 'year', 
                        'ks_process': 'range', 
                        'ks_range_constrain': False
                        }}}).ks_get_dynamic_fin_info(False, {})


        temp_dic = {}        
        for dic in result['ks_report_lines']:
            if dic.get('ks_df_report_account_type') == 'account' and dic['parent'] in temp_dic:
                temp_dic[dic['parent']]['account_ids'].append((0, 0,
                                                    {'name': dic['ks_name'],
                                                    'bal_curr_year_temp': dic['balance'],
                                                    'bal_prev_year_temp': dic['balance_cmp']['comp_bal_' + str(prev_year)]}))
            else:
                temp_dic[dic['self_id']] = {'account_ids': []}
                a = {
                    'bal_curr_year_temp': dic['balance'],
                    'bal_prev_year_temp': dic['balance_cmp']['comp_bal_' + str(prev_year)],
                    'name': dic['ks_name'], #". . " * len(dic['list_len']) +
                    'self_id': dic['self_id'],
                    'level': len(dic['list_len']) + 1
                }
                pl_lines.append(a)

        for dic in pl_lines:
            if dic['self_id'] in temp_dic:
                dic.update(temp_dic[dic['self_id']])
                dic.pop('self_id')
            curr_vals.append((0,0,dic))

        self.write({'pl_ids': [(5,)] + curr_vals})

    def populate_balance_sheet(self):
        print("\npopulate_balance_sheet() >>>>>")
        year_dic = {int(self.year): 'bal_curr_year_temp', int(self.year) -1: 'bal_prev_year_temp'}
        curr_vals = []

        child_dic, n_dic = {}, {}

        for year in year_dic.keys():
            fiscal_o = self.env['account.fiscal.year'].sudo().search([('company_id','=',self.company_id.id),('name','=',year)], limit=1)
            balance_sheet_config_obj = self.env.ref('ks_dynamic_financial_report.ks_dynamic_financial_balancesheet')
            result = balance_sheet_config_obj.with_context({'external_call_bs': {'date': {'ks_string': 'As of %s' % (str(fiscal_o.date_to)), 'ks_filter': 'last_year', 'ks_interval_type': 'year', 'ks_start_date': str(fiscal_o.date_from), 'ks_end_date': str(fiscal_o.date_to)}}}).ks_get_dynamic_fin_info(False, {})
            print("\n",result['ks_report_lines'])
            for dic in result['ks_report_lines']:
                ks_name = dic['ks_name'] + "__" + str(dic['ks_level'])
                dic['ks_name'] = ks_name
                if dic.get('ks_df_report_account_type') == 'account':
                    if temp_dic['ks_name'] in child_dic.keys():
                        if ks_name in child_dic[temp_dic['ks_name']].keys():
                            child_dic[temp_dic['ks_name']][ks_name].update({year_dic[year]: dic['balance']})
                        else:
                            child_dic[temp_dic['ks_name']].update({ks_name: {'bal_curr_year_temp': 0.0, 'bal_prev_year_temp': 0.0}})
                            child_dic[temp_dic['ks_name']][ks_name].update({year_dic[year]: dic['balance']})
                    else:
                        child_dic.update({temp_dic['ks_name'] : {ks_name: {'bal_curr_year_temp': 0.0, 'bal_prev_year_temp': 0.0}}})
                        child_dic[temp_dic['ks_name']][ks_name][year_dic[year]] = dic['balance']
                else:
                    if dic.get('ks_name') in n_dic:
                        n_dic[ks_name].update({year_dic[year]: dic['balance']})
                    else:
                        n_dic.update({ks_name: {'bal_curr_year_temp': 0.0, 'bal_prev_year_temp': 0.0, 'ks_level': dic['ks_level']}})
                        n_dic[ks_name][year_dic[year]] = dic['balance']
                    temp_dic = dic

        print("\nn_dic",n_dic)
        print("\nchild_dic",child_dic)
        for a, b in n_dic.items():
            dic = {'name': a.split("__")[0], 'bal_curr_year_temp': b['bal_curr_year_temp'], 'bal_prev_year_temp': b['bal_prev_year_temp'], 'level': b['ks_level']}
            if a in child_dic.keys():
                account_ids = []
                for c,d in child_dic[a].items():
                    account_ids.append((0, 0, {'name': c.split("__")[0], 'bal_curr_year_temp': d['bal_curr_year_temp'], 'bal_prev_year_temp': d['bal_prev_year_temp']}))
                dic['account_ids'] = account_ids
            curr_vals.append((0, 0, dic))
        print("\ncurr_vals ===",curr_vals)
        self.write({'bs_ids': [(5,)] + curr_vals})

    def populate_cash_flow(self):
        print("\npopulate_cash_flow() >>>>>")
        year_dic = {int(self.year): 'bal_curr_year_temp', int(self.year) -1: 'bal_prev_year_temp'}
        year_dic2 = {
            int(self.year): 'this_year', 
            int(self.year) -1: 'last_year'}

        child_dic, n_dic, curr_vals = {}, {}, []

        for year in year_dic.keys():
            fiscal_o = self.env['account.fiscal.year'].sudo().search([('company_id','=',self.company_id.id),('name','=',year)], limit=1)
            cash_flow_config_obj = self.env.ref('ks_dynamic_financial_report.ks_df_report_cash_flow0')
            result = cash_flow_config_obj.with_context({'external_call_bs': {'date': {'ks_string': 'As of %s' % (str(fiscal_o.date_to)), 'ks_filter': 'last_year', 'ks_interval_type': 'year', 'ks_start_date': str(fiscal_o.date_from), 'ks_end_date': str(fiscal_o.date_to)}}}).ks_get_dynamic_fin_info(False, {})

            result = cash_flow_config_obj.with_context(
                {'external_call_cf': 
                    {'date': {
                        'ks_string': str(year), 
                        'ks_interval_type': 'year', 
                        'ks_process': 'range', 
                        'ks_range_constrain': False, 
                        'ks_start_date': str(fiscal_o.date_from), 
                        'ks_end_date': str(fiscal_o.date_to), 
                        'ks_filter': year_dic2.get(year)
                        }
                }}).ks_get_dynamic_fin_info(False, {})

            for dic in result['ks_report_lines']:
                ks_name = dic['ks_name'] + '_' + str(dic['self_id'])
                if dic.get('ks_df_report_account_type') == 'account':                    
                    if temp_dic['ks_name'] in child_dic.keys():
                        if ks_name in child_dic[temp_dic['ks_name']].keys():
                            child_dic[temp_dic['ks_name']][ks_name].update({year_dic[year]: dic['balance']})
                        else:
                            child_dic[temp_dic['ks_name']].update({ks_name: {'bal_curr_year_temp': 0.0, 'bal_prev_year_temp': 0.0}})
                            child_dic[temp_dic['ks_name']][ks_name].update({year_dic[year]: dic['balance']})
                    else:
                        child_dic.update({temp_dic['ks_name'] : {ks_name: {'bal_curr_year_temp': 0.0, 'bal_prev_year_temp': 0.0}}})
                        child_dic[temp_dic['ks_name']][ks_name][year_dic[year]] = dic['balance']
                else:
                    if ks_name in n_dic:
                        n_dic[ks_name].update({year_dic[year]: dic['balance']})
                    else:
                        n_dic.update({ks_name: {'bal_curr_year_temp': 0.0, 'bal_prev_year_temp': 0.0, 'ks_level': dic['ks_level']}})
                        n_dic[ks_name][year_dic[year]] = dic['balance']
                    temp_dic = dic
        
        for a, b in n_dic.items():
            dic = {'name': a, 'bal_prev_year_temp': b['bal_prev_year_temp'], 'bal_curr_year_temp': b['bal_curr_year_temp'], 'level': b['ks_level'] + 1}
            if a in child_dic.keys():
                account_ids = []
                for c,d in child_dic[a].items():
                    account_ids.append((0, 0, {'name': c, 'bal_prev_year_temp': d['bal_prev_year_temp'], 'bal_curr_year_temp': d['bal_curr_year_temp']}))
                dic['account_ids'] = account_ids
            dic['name'] = dic['name'].split('_')[0]
            curr_vals.append((0, 0, dic))

        self.write({'cf_ids': [(5,)] + curr_vals})

    def get_fiscalyear_enddate(self):
        print("\nget_fiscalyear_enddate() >>>>>>")
        fiscal_o = self.env['account.fiscal.year'].sudo().search([('company_id','=',self.company_id.id),('name','=',self.year)], limit=1)
        if fiscal_o:
            formatted_date = fiscal_o.date_to.strftime("%d %B %Y").upper()
            print("formatted_date ====",formatted_date)
            return formatted_date

    def populate_equity_changes(self):
        curr_year = int(self.year)
        prev_year = int(self.year) -1

        fiscal_o = self.env['account.fiscal.year'].sudo().search([('company_id','=',self.company_id.id),('name','=',curr_year)], limit=1)
        curr_year_date_from = fiscal_o.date_from
        curr_year_date_to = fiscal_o.date_to

        fiscal_o = self.env['account.fiscal.year'].sudo().search([('company_id','=',self.company_id.id),('name','=',prev_year)], limit=1)
        prev_year_date_from = fiscal_o.date_from
        prev_year_date_to = fiscal_o.date_to

        self.write({
            'eq_changes_prev_year_start_date': 'At ' + prev_year_date_from.strftime('%d %B %Y'),
            'eq_changes_prev_year_end_date': 'At ' + prev_year_date_to.strftime('%d %B %Y'),
            'eq_changes_curr_year_start_date': 'At ' + curr_year_date_from.strftime('%d %B %Y'),
            'eq_changes_curr_year_end_date': 'At ' + curr_year_date_to.strftime('%d %B %Y'),
            })

    def get_pl_notes(self, note=None):
        print("\n\nget_pl_notes() >>>>>>>>>>>>>>>>>>> notessssssssss")
        print("self=====",self)
        print("note====",note,type(note))
        print(self.pl_ids.filtered(lambda x: x.note == str(note)))
        content_found = False
        for line in self.pl_ids.filtered(lambda x: x.note == str(note)):
            print("returning noteeeeeeeeee",note)
            return line.content or ""
            content_found = True
            break    
        if not content_found:
            return ""

    def get_pl_accounts(self, note=None):
        print("\n\nget_pl_accounts() >>>>>>>>>>>>>>>>>>>")
        print("self=====",self)
        content_found = False
        for line in self.pl_ids.filtered(lambda x: x.note == str(note)):
            print("returning get_pl_accounts")
            return line.account_ids
            content_found = True
            break    
        if not content_found:
            return []

    def get_director_label_uppercase(self):
        if not len(self.config_id.director_ids) > 1:
            return 'DIRECTORS'
        else:
            return 'DIRECTOR'

    def get_director_label_lowercase(self):
        if not len(self.config_id.director_ids) > 1:
            return 'Directors'
        else:
            return 'Director'

    def get_director_statement_content_label(self):
        if not len(self.config_id.director_ids) > 1:
            return 'The Director at the date of this report is'
        else:
            return 'The Directors at the date of this report are'

    def get_their_his_label(self):
        return len(self.config_id.director_ids) > 1 and 'their' or 'his'

    def get_current_date(self):
        print("\nget_current_date() >>>>>>")
        def get_ordinal_suffix(day):
            if 11 <= day <= 13:
                return 'th'
            last_digit = day % 10
            if last_digit == 1:
                return 'st'
            elif last_digit == 2:
                return 'nd'
            elif last_digit == 3:
                return 'rd'
            else:
                return 'th'

        def get_current_date_string():
            now = datetime.now()
            day = now.day
            month = now.strftime("%B")
            year = now.year
            ordinal_suffix = get_ordinal_suffix(day)
            return f"{day}{ordinal_suffix} {month} {year}"

        current_date_string = get_current_date_string()
        return current_date_string

    def get_director2_name(self):
        if len(self.config_id.director_ids) > 1:
            return self.config_id.director_ids[1].name
        else:
            return False

    def get_director2_signature_allowed(self):
        if len(self.config_id.director_ids) > 1 and self.config_id.director_ids[1].required_signature:
            return True
        else:
            return False 
# class ResUsers(models.Model):
#     _inherit = 'res.users'

#     def print_name(self):
#         return 'TEST NAME'
