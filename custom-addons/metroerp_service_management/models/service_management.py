from pkg_resources import require

from odoo import models, fields, api

class ServiceManagement(models.Model):
    _name = 'service.management'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Service Management"

    name = fields.Char(string="Service Chit No.", default=lambda self: 'New')
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    template_id = fields.Many2one('service.template', string='Service Template', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assign_request', 'Assign Request'),
        ('in_progress', 'In Progress'),
         ('done', 'Done')
    ], string='Status', readonly=True, required=True, tracking=True, copy=False, default='draft')
    assigned_to = fields.Many2one(comodel_name='res.users', string='Assigned Technician', tracking=True)
    time_arrival = fields.Datetime(string="Time of Arrival", tracking=True)
    time_completed = fields.Datetime(string="Time Completed", tracking=True)
    quotation_id = fields.Many2one('sale.order', string='Quotation')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    action_type = fields.Selection(related='template_id.action_type', readonly=True)

    def create_quotation(self):
        if self.template_id:
            pricelist = self.partner_id.property_product_pricelist or self.env['product.pricelist'].search([], limit=1)

            sale_order = self.env['sale.order'].create({
                'partner_id': self.partner_id.id,
                'pricelist_id': pricelist.id,
                'order_line': [(0, 0, {
                    'product_id': self.template_id.product_id.id,
                    'product_uom_qty': 1,  # Set the quantity as needed
                })],
                'service_id': self.id,
            })
            self.quotation_id = sale_order.id
            return {
                'type': 'ir.actions.act_window',
                'name': 'Quotation',
                'view_mode': 'form',
                'res_model': 'sale.order',
                'res_id': sale_order.id,
                'target': 'current',
            }

    def create_invoice(self):
        if self.template_id:
            invoice = self.env['account.move'].create({
                'partner_id': self.partner_id.id,
                'move_type': 'out_invoice',
                'invoice_line_ids': [(0, 0, {
                    'product_id': self.template_id.product_id.id,
                    'quantity': 1,  # Set the quantity as needed
                })],
                'service_id': self.id,
            })
            self.invoice_id = invoice.id
            return {
                'type': 'ir.actions.act_window',
                'name': 'Invoice',
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': invoice.id,
                'target': 'current',
            }


    def action_print_report(self):
        print("\n\n\n",self)
        print(self._context)
        ctx = self._context or {}
        ctx = dict(ctx)
        if 'params' in ctx:
            ctx.pop('params')
        if 'active_model' in ctx:
            ctx.pop('active_model')
        if 'active_id' in ctx:
            ctx.pop('active_id')
        if 'active_ids' in ctx:
            ctx.pop('active_ids')
        print(ctx)
        return self.with_context(ctx).template_id.report_id.report_action(self)


    def action_open_create_dynamic_fields(self):
        create_field_form_id = self.env.ref('all_in_one_dynamic_custom_fields.dynamic_fields_view_form').id

        ctx = {
            'default_model': 'service.management'
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

    def assign_request_to_technician(self):
        if self.name == 'New':
            record_name = self.env['ir.sequence'].next_by_code('service.management') or 'New'
            self.write({'name':record_name})
        self.state = 'assign_request'


    # def request_done(self):
    #     self.state = 'done'

    def action_open_sale_order(self):
        """Opens the Sale Order form view with the current partner as default."""
        self.ensure_one()  # Ensure the method is called on a single record
        # Search for an existing sale order for this partner
        existing_sale_order = self.env['sale.order'].search([
            ('partner_id', '=', self.partner_id.id),
            ('state', 'in', ['draft', 'sent'])  # Adjust the states as needed
        ], limit=1)
        if existing_sale_order:
            # If an existing sale order is found, open it in form view
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sale Order',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': existing_sale_order.id,
                'target': 'current',
            }
        else:
            # If no existing sale order is found, open a new sale order form
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sale Order',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_partner_id': self.partner_id.id,  # Pre-fill the current partner as the customer
                },
            }

    def action_share_to_customer(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'portal.share',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'service.management',
                'is_customer': True
            },
        }

    def action_share_to_technician(self):
        partner_ids = self.assigned_to.partner_id.ids if self.assigned_to else False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'portal.share',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'service.management',
                'partner_ids': partner_ids,
                'is_tech': True
            },
        }

    def action_start(self):
        self.write({
            'state': 'in_progress',
            'time_arrival': fields.Datetime.now(),
        })

    def request_done(self):
        self.write({
            'state': 'done',
            'time_completed': fields.Datetime.now(),
        })

    def preview_service_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }

    def _compute_access_url(self):
        super(ServiceManagement, self)._compute_access_url()
        for service in self:
            service.access_url = '/my/service_management/%s' % (service.id)

    def action_send_by_mail(self):
        self.ensure_one()
        lang = self.env.context.get('lang')
        templates = self.env.ref(
            'metroerp_service_management.mail_template_service_send_by_mail'
        )

        if templates.lang:
            lang = templates._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'service.management',
            'default_res_id': self.ids[0],
            'default_use_template': bool(templates),
            'default_template_id': templates.id,
            'default_composition_mode': 'comment',
            'force_email': True,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }


class PortalShare(models.TransientModel):
    _inherit = 'portal.share'

    @api.model
    def default_get(self, fields):
        result = super(PortalShare, self).default_get(fields)
        result['res_model'] = self._context.get('active_model', False)
        result['res_id'] = self._context.get('active_id', False)
        if result['res_model'] and result['res_id']:
            record = self.env[result['res_model']].browse(result['res_id'])
            result['partner_ids'] = self._context.get('partner_ids', False) if result['res_model'] == 'service.management' and self._context.get('is_tech', False) else record.partner_id
        return result

    def action_send_mail(self):
        if self._context.get('is_tech', False):
            res_model = self._context.get('active_model', False)
            res_id = self._context.get('active_id', False)
            if res_model == 'service.management' and res_id:
                record = self.env[res_model].browse(res_id)
                if record.name == 'New':
                    record_name = self.env['ir.sequence'].next_by_code('service.management') or 'New'
                    record.write({'name': record_name})
                record.state = 'assign_request'
        return super(PortalShare, self).action_send_mail()

    def action_send_whatsapp(self):
        if self._context.get('is_tech', False):
            res_model = self._context.get('active_model', False)
            res_id = self._context.get('active_id', False)
            if res_model == 'service.management' and res_id:
                record = self.env[res_model].browse(res_id)
                record.state = 'assign_request'
        return super(PortalShare, self).action_send_whatsapp()