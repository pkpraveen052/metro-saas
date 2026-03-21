# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountInvoiceSend(models.TransientModel):
    _inherit = 'account.invoice.send'
    _description = 'Account Invoice Send'

    @api.model
    def default_get(self, fields):
        """
        This method default set mass email template id in wizard.
        """
        res = super(AccountInvoiceSend, self).default_get(fields)
        if len(res.get('invoice_ids')) > 1 and self._context.get('active_model') == 'account.move':
            template = self.env.ref('metroerp_customizations.mass_email_template_edi_invoice', raise_if_not_found=False)
            res.update({'template_id': template.id})
        return res
