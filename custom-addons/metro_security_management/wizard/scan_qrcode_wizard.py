# -*- coding: utf-8 -*-
import json
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime
from pytz import timezone, UTC
from odoo.exceptions import ValidationError,UserError
from odoo import api, fields, models, _


class ScanqrcodeWizard(models.TransientModel):
    _name = "scan.qrcode.wizard"
    _description = "Scan qrcode Wizard"

    qrcode = fields.Char('QR code', required=True)
    visitor_id = fields.Many2one('visitor.details', string='Visitor')
    is_valid = fields.Boolean('Is Valid ?')


    # @api.onchange('qrcode')
    # def _onchange_qrcode(self):
    #     if self.qrcode:
    #         try:
    #             # Parse the JSON data from the QR code
    #             qr_data = json.loads(self.qrcode)

    #             # Search for related models
    #             location = self.env['security.location'].search([('location_ref', '=', qr_data.get('location_ref', ''))], limit=1)
    #             visit_type = self.env['visitor.type'].search([('name', '=', qr_data.get('visit_type', ''))], limit=1)
    #             visit_category = self.env['visitor.category'].search([('name', '=', qr_data.get('visit_category', ''))], limit=1)
    #             ic_number = self.env['ic.number'].search([('ic_number', '=', qr_data.get('ic_number', ''))], limit=1)
    #             unit = self.env['block.location'].search([('complete_name', '=', qr_data.get('unit', ''))], limit=1)

    #             # Raise errors for critical missing data
    #             if not location:
    #                 raise UserError("Location with the given reference was not found.")
    #             if qr_data.get('ic_number') and not ic_number:
    #                 raise UserError(f"IC number {qr_data['ic_number']} not found.")

    #             # Extract all fields from the QR data
    #             visitor_vals = {
    #                 'name': qr_data.get('name', ''),
    #                 'phone': qr_data.get('phone', ''),
    #                 'email': qr_data.get('email', ''),
    #                 'check_in_type': qr_data.get('check_in_type', ''),
    #                 'check_in': datetime.strptime(qr_data['check_in'], '%Y-%m-%d %H:%M:%S') if qr_data.get('check_in') else False,
    #                 'vehicle_number': qr_data.get('vehicle_number', ''),
    #                 'visit_type_id': visit_type.id if visit_type else None,
    #                 'visit_category_id': visit_category.id if visit_category else None,
    #                 'ic_number_id': ic_number.id if ic_number else None,  # Handle missing ic_number_id
    #                 'pass_number': qr_data.get('pass_number', ''),
    #                 'location_id': location.id,
    #                 'unit_location_id': unit.id if unit else None,
    #             }

    #             # Create or update visitor.details record
    #             visitor = self.env['visitor.details'].create(visitor_vals)

    #             # Link the created record to the wizard
    #             self.visitor_id = visitor.id

    #         except json.JSONDecodeError:
    #             raise UserError("Invalid QR code data. Please ensure the QR code contains valid JSON.")
    #         except Exception as e:
    #             raise UserError(f"Error processing QR code: {e}")
            

    @api.onchange('qrcode')
    def _onchange_qrcode(self):
        if self.qrcode:
            try:
                # Parse the JSON data from the QR code
                qr_data = json.loads(self.qrcode)
                _logger.info("Parsed QR code data: %s", qr_data)

                # Search for related models
                location = self.env['security.location'].search([('location_ref', '=', qr_data.get('location_ref', ''))], limit=1)
                visit_type = self.env['visitor.type'].search([('name', '=', qr_data.get('visit_type', ''))], limit=1)
                visit_category = self.env['visitor.category'].search([('name', '=', qr_data.get('visit_category', ''))], limit=1)
                ic_number = self.env['ic.number'].search([('ic_number', '=', qr_data.get('ic_number', ''))], limit=1)
                unit = self.env['block.location'].search([('complete_name', '=', qr_data.get('unit', ''))], limit=1)

                # Raise errors for critical missing data
                if not location:
                    raise UserError(_("Location with reference '%s' not found.") % qr_data.get('location_ref', 'N/A'))
                if qr_data.get('ic_number') and not ic_number:
                    raise UserError(_("IC number '%s' not found.") % qr_data['ic_number'])
                if qr_data.get('unit') and not unit:
                    raise UserError(_("Unit '%s' not found.") % qr_data['unit'])

                pre_approved_visitor = self.env['pre.approved.visitor'].search([('id', '=', qr_data['record_id'])], limit=1)

                # Validate and process visitor status
                if pre_approved_visitor:
                    _logger.info("Pre-approved visitor status: %s", pre_approved_visitor.status)

                    if pre_approved_visitor.status == 'used':
                        raise UserError(_("This pre-approved visitor has already been used."))

                    # Update the status to 'used'
                    pre_approved_visitor.write({'status': 'used'})
                    _logger.info("Pre-approved visitor status changed to 'used'.")
                else:
                    raise UserError(_("No matching pre-approved visitor found."))

                # Prepare visitor details
                visitor_vals = {
                    'name': qr_data.get('name', ''),
                    'phone': qr_data.get('phone', ''),
                    'email': qr_data.get('email', ''),
                    'check_in_type': qr_data.get('check_in_type', ''),  # not needed
                    'check_in': fields.Datetime.now(),
                    'vehicle_number': qr_data.get('vehicle_number', ''),  # not needed
                    'visit_type_id': visit_type.id if visit_type else None,
                    'visit_category_id': visit_category.id if visit_category else None,
                    'ic_number_id': ic_number.id if ic_number else None,
                    'pass_number': qr_data.get('pass_number', ''),
                    'location_id': location.id,
                    'unit_location_id': unit.id if unit else None,
                }

                # Check for duplicates
                existing_visitor = self.env['visitor.details'].search([('ic_number_id', '=', ic_number.id)], limit=1)
                if existing_visitor:
                    # Update existing visitor record
                    existing_visitor.write(visitor_vals)
                    self.visitor_id = existing_visitor.id
                    _logger.info("Updated existing visitor record with IC number: %s", ic_number.ic_number)
                else:
                    # Create a new visitor record
                    visitor = self.env['visitor.details'].create(visitor_vals)
                    self.visitor_id = visitor.id
                    _logger.info("Created new visitor record.")

                self.is_valid = True

            except json.JSONDecodeError:
                _logger.error("Invalid QR code data: %s", self.qrcode)
                raise UserError(_("Invalid QR code data. Please ensure the QR code contains valid JSON."))
            except UserError as ue:
                raise ue
            except Exception as e:
                _logger.exception("Unexpected error processing QR code: %s", e)
                raise UserError(_("An unexpected error occurred while processing the QR code. Please try again."))
        


    def save_data(self):
        """Redirect to the created visitor's details form view."""
        if self.visitor_id:
            return {
                "name": _("Visitor"),
                "type": 'ir.actions.act_window',
                "res_model": 'visitor.details',
                "views": [[False, 'form']],
                "res_id": self.visitor_id.id,
                "target": 'current',
            }
        else:
            return {
                'warning': {
                    'title': _('Error!'),
                    'message': _('No visitor record was created.'),
                }
            }