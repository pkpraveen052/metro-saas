from odoo import models, fields, api
from odoo.exceptions import UserError


class VendorNotFoundWizard(models.TransientModel):
    _name = 'vendor.not.found.wizard'
    _description = 'Vendor Not Found Wizard'

    ocr_vendor_name = fields.Char('Vendor Name', readonly=True)
    option = fields.Selection([
        ('create', 'Create a new vendor'),
        ('select', 'Select from existing vendors'),
    ], string='Action', required=True, default='create')
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )
    selected_vendor_id = fields.Many2one('res.partner', string="Select Vendor", domain="[('supplier_rank', '>', 0), ('company_id', '=', company_id)]")
    invoice_file = fields.Binary('Vendor Bill File')
    filename = fields.Char('Filename')

    @api.onchange('option')
    def _onchange_option(self):
        if self.option != 'select':
            self.selected_vendor_id = False

    def action_continue(self):
        context = dict(self._context or {})
        data = context.get('data')
        ocr_vendor_name = self.ocr_vendor_name
        invoice_file = context.get('invoice_file')
        filename = context.get('filename')
        country_id = False
        if self.option == 'create':
            partner_vals_dict = {'name':ocr_vendor_name, 'supplier_rank': 1, 'company_id': self.company_id.id}
            if context.get('vendor_registration_number', False):
                partner_vals_dict['l10n_sg_unique_entity_number'] = context.get('vendor_registration_number', False)
            if context.get('street', False):
                partner_vals_dict['street'] = context.get('street', False)
            if context.get('street2', False):
                partner_vals_dict['street2'] = context.get('street2', False)
            if context.get('city', False):
                partner_vals_dict['city'] = context.get('city', False)
            if context.get('zip_code', False):
                partner_vals_dict['zip'] = context.get('zip_code', False)
            if context.get('country', False):
                country_id = self.env['res.country'].search([('name', '=', context.get('country', False))], limit=1).id

                partner_vals_dict['country_id'] = country_id
            if context.get('mobile', False):
                partner_vals_dict['mobile'] = context.get('mobile', False)
            if context.get('phone', False):
                partner_vals_dict['phone'] = context.get('phone', False)
            if context.get('vendor_email', False):
                partner_vals_dict['email'] = context.get('vendor_email', False)
            if not country_id:
                country_id = self.env['res.country'].search([('name', '=', "Singapore")], limit=1).id
                partner_vals_dict['country_id'] = country_id

            partner_id = self.env['res.partner'].create(partner_vals_dict)
            # Redirect to partner creation with prefilled name
            result = self.env['invoice.upload.wizard'].with_context(
                selected_vendor_id=partner_id.name,
                ocr_data=data,
                invoice_file=invoice_file,
                filename=filename
            ).action_create_vendor_bill()


            if isinstance(result, int):
                # This is invoice ID
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'res_id': result,
                    'view_mode': 'form',
                    'target': 'current',
                }

            elif isinstance(result, str):
                # This is a warning string (like tax missing or mismatch total)
                raise UserError(result)

            elif isinstance(result, dict) and result.get('res_model') == 'account.move':
                return result

        if self.option == 'select':
            result = self.env['invoice.upload.wizard'].with_context(
                selected_vendor_id=self.selected_vendor_id.name,
                ocr_data=data,
                invoice_file = invoice_file,
                filename = filename
            ).action_create_vendor_bill()
            if isinstance(result, int):
                # This is invoice ID
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'res_id': result,
                    'view_mode': 'form',
                    'target': 'current',
                }

            elif isinstance(result, str):
                # This is a warning string (like tax missing or mismatch total)
                raise UserError(result)

            elif isinstance(result, dict) and result.get('type') == 'ir.actions.act_window':
                # Return action to show mismatch wizard or invoice form
                return result

