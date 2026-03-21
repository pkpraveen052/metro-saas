# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from werkzeug.urls import url_encode


class VendorListPeppol(models.Model):
    _name = 'vendor.list.peppol'
    _description = "Vendor List For Peppol"
    _rec_name = "company_name"

    company_name = fields.Char(string="Company Name", required=True)
    company_uen = fields.Char(string="Company UEN", required=True)
    company_logo = fields.Image("Company Logo", max_width=1920, max_height=1920, store=True)
    contact_person = fields.Char(string="Contact Person")
    contact_email = fields.Char(string="Contact Person Email")
    vendor_business_category = fields.Char(string="Vendor Business Category")
    redirect_url = fields.Char()
    company_id = fields.Many2one("res.company", string="Company Name")
    marketplace_uenNo = fields.Char(string="Market Place uen No")

    def action_purchase_now(self):
        data = {
            'login_user_name': self.env.user.name,
            'login_user_email': self.env.user.email,
            'company_name': self.company_id.name,
            'company_uen': self.company_id.l10n_sg_unique_entity_number,
            'vendor_uen': self.company_uen,
        }
        url = self.redirect_url + '/vendor/products?%s' % url_encode(data),
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': url,
        }

