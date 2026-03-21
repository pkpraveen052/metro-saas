# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def unlink(self):
        """Inherited to pass the context 'partner_company_id' to the base addons unlink() method to by pass the POS Session validation. """
        return super(ResPartner, self.with_context({'partner_company_id': self.company_id and self.company_id.id or False})).unlink()
