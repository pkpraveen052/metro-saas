from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    company_id = fields.Many2one('res.company', string='Company', required=True)

    @api.model
    def default_get(self, fields):
        rec = super(AccountPaymentTerm, self).default_get(fields)
        rec['company_id'] = self.env.company.id
        return rec
    
  
