# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class DirectorStatementTemplate(models.Model):
    _name = 'director.statement.template'

    name = fields.Char('Name of the Style', required=True)
    report_id = fields.Many2one('ir.actions.report', domain=[('report_type','=','docx-docx'),('model','=','director.statement')], string='Select Report', help='Technical')


    @api.model
    def create(self, vals):
        obj = super(DirectorStatementTemplate, self).create(vals)
        if not vals.get('report_id', False):
            report_id = self.env['ir.actions.report'].sudo().create({
                'name': 'Financial Statement - ' + str(obj.name),
                'report_type': 'docx-docx',
                'model': 'director.statement',
                'print_report_name': "'Financial_Statement - %s' % (object.year)"
                }).id
            obj.write({'report_id': report_id})
        return obj

    def write(self, vals):
        obj = super(DirectorStatementTemplate, self).write(vals)
        if vals.get('name'):
            obj.report_id.write({'name': 'Financial Statement - ' + str(obj.name)})
        return obj
        
