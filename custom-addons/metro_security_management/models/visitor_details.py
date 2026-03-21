from odoo import models,fields,api,_
from datetime import datetime
from odoo.exceptions import UserError,ValidationError

class VisitorDetails(models.Model):
    _name = "visitor.details"
    _inherit = ['mail.activity.mixin','mail.thread','portal.mixin']
    _description = "Visitor Details"
    _order = "id desc"
    _rec_name = "visitor_ref"
    
    visitor_ref = fields.Char(string="Visitor Reference",required=True, readonly=True,default="New",copy=False)
    location_id = fields.Many2one("security.location",string="Location",required=True,tracking=True)
    contact_company_id = fields.Many2one("res.partner",string="Company Name",tracking=True,domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    name = fields.Char(string="Name",related="ic_number_id.name",tracking=True,readonly=False,store=True)
    phone = fields.Char(string="Phone",related="ic_number_id.phone",tracking=True,readonly=False,store=True)
    email = fields.Char(string="Email",related="ic_number_id.email",tracking=True,readonly=False,store=True)
    check_in_type = fields.Selection([('walk_in','WALK-IN'),('vehicle','VEHICLE')],default="walk_in",string="Check In Type",tracking=True)
    check_in = fields.Datetime(string="Check In",required=True,tracking=True)
    check_out = fields.Datetime(string="Check Out",tracking=True)
    duration = fields.Char(string="Duration", compute='_compute_duration',store=True)
    visit_type_id = fields.Many2one("visitor.type",string="Visit Type",tracking=True)
    visit_category_id = fields.Many2one("visitor.category",string="Visit Category",tracking=True)
    visitor_purpose = fields.Text(string="Visitor Perpose",tracking=True)
    contractor_pass  = fields.Char(string="Contractor Pass",tracking=True)
    pass_number = fields.Char(string="Pass Number",tracking=True)
    unit_location_id = fields.Many2one("block.location",string="Unit",tracking=True)
    visitor_feed_back = fields.Text(string="Visitor Feedback",tracking=True)
    priority = fields.Selection([('0', 'Normal'),
                                 ('1', 'Low'),
                                 ('2', 'High'),
                                 ('3', 'Very High')], string="Priority")

   
    owner = fields.Char(related="unit_location_id.owner",string="Owner",store=True,tracking=True)
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)
    image_1920 = fields.Image(related='ic_number_id.image_1920',string="Image",store=True,readonly=False)
    active = fields.Boolean(string="Active",default=True)
    vehicle_number = fields.Char(related="visitor_vehicle_id.vehicle_number",string="Vehicle Number",readonly=False,require=True,tracking=True,store=True)
    visitor_company_id = fields.Many2one("visitor.company",string="Company")
    visitor_vehicle_id = fields.Many2one("visitor.vehicle",string="Vehicle")
    ic_number_id = fields.Many2one("ic.number",required=True,tracking=True)
    partner_id = fields.Many2one("res.partner",string="Partner",domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    vehicle_image = fields.Binary(related='visitor_vehicle_id.vehicle_image',string="Vehicle Image",store=True,readonly=False)

    @api.model
    def _visitor_default_note(self):
        return self.env.company.use_visitor_tc and self.env.company.visitor_tc or ''
    
    note = fields.Text('Terms and conditions', default=_visitor_default_note)


    @api.depends('check_in','check_out')
    def _compute_duration(self):
        for record in self:
            if record.check_in and record.check_out:
                duration = record.check_out - record.check_in
                days, seconds = duration.days, duration.seconds
                hours = days * 24 + seconds // 3600
                minutes = (seconds % 3600) // 60
                record.duration = f"{hours} hours, {minutes} minutes"
            else:
                record.duration = 'N/A'


    def action_set_check_out(self):
        for record in self:
            record.check_out = datetime.now()


    # @api.onchange('ic_number_id')
    # def _onchange_ic_number(self):
    #     if self.ic_number_id:
    #         # Search for the ic_number in the ic.number model
    #         visitor = self.env['ic.number'].search(
    #             [('ic_number_id', '=', self.ic_number)], order='create_date desc', limit=1
    #         )
    #         if visitor:
    #             # If found, populate the visitor's details
    #             self.name = visitor.name
    #             self.phone = visitor.phone
    #             self.email = visitor.email

    #         else:
    #             # Clear the fields so the user can input details manually
    #             self.name = False
    #             self.phone = False
    #             self.email = False


    @api.model
    def create(self, vals):
        # Check if visitor details match any blocked entry
        self._check_blocked_visitor(vals)
        
        # Generate sequence if needed
        if vals.get('visitor_ref', _('New')) == _('New'):
            vals['visitor_ref'] = self.env['ir.sequence'].sudo().next_by_code('visitor.details') or _('New')
        
        # Create the visitor record
        res = super(VisitorDetails, self).create(vals)
        
        # Sync data with ic.number model, including is_blocked field
        ic_number_record = self.env['ic.number'].search([('id', '=', res.ic_number_id.id)], limit=1)
        
        if ic_number_record:
            # Update the existing ic.number record with visitor details
            ic_number_record.write({
                'name': res.name,
                'phone': res.phone,
                'email': res.email,
            })
        else:
            # Create a new ic.number record if none exists
            self.env['ic.number'].create({
                'ic_number': res.ic_number_id.id,
                'name': res.name,
                'phone': res.phone,
                'email': res.email,
            })
        
        return res


    def write(self, vals):
        # Run block validation if necessary fields are being updated
        if any(field in vals for field in ['ic_number_id', 'visitor_vehicle_id', 'visitor_company_id']):
            self._check_blocked_visitor(vals)
        
        # Proceed with the write operation if no validation errors
        res = super(VisitorDetails, self).write(vals)
        
        # Update related ic.number records after the main write operation
        for record in self:
            if record.ic_number_id:
                # Find or create the related ic.number record
                ic_number_record = self.env['ic.number'].search([('id', '=', record.ic_number_id.id)], limit=1)
                
                if ic_number_record:
                    # Update the existing ic.number record with relevant fields
                    ic_number_record.write({
                        'name': vals.get('name', record.name),
                        'phone': vals.get('phone', record.phone),
                        'email': vals.get('email', record.email),
                    })
                else:
                    # Create a new ic.number record if none exists
                    self.env['ic.number'].create({
                        'ic_number': record.ic_number_id.id,
                        'name': record.name,
                        'phone': record.phone,
                        'email': record.email,
                    })
        
        return res

    # def _check_if_visitor_blocked(self, vals):
    #     """
    #     Check if the visitor's IC number, vehicle number, or company is blocked.
    #     """
    #     # Check if IC number is provided and blocked
    #     if vals.get('ic_number'):
    #         ic_blocked = self.env['ic.number'].search([
    #             ('ic_number', '=', vals['ic_number']),
    #             ('is_blocked', '=', True)
    #         ], limit=1)
    #         if ic_blocked:
    #             raise ValidationError(_("This visitor is blocked by IC Number: %s") % vals['ic_number'])
        
    #     # Check if vehicle number is provided and blocked
    #     if vals.get('vehicle_number'):
    #         vehicle_blocked = self.env['ic.number'].search([
    #             ('vehicle_number', '=', vals['vehicle_number']),
    #             ('is_blocked', '=', True)
    #         ], limit=1)
    #         if vehicle_blocked:
    #             raise ValidationError(_("This visitor is blocked by Vehicle Number: %s") % vals['vehicle_number'])
        
    #     # Check if company is provided and blocked
    #     if vals.get('visitor_company_id'):
    #         company_blocked = self.env['ic.number'].search([
    #             ('visitor_company_id', '=', vals['visitor_company_id']),
    #             ('is_blocked', '=', True)
    #         ], limit=1)
    #         if company_blocked:
    #             raise ValidationError(_("This visitor is blocked by Company: %s") % vals['visitor_company_id'])

    def _check_blocked_visitor(self, vals):
        """
        Validates if the visitor matches any record in the block list based on
        location and block reason.
        """
        # Get the location and visitor details from vals or current record
        location_id = vals.get('location_id', self.location_id.id)
        ic_number_id = vals.get('ic_number_id', self.ic_number_id.id)
        vehicle_id = vals.get('visitor_vehicle_id', self.visitor_vehicle_id.id)
        company_id = vals.get('visitor_company_id', self.visitor_company_id.id)

        # Define the domain to search in block.list
        domain = [('location_id', '=', location_id), ('is_blocked', '=', True)]

        # Add conditions based on block_reason field
        domain_ic_number = domain + [('block_reason', '=', 'ic_number'), ('visitor_ic_num_id', '=', ic_number_id)]
        domain_vehicle = domain + [('block_reason', '=', 'vehicle'), ('visitor_vehicle_id', '=', vehicle_id)]
        domain_company = domain + [('block_reason', '=', 'company'), ('visitor_company_id', '=', company_id)]

        # Search in block.list for any matches
        blocked_ic_number = self.env['block.list'].search(domain_ic_number, limit=1)
        blocked_vehicle = self.env['block.list'].search(domain_vehicle, limit=1)
        blocked_company = self.env['block.list'].search(domain_company, limit=1)

        # Raise validation error if any blocked match is found
        if blocked_ic_number or blocked_vehicle or blocked_company:
            raise ValidationError(
                "Access Denied: This visitor matches a blocked entry based on location and selected details."
            )

    # def _check_if_visitor_blocked(self, vals):
    #     """
    #     Check if the visitor's IC number, vehicle ID, or company is blocked.
    #     """
    #     # Check if IC number is provided and blocked
    #     if vals.get('ic_number'):
    #         ic_blocked = self.env['ic.number'].search([
    #             ('ic_number', '=', vals['ic_number']),
    #             ('is_blocked', '=', True)
    #         ], limit=1)
    #         if ic_blocked:
    #             raise ValidationError(_("This visitor is blocked by IC Number: %s") % vals['ic_number'])
        
    #     # Check if visitor vehicle is provided and blocked
    #     if vals.get('visitor_vehicle_id'):
    #         vehicle_blocked = self.env['ic.number'].search([
    #             ('visitor_vehicle_id', 'in', [vals['visitor_vehicle_id']]),
    #             ('is_blocked', '=', True)
    #         ], limit=1)
    #         if vehicle_blocked:
    #             vehicle_number = vehicle_blocked.visitor_vehicle_id[0].vehicle_number  # Retrieve the first matched vehicle number
    #             raise ValidationError(_("This visitor is blocked by Vehicle Number: %s") % vehicle_number)
        
    #     # Check if company is provided and blocked
    #     if vals.get('visitor_company_id'):
    #         company_blocked = self.env['ic.number'].search([
    #             ('visitor_company_id', 'in', [vals['visitor_company_id']]),
    #             ('is_blocked', '=', True)
    #         ], limit=1)
    #         if company_blocked:
    #             company_name = company_blocked.visitor_company_id[0].name  # Retrieve the first matched company name
    #             raise ValidationError(_("This visitor is blocked by Company: %s") % company_name)
            

    @api.constrains('check_in','check_out')
    def _check_dates(self):
        for record in self:
            if record.check_in and record.check_out and record.check_in > record.check_out:
                raise ValidationError("Check In Date cannot be earlier than Check Out Date.")
            
    

    # @api.model
    # def process_scanned_data(self, qr_data):
    #     """Method to process scanned QR data and create visitor details."""
    #     # Parse the QR data
    #     visitor_data = eval(qr_data)  # Use safer JSON parsing in production
    #     visitor_vals = {
    #         "visitor_code": visitor_data.get("visitor_code"),
    #         "location_id": self.env['security.location'].search([('location_ref', '=', visitor_data.get("location_ref"))], limit=1).id,
    #         "name": visitor_data.get("name"),
    #         "phone": visitor_data.get("phone"),
    #         "email": visitor_data.get("email"),
    #         "check_in_type": visitor_data.get("check_in_type"),
    #         "check_in": visitor_data.get("check_in"),
    #         "vehicle_number": visitor_data.get("vehicle_number"),
    #         "visit_type_id": self.env['visitor.type'].search([('name', '=', visitor_data.get("visit_type"))], limit=1).id,
    #         "visit_category_id": self.env['visitor.category'].search([('name', '=', visitor_data.get("visit_category"))], limit=1).id,
    #         "pass_number": visitor_data.get("pass_number"),
    #     }
    #     # Create or update the visitor.details record
    #     visitor_record = self.env['visitor.details'].create(visitor_vals)
    #     return visitor_record