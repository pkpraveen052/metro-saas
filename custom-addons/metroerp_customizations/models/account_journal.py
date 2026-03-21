# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # Overidden Method
    def _default_invoice_reference_model(self):
        """Get the invoice reference model according to the company's country."""
        country_code = self.env.company.country_id.code
        country_code = country_code and country_code.lower()
        if country_code:
            for model in self._fields['invoice_reference_model'].get_values(self.env):
                if model.startswith(country_code):
                    return model
        return 'odoo'
        
    invoice_reference_model = fields.Selection(string='Communication Standard', required=True, selection=[('odoo', 'ERP'),('euro', 'European')], default=_default_invoice_reference_model, help="You can choose different models for each type of reference. The default one is the ERP reference.")

