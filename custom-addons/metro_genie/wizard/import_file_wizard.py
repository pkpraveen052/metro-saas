from odoo import models, fields, api

class MetroSampleFileWizard(models.TransientModel):
    _name = 'metro.sample.file.wizard'
    _description = 'Download Sample Files'

    attachment_id = fields.Many2one(
        'ir.attachment',
        string='Sample Files',
        domain=lambda self: [
            ('is_export', '=', True),
            ('group_ids', 'in', self.env.user.groups_id.ids)
        ]
    )

    def action_download_file(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % self.attachment_id.id,
            'target': 'self',
        }

    # @api.model
    # def default_get(self, fields_list):
    #     res = super().default_get(fields_list)
    #
    #     active_model = self.env.context.get('active_model')
    #
    #     domain = [
    #         ('is_export_sample', '=', True),
    #         ('public', '=', True),
    #     ]
    #
    #     if active_model:
    #         domain.append(('res_model', '=', active_model))
    #
    #     attachments = self.env['ir.attachment'].search(domain)
    #
    #     res['attachment_ids'] = [(6, 0, attachments.ids)]
    #     return res
