from odoo import models,fields,api,_

class AccountMoveInherited(models.Model):
    _inherit = "account.move"

    use_assistro = fields.Boolean(related="company_id.use_assistro",string="Use Assistro",readonly=False)

    def action_open_whatsapp_composer(self):
        """ Opens the WhatsApp message composer wizard. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send WhatsApp Message',
            'res_model': 'whatsapp.composer',
            'view_mode': 'form',
            'view_id': False,
            'target': 'new',
            'context': {
                'default_active_model': self._name,
                'default_active_id': self.id,
                'default_template_id': self.env['assistro.whatsapp.template'].search([('is_default', '=', True)], limit=1).id,
            },
        }
    