# -*- coding: utf-8 -*-

import ast
import datetime

from dateutil import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class FinancialDocuments(models.Model):
    _name = 'financial.documents'
    _description = 'Financial Documents'
    _order = 'sequence'

    name = fields.Char('Name')
    tech_name = fields.Char('Technical Name')
    color = fields.Integer('Color Index', default=1)
    sequence = fields.Integer("Sequence", default=10)

#Financial Statement.....................
    def action_view_fs(self):
        return {
            'name': 'Financial Statement',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'director.statement',
        }

    def action_create_fs(self):
        return {
            'name': 'Financial Statement',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'director.statement',
        }

    def action_fs_select_template(self):
        ids = self.env['director.statement.template'].search([('company_id','=',self.env.company.id)])
        if not ids:
            return {
                'name': 'FS Default Form',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'director.statement.template',
            }
        return {
            'name': 'FS Report Style',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'director.statement.template',
        }

    def action_fs_view_default(self):
        obj = self.env['director.statement.config'].search([('company_id','=',self.env.company.id)], limit=1)
        if not obj:
            return {
                'name': 'FS Default Form',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'director.statement.config',
            }
        else:
            return {
                'name': 'FS Default Form',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': obj.id,
                'res_model': 'director.statement.config',
            }

#CS Document...................
    def action_view_csdoc(self):
        return {
            'name': 'CS Document',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'cs.document',
        }

    def action_create_csdoc(self):
        return {
            'name': 'CS Document',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'cs.document',
        }

# XBRL................
    def action_view_xbrl(self):
        return {
            'name': self.env.ref('l10n_it_account_balance_eu.account_balance_configuration_act_window').name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'account.balance.configuration',
        }

    def action_create_xbrl(self):
        return {
            'name': self.env.ref('l10n_it_account_balance_eu.account_balance_configuration_act_window').name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.balance.configuration',
        }

    def action_xbrl_lines(self):
        return {
            'name': self.env.ref('l10n_it_account_balance_eu.account_balance_eu_act_window').name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'account.balance.eu',
        }

# Form CS.............
    def action_view_formcs(self):
        return {
            'name': self.env.ref('metroerp_iras.form_cs_action').name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'form.cs',
        }

    def action_create_formcs(self):
        return {
            'name': self.env.ref('metroerp_iras.form_cs_action').name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'form.cs',
        }

    def action_import_formcs_bulk(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'formcs.bulk.import',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new'
        }

    def action_coa_mapping(self):
        return {
            'name': self.env.ref('account.action_account_form').name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,kanban,form',
            'view_type': 'form',
            'search_view_id': self.env.ref('account.view_account_search').id,
            'res_model': 'account.account',
            'context': {'search_default_activeacc': True}
        }
