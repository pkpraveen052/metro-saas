# -*- coding: utf-8 -*-

from odoo import api, models, tools, fields


class ResCompany(models.Model):
    _inherit = 'res.company'


    def create_service_company_sequence(self):
        obj = self
        service_sequence = self.env['ir.sequence'].search([('code', '=', 'service.management'), ('company_id', '=', obj.id)])
        if not service_sequence:
            service_sequence = self.env['ir.sequence'].create({
                'name': 'Service Management Sequence - ' + obj.name,
                'code': 'service.management',
                'padding': 3,
                'prefix': 'SERV',
                'company_id': obj.id
            })