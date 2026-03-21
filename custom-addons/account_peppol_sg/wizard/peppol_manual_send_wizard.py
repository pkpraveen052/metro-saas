# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError
import logging

logger = logging.getLogger(__name__)


class PeppolManualSendWizard(models.TransientModel):
    _name = 'peppol.manual.send.wizard'
    _description = 'PEPPOL Manual Send Wizard'

    mode = fields.Selection([('test', 'test'), ('live', 'live')], string="Mode")
    message = fields.Text(readonly=True)

    def button_send(self):
        self.ensure_one()
        ctx = self._context
        account_ppool = self.env['account.move']
        documents = account_ppool.browse(ctx['active_ids'])
        Queue = self.env['peppol.queue.out']
        for document in documents:
            document.check_peppol_identifier()
            queue_ref = Queue._add_to_queue(document)
            document.write({'outgoing_inv_doc_ref': queue_ref.id})

        return {
            'name': self.sudo().env.ref('account_peppol_sg.peppol_queue_out_action').name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'peppol.queue.out',
        }


class PeppolWarnigWizard(models.TransientModel):
    _name = 'peppol.warning.wizard'
    _description = 'PEPPOL Warning Wizard'

    message = fields.Text(readonly=True)
