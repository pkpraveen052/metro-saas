from odoo import models,fields,api,_
import logging
_logger = logging.getLogger(__name__)

class Whatsapptemplate(models.Model):
    _name = 'assistro.whatsapp.template'
    _description = 'Assistro Whatsapptemplate'

    name = fields.Char(string="Name")
    model_id = fields.Many2one('ir.model', string='Applies to',help="Select Model For Whatsapptemplate.")
    model = fields.Char(related="model_id.model",string="Model")
    res_model = fields.Char(string="Related Model")
    body = fields.Text(string="Body")
    footer_text = fields.Char(string="Footer Message")
    is_default = fields.Boolean(string="Is Default",default=False)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    available_placeholders = fields.Text(string='Available Placeholders', compute='_compute_available_placeholders')

    def _compute_available_placeholders(self):
        for record in self:
            if not record.model_id:
                record.available_placeholders = "No model selected. Please select a model first."
                continue

            model = self.env['ir.model'].browse(record.model_id.id)
            if not model.model:
                record.available_placeholders = "Invalid model selected. Please check the model."
                continue

            try:
                fields = self.env[model.model].fields_get()
                placeholders = []
                for field_name, field_attrs in fields.items():
                    placeholders.append(f"{{object.{field_name}}}")
                record.available_placeholders = "\n".join(placeholders)
            except KeyError:
                record.available_placeholders = "Error: Invalid model or model not found."


    def action_open_placeholder_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Insert Placeholder',
            'res_model': 'whatsapp.placeholder.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_template_id': self.id,
                'active_model': self._name,  # Pass the model name
                'active_id': self.id,        # Pass the record ID
            },
        }


    @api.onchange('model_id')
    def _onchange_model_id(self):
        """Update the body field when the model_id is selected."""
        # Predefined example templates for different models
        example_templates = {
            "sale.order": (
                "Dear {object.partner_id.name},\n"
                "Your order {object.name} amounting to {object.currency_id.symbol} {object.amount_total} has been confirmed.\n"
                "Thank you for your trust!"
            ),
            "account.move": (
                "Dear {object.partner_id.name},\n"
                "Your invoice {object.name} for {object.currency_id.symbol} {object.amount_total} is ready for payment.\n"
                "Please review the details and make a payment."
            ),
            "stock.picking": (
                "Dear {object.partner_id.name},\n"
                "Your delivery order {object.name} has been confirmed.\n"
                "Please check the details attached."
            ),
            "purchase.order": (
                "Dear {object.partner_id.name},\n"
                "Your purchase order {object.name} with a total amount of {object.currency_id.symbol} {object.amount_total} has been confirmed.\n"
                "Expected delivery date: {object.date_order}\n"
                "Thank you for your business!"
            )
        }

        # Set the corresponding example body when model_id is selected
        if self.model_id:
            model_name = self.model_id.model
            self.res_model = model_name
            # Assign the example template for the selected model
            self.body = example_templates.get(model_name, "Enter your message here.")
        else:
            self.body = "Enter your message here."



    # @api.model
    # def default_get(self, fields):
    #     result = super(Whatsapptemplate, self).default_get(fields)
        
    #     # Get the active model from the context
    #     active_model = self._context.get('active_model')
        
    #     # Set model_id to the active model if it exists
    #     if active_model:
    #         model = self.env['ir.model'].search([('model', '=', active_model)], limit=1)
    #         result['model_id'] = model.id if model else False
        
    #     return result

   
    # @api.model
    # def _create_temp_records(self):
    #     company_ids = self.env['res.company'].sudo().search([]).ids
    #     reports = [{'name':'Sales', 'model_id': 'sale.model_sale_order',
    #                 'models_record': 'sale_order'},
    #                {'name': 'Invoice', 'model_id': 'account.model_account_move',
    #                 'models_record': 'Invoice'},
    #                {'name': 'Purchase Order', 'model_id': 'purchase.model_purchase_order',
    #                 'models_record': 'purchase_order'},
    #                {'name': 'Delivery Note', 'model_id': 'stock.model_stock_picking',
    #                 'models_record': 'delivery'},
    #                ]
    #     for company_id in company_ids:
    #         company_record = self.env['assistro.whatsapp.template'].sudo().search([('company_id', '=', company_id)])
    #         if not company_record:
    #             for report in reports:
    #                 self.env['assistro.whatsapp.template'].create({
    #                     'name': report['name'],
    #                     'model_id': self.env.ref(report['model_id']).id,
    #                     'models_record': report['models_record'],
    #                     'company_id' : company_id,
    #                 })



    