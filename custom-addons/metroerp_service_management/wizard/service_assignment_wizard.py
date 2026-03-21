from odoo import models, fields, api

class ServiceAssignmentWizard(models.TransientModel):
    _name = 'service.assignment.wizard'
    _description = 'Service Assignment Wizard'

    service_template_id = fields.Many2one('service.template', string='Service Template', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    number_of_services = fields.Integer(string='Number of Services', required=True, default=1)

    @api.model
    def default_get(self, fields):
        res = super(ServiceAssignmentWizard, self).default_get(fields)
        if self.env.context.get('active_id'):
            service_template = self.env['service.template'].browse(self.env.context.get('active_id'))
            res['service_template_id'] = service_template.id
        return res

    def action_assign_services(self):
        # Create the specified number of service records for the selected customer and template
        service_obj = self.env['service.management']
        for _ in range(self.number_of_services):
            service_obj.create({
                'template_id': self.service_template_id.id,
                'partner_id': self.partner_id.id,
            })
        return {'type': 'ir.actions.act_window_close'}