# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class DirectorStatementTemplate(models.Model):
    _name = 'director.statement.template'

    name = fields.Char('Name of the Style', required=True)
    report_id = fields.Many2one('ir.actions.report', domain=[('report_type','=','docx-docx'),('model','=','director.statement')], string='Select Report', help='Technical')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    report_docx_template = fields.Binary(
        string="Report docx template",
    )

    @api.model
    def create(self, vals):
        obj = super(DirectorStatementTemplate, self).create(vals)
        if not vals.get('report_id', False):
            report_obj = self.env.ref('metroerp_fs.ir_actions_report_metro_style2')
            if report_obj:
                custom_report_field_ids = []
                for line in report_obj.custom_report_field_ids:
                    custom_report_field_ids.append((0,0,{
                        'name': line.name,
                        'technical_name': line.technical_name,
                        'default_value': line.default_value
                        }))
            report_id = self.env['ir.actions.report'].sudo().create({
                'name': 'Financial Statement - ' + str(obj.name),
                'report_type': 'docx-docx',
                'model': 'director.statement',
                'print_report_name': "'Financial_Statement - %s' % (object.year)",
                'report_docx_template': obj.report_docx_template,
                'custom_report_field_ids': custom_report_field_ids or False
                    [()]
                }).id
            obj.write({'report_id': report_id})
            obj.update_custom_fields()
        return obj

    def write(self, vals):
        res = super(DirectorStatementTemplate, self).write(vals)
        for obj in self:
            if vals.get('name'):
                obj.report_id.write({'name': 'Financial Statement - ' + str(obj.name)})
            if vals.get('report_docx_template'):
                obj.report_id.write({'report_docx_template': obj.report_docx_template})
        return res
        

    def unlink(self):
        for obj in self:
            if obj.report_id:
                obj.sudo().report_id.unlink()
        return super(DirectorStatementTemplate, self).unlink()

    def update_custom_fields(self):
        report_obj = self.env.ref('metroerp_fs.ir_actions_report_metro_style2')
        if report_obj:
            custom_report_field_ids = []
            for line in report_obj.custom_report_field_ids:
                custom_report_field_ids.append((0,0,{
                    'name': line.name,
                    'technical_name': line.technical_name,
                    'default_value': line.default_value
                    }))
            if custom_report_field_ids:
                self.report_id.write({'custom_report_field_ids': [(5,)] + custom_report_field_ids})