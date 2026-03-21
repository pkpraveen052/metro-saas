# -*- coding: utf-8 -*-
from odoo import api, models, tools, fields,_

import logging
_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'


    company_apikey = fields.Char(string="API Key", size=16, readonly=True)
    company_apisecret = fields.Char(string="API Secret", size=32, readonly=True)
    corporate_partner_ids = fields.One2many('res.partner', 'officer_id', string='Contact')
    brs_deposit_amount = fields.Float(string="BCRS Deposit Amount", help="Default deposit amount for BCRS.")
    brs_deposit_product_id = fields.Many2one('product.product', string="BCRS Deposit Product", help="Product used for BCRS deposits.")

    @api.model
    def create(self, vals):
        if self.env.user.has_group('metroerp_saas_customization.accounting_partner'):
            obj = super(ResCompany, self.with_env(self.env(su=True))).create(vals)
            template = self.env.ref('metroerp_saas_customization.accounting_partner_new_company')
            if template:
                template.sudo().send_mail(obj.id, force_send=True)
            for usr_obj in self.env.ref('base.group_system').sudo().users:
                usr_obj.sudo().write({'company_ids': [(4, obj.id)]})
            return obj
        else:
            return super(ResCompany, self).create(vals)
