from odoo import models, fields, api

class ServiceTemplate(models.Model):
    _name = 'service.template'
    _description = 'Service Template'

    name = fields.Char(string='Service Name', required=True)
    field_ids = fields.One2many('dynamic.fields', 'template_id', string='Custom Fields')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    custom_group_ids = fields.One2many('dynamic.field.group', 'template_id', string='Custom Groups')
    tech_name = fields.Char('Technical Name')
    color = fields.Integer('Color Index', default=1)
    sequence = fields.Integer("Sequence", default=10)
    report_id = fields.Many2one('ir.actions.report',
                                domain=[('report_type', '=', 'docx-pdf'), ('model', '=', 'service.management')],
                                string='Select Report', help='Technical')

    report_docx_template = fields.Binary(
        string="Report docx template",
    )
    action_type = fields.Selection([
        ('quotation', 'Create Quotation'),
        ('invoice', 'Create Invoice')
    ], string='Action Type', default='quotation')

    product_id = fields.Many2one('product.product', string='Default Product')


    @api.model
    def create(self, vals):
        obj = super(ServiceTemplate, self).create(vals)
        if not vals.get('report_id', False):
            report_id = self.env['ir.actions.report'].sudo().create({
                'name': 'Report - ' + str(obj.name),
                'report_type': 'docx-pdf',
                'model': 'service.management',
                'print_report_name': "'Report - %s' % (object.name)",
                'report_docx_template': obj.report_docx_template,
            }).id
            obj.write({'report_id': report_id})
        return obj

    def write(self, vals):
        res = super(ServiceTemplate, self).write(vals)
        for obj in self:
            if vals.get('name'):
                obj.report_id.write({'name': 'Report - ' + str(obj.name)})
            if vals.get('report_docx_template'):
                obj.report_id.write({'report_docx_template': obj.report_docx_template})
        return res

    def unlink(self):
        for obj in self:
            if obj.report_id:
                obj.sudo().report_id.unlink()
        return super(ServiceTemplate, self).unlink()


    def action_view_sf(self):
        service_request_ids = self.env['service.management'].search([('template_id','=',self.id)]).ids
        return {
            'name': 'Service Request',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'service.management',
            'domain': [('id', 'in', service_request_ids)],
        }

    def action_assign_request(self):
        return {
            'name': 'Service Request',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'res_model': 'service.assignment.wizard',
        }

    def action_open_create_dynamic_fields(self):
        create_field_form_id = self.env.ref('all_in_one_dynamic_custom_fields.dynamic_fields_view_form').id

        ctx = {
            'default_model_id': 'service.management',
            'default_template_id': self.id,
        }

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dynamic.fields',
            'view_id': create_field_form_id,
            'target': 'current',
            'context': ctx
        }

    def action_open_create_dynamic_group(self):
        create_field_form_id = self.env.ref('all_in_one_dynamic_custom_fields.view_field_dynamic_group_form').id

        ctx = {
            'default_template_id': self.id
        }

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dynamic.field.group',
            'view_id': create_field_form_id,
            'target': 'current',
            'context': ctx
        }

    # def action_create_sf(self):
    #     return {
    #         'name': 'Service Form',
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'form',
    #         'view_type': 'form',
    #         'res_model': 'service.management',
    #     }
