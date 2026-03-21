from odoo import models, fields

class MismatchWarningWizard(models.TransientModel):
    _name = 'mismatch.warning.wizard'
    _description = 'Invoice Mismatch Warning'

    message = fields.Text(readonly=True)
    invoice_id = fields.Many2one('account.move', string="Created Invoice", readonly=True)

    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}