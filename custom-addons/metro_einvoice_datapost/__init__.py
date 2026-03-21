# -*- coding: utf-8 -*-
from . import models
from . import wizard
from . import report

from odoo import api, SUPERUSER_ID


def _pre_init_peppol_id_scheme(cr, registry):
    """ Allow installing MRP in databases with large stock.move table (>1M records)
        - Creating the computed+stored field stock_move.is_done is terribly slow with the ORM and
          leads to "Out of Memory" crashes
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    for partner in env['res.partner'].search([('peppol_scheme','=',False)]):
        vals = {'peppol_scheme': '0195'}
        if partner.l10n_sg_unique_entity_number:
            vals.update({'peppol_identifier': 'SGUEN' + str(partner.l10n_sg_unique_entity_number)})
        partner.write(vals)

    for company in env['res.company'].search([('peppol_scheme','=',False)]):
        company.write({'peppol_scheme': '0195'})
