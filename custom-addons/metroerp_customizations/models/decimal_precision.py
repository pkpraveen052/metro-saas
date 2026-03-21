from odoo import api, fields, models, tools,_
import logging
import sys
_logger = logging.getLogger(__name__)


class DecimalPrecision(models.Model):
    _inherit = 'decimal.precision'

    company_id = fields.Many2one('res.company', string='Company', ondelete='cascade')

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Only one value can be defined for each usage and company!'),
    ]


    @api.model
    @tools.ormcache('application', 'company_id')
    def precision_get(self, application, company_id=None):

        self.flush(['name', 'digits', 'company_id'])
        if not company_id:
            company_id = self.env.company.id

        self.env.cr.execute("""
                SELECT digits
                FROM decimal_precision
                WHERE name = %s AND (company_id IS NULL OR company_id = %s)
                ORDER BY company_id IS NULL, company_id DESC
                LIMIT 1
            """, (application, company_id))

        result = self.env.cr.fetchone()
        self.clear_caches()

        if result:
            return result[0]
        else:
            return 2
        