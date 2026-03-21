from odoo import models,fields,api,_
from odoo.exceptions import ValidationError
import base64
from werkzeug.exceptions import HTTPException

import logging
_logger = logging.getLogger(__name__)


class SecurityResponses(models.Model):
    _name = "security.responses"
    _inherit = ['mail.activity.mixin','mail.thread','portal.mixin']
    _description = "Security Responses"
    
    name = fields.Char(string="Reporter Name")
    location_id = fields.Many2one(related="check_point_id.location_id",store=True,string="Location",tracking=True)
    check_point_id = fields.Many2one("security.contract.checkpoint",string="Checkpoint",tracking=True,required=True)
    contract_id = fields.Many2one(related="location_id.contract_id",store=True,string="Contract",tracking=True)
    device_id = fields.Char(related="check_point_id.device_id",store=True,string="Device ID",tracking=True)
    timestamp = fields.Datetime(string="Timestamp",required=True,tracking=True)
    image_attachment_ids = fields.Many2many("ir.attachment", 'product_variant_attachments_rel', 'product_id', 'attach_id', string="Upload")
    remarks = fields.Text(string="Remarks")
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)
    image = fields.Binary(string="Image")

    

    @api.model
    def create(self, vals):
        # Perform validations only if location_ref is provided (assumed API request)
        if 'location_ref' in vals:
            device_id = vals.get('device_id')
            location_ref = vals.get('location_ref')
            
            location = self.env['security.location'].search([('location_ref', '=', location_ref)], limit=1)
            if not location:
                raise ValidationError(_("Invalid location reference. Please provide a correct location reference."))
            
            if not device_id:
                raise ValidationError(_("Device ID is required to proceed."))
            
            checkpoint = self.env['security.contract.checkpoint'].search([
                ('location_id', '=', location.id),
                ('device_id', '=', device_id)
            ], limit=1)
            
            if not checkpoint:
                raise ValidationError(_("No checkpoint found for the specified location and device ID. Please ensure both are correct."))
            
            # Set related fields in vals based on found location and checkpoint
            vals['location_id'] = location.id
            vals['check_point_id'] = checkpoint.id
            vals['contract_id'] = location.contract_id.id

            # Remove location_ref from vals before creating the record
            vals.pop('location_ref', None)
        
        # Create the record
        response = super(SecurityResponses, self).create(vals)
        return response
