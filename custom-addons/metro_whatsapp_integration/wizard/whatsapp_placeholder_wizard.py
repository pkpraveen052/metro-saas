from odoo import models, fields, api

class WhatsappPlaceholderWizard(models.TransientModel):
    _name = 'whatsapp.placeholder.wizard'
    _description = 'WhatsApp Placeholder Wizard'

    placeholder = fields.Selection(
        string="Placeholder",
        selection="_get_placeholders",
        help="Select a placeholder to insert into the template."
    )
    template_id = fields.Many2one('assistro.whatsapp.template', string="Template")

    @api.model
    def _get_placeholders(self):
        """Retrieve model fields for dynamic placeholder selection."""
        template = self.env['assistro.whatsapp.template'].browse(self._context.get('active_id'))

        if not template.model_id:
            return [("", "No model is set for this template. Please select a model first.")]

        model = self.env[template.model_id.model]
        fields_info = model.fields_get()

        placeholders = []
        for field_name, field_attrs in fields_info.items():
            field_label = field_attrs.get('string', field_name)

            field_type = field_attrs.get('type')

            if field_type == 'many2one':
                # Many2one fields should show the related record's name
                placeholders.append((f"{{object.{field_name}.name}}", f"{field_label} (Name)"))

            else:
                # Standard fields
                placeholders.append((f"{{object.{field_name}}}", field_label))

        return placeholders

    def action_insert_placeholder(self):
        """Insert the selected placeholder into the template body and replace ID fields with names."""
        self.ensure_one()
        template = self.template_id

        if template and self.placeholder:
            # Ensure 'body' is a string before appending
            template.body = (template.body or "") + f" {self.placeholder}"
        