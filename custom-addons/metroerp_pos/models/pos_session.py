# -*- coding: utf-8 -*-
from odoo import fields, models, api

class PosSession(models.Model):
    _inherit = 'pos.session'

    _sql_constraints = [('uniq_name', 'unique(name,company_id)', "The name of this POS Session must be unique !")]

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """This method appends the args [()] when a context {'partner_company_id'} is received. """
        ctx = self._context

        if ctx.get('partner_company_id'):
            args.append(('company_id','=',ctx.get('partner_company_id')))
        res = super(PosSession, self).search(args, offset=offset, limit=limit, order=order, count=count)
        return res

