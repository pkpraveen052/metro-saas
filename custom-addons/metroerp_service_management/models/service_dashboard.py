# -*- coding: utf-8 -*-

import ast
import datetime

from dateutil import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ServiceDashboard(models.Model):
    _name = 'service.dashboard'
    _description = 'Service Dashboard'
    _order = 'sequence'

    name = fields.Char('Name')
    tech_name = fields.Char('Technical Name')
    color = fields.Integer('Color Index', default=1)
    sequence = fields.Integer("Sequence", default=10)

    # Financial Statement.....................
    def action_view_sf(self):
        return {
            'name': 'Service Form',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'service.management',
        }

    def action_create_sf(self):
        return {
            'name': 'Service Form',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'service.management',
        }

    # def action_fs_select_template(self):
    #     ids = self.env['director.statement.template'].search([('company_id', '=', self.env.company.id)])
    #     if not ids:
    #         return {
    #             'name': 'FS Default Form',
    #             'type': 'ir.actions.act_window',
    #             'view_mode': 'form',
    #             'view_type': 'form',
    #             'res_model': 'director.statement.template',
    #         }
    #     return {
    #         'name': 'FS Report Style',
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'tree,form',
    #         'view_type': 'form',
    #         'res_model': 'director.statement.template',
    #     }
    #
    # def action_fs_view_default(self):
    #     obj = self.env['director.statement.config'].search([('company_id', '=', self.env.company.id)], limit=1)
    #     if not obj:
    #         return {
    #             'name': 'FS Default Form',
    #             'type': 'ir.actions.act_window',
    #             'view_mode': 'form',
    #             'view_type': 'form',
    #             'res_model': 'director.statement.config',
    #         }
    #     else:
    #         return {
    #             'name': 'FS Default Form',
    #             'type': 'ir.actions.act_window',
    #             'view_mode': 'form',
    #             'view_type': 'form',
    #             'res_id': obj.id,
    #             'res_model': 'director.statement.config',
    #         }
