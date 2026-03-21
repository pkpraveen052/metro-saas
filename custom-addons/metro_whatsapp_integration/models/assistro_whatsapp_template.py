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
            "progressive.billing.qt": (
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
            ),
            "account.payment": (
            "Dear {object.partner_id.name},\n"
            "Thank you for your payment of {object.currency_id.symbol} {object.amount} to {object.company_id.name}.\n"
            "Do not hesitate to contact us if you have any questions."
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


    @api.model
    def _create_temp_records(self):
        """Creates WhatsApp templates for all companies if not already present."""
        company_ids = self.env['res.company'].sudo().search([])

        templates = [
            {
                'name': 'Default Sales Template',
                'model_id': 'sale.model_sale_order',
                'body': "Dear {object.partner_id.name}, Your order {object.name} amounting in {object.currency_id.symbol} {object.amount_total} has been confirmed. Thank you for your trust!"
            },
            {
                'name': 'Default Progressive Billing Sales Template',
                'model_id': 'metroerp_progressive_billing.model_progressive_billing_qt',
                'body': "Dear {object.partner_id.name}, Your order {object.name} amounting in {object.currency_id.symbol} {object.amount_total} has been confirmed. Thank you for your trust!"
            },
            {
                'name': 'Default Invoice Template',
                'model_id': 'account.model_account_move',
                'body': "Dear {object.partner_id.name}, Here is your invoice {object.name} amounting in {object.currency_id.symbol} {object.amount_total} from {object.company_id.name}. Please remit payment at your earliest convenience."
            },
            {
                'name': 'Default Purchase Order Template',
                'model_id': 'purchase.model_purchase_order',
                'body': "Dear {object.partner_id.name}, Here is in attachment a purchase order {object.name} amounting in {object.currency_id.symbol} {object.amount_total} from {object.company_id.name}. The receipt is expected for {object.date_planned}. Could you please acknowledge the receipt of this order?"
            },
            {
                'name': 'Default Delivery Note Template',
                'model_id': 'stock.model_stock_picking',
                'body': "Dear {object.partner_id.name}, We are glad to inform you that your delivery order {object.name} has been confirmed. Please find your delivery order attached for more details. Thank you, {object.company_id.name}."
            },
            {
                'name': 'Default Payment Receipts Template',
                'model_id': 'account.model_account_payment',
                'body': "Dear {object.partner_id.name}, Thank you for your payment of {object.currency_id.symbol} {object.amount} to {object.company_id.name}. Do not hesitate to contact us if you have any questions."
            },
        ]

        for company in company_ids:
            # Fetch existing template names for this company
            existing_templates = self.sudo().search([('company_id', '=', company.id)]).mapped('name')

            for template in templates:
                if template['name'] not in existing_templates:
                    model_ref = self.env.ref(template['model_id'], raise_if_not_found=False)

                    if model_ref:
                        self.sudo().create({
                            'name': template['name'],
                            'model_id': model_ref.id,
                            'company_id': company.id,
                            'body': template['body'],
                            'is_default': True
                        })
                    else:
                        print(f"❌ Model not found: {template['model_id']} (Skipping)")



   