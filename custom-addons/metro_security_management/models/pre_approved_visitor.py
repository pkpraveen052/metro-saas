import json
import logging
_logger = logging.getLogger(__name__)
from odoo import models,fields,api,_
from odoo.exceptions import UserError
from pytz import timezone, UTC

try:
   import qrcode
except ImportError:
   qrcode = None
try:
   import base64
except ImportError:
   base64 = None
from io import BytesIO

class PreApprovedVisitor(models.Model):
    _name = "pre.approved.visitor"
    _inherit = ['mail.activity.mixin','mail.thread','portal.mixin']
    _description = "Pre-Approved Visitor"

    visitor_code = fields.Char('Visitor Code',default="New",readonly=True, copy=False)
    location_id = fields.Many2one("security.location",string="Location",required=True,tracking=True)
    name = fields.Char(string="Name",related="ic_number_id.name",tracking=True,readonly=False,store=True)
    phone = fields.Char(string="Phone",related="ic_number_id.phone",tracking=True,readonly=False,store=True)
    email = fields.Char(string="Email",related="ic_number_id.email",tracking=True,readonly=False,store=True)
    check_in_type = fields.Selection([('walk_in','WALK-IN'),('vehicle','VEHICLE')],default="walk_in",string="Check In Type",tracking=True)
    check_in = fields.Datetime(string="Check In",required=True,tracking=True)
    visit_type_id = fields.Many2one("visitor.type",string="Visit Type",tracking=True)
    visit_category_id = fields.Many2one("visitor.category",string="Visit Category",tracking=True)
    pass_number = fields.Char(string="Pass Number",tracking=True)
    unit_location_id = fields.Many2one("block.location",string="Unit",tracking=True)
    owner = fields.Char(related="unit_location_id.owner",string="Owner",store=True,tracking=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    vehicle_number = fields.Char(related="visitor_vehicle_id.vehicle_number",string="Vehicle Number",readonly=False,require=True,tracking=True,store=True)
    visitor_company_id = fields.Many2one("visitor.company",string="Company")
    visitor_vehicle_id = fields.Many2one("visitor.vehicle",string="Vehicle")
    ic_number_id = fields.Many2one("ic.number",required=True,tracking=True)
    partner_id = fields.Many2one("res.partner",string="Partner",domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    status = fields.Selection([
        ('new', 'New'),
        ('used', 'Used')
    ], default='new')
    user_id = fields.Many2one("res.users",string="User",default=lambda self: self.env.user.id)

    qr_code = fields.Binary('QR code',compute="_generate_qr",store=True)

    @api.model
    def create(self, vals):
        if vals.get('visitor_code', 'New') == 'New':
            vals['visitor_code'] = self.env['ir.sequence'].sudo().next_by_code('pre.approved.visitor') or 'New'
        res = super(PreApprovedVisitor, self).create(vals)
        res._generate_qr()
        res.send_qr_email()
        return res
    
   

    def _generate_qr(self):
        for rec in self:
            if qrcode and base64:
                try:
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=3,
                        border=4,
                    )
                    # Collect necessary data for the QR code
                    qr_data = {
                        "record_id": rec.id,
                        "location_ref": rec.location_id.location_ref if rec.location_id else "",
                        "name": rec.name,
                        "phone": rec.phone,
                        "email": rec.email,
                        "visit_type": rec.visit_type_id.name if rec.visit_type_id else "",
                        "visit_category": rec.visit_category_id.name if rec.visit_category_id else "",
                        "ic_number": rec.ic_number_id.ic_number if rec.ic_number_id else "",
                        "pass_number": rec.pass_number,
                        "unit": rec.unit_location_id.complete_name if rec.unit_location_id else "",
                    }
                    # Serialize data to JSON and add to the QR code
                    qr.add_data(json.dumps(qr_data))
                    qr.make(fit=True)

                    # Generate the QR code image and store it as binary
                    img = qr.make_image()
                    temp = BytesIO()
                    img.save(temp, format="PNG")
                    qr_image = base64.b64encode(temp.getvalue())  # Store as base64 binary data

                    # Update the record with the QR code binary
                    rec.update({'qr_code': qr_image})

                except Exception as e:
                    _logger.error(f"Error generating QR code for record {rec.id}: {e}")
                    raise UserError(_("An error occurred while generating the QR code. Please try again."))
                


    def send_qr_email(self):
        if self.email:
            template = self.env.ref('metro_security_management.qr_code_email_template')
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)


    qr_code_url = fields.Char('QR Code URL', compute="_compute_qr_code_url")

    def _compute_qr_code_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            rec.qr_code_url = f"{base_url}/web/image/pre.approved.visitor/{rec.id}/qr_code"
        
    