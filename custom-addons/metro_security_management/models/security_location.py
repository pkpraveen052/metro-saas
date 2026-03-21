from odoo import models,fields,api,_
from odoo.exceptions import ValidationError

class SecurityLocation(models.Model):
    _name = "security.location"
    _inherit = ['mail.activity.mixin','mail.thread','portal.mixin']
    _description = "Security Location"
    _rec_name = "location_ref"
    
    location_ref = fields.Char(string="Location Ref", required=True,readonly=True,default="New",copy=False)
    location_name = fields.Char(string="Location Name",required=True)
    address_id = fields.Many2one("res.partner",string="Address",required=True,tracking=True)
    contract_id = fields.Many2one("security.contract",string="Contract",required=True,tracking=True)
    start_date = fields.Date(string="Start Date",required=True)
    end_date = fields.Date(string="End Date",required=True)
    active = fields.Boolean(string="Active",default=True)
    checkpoint_ids = fields.One2many("security.contract.checkpoint","location_id",string="Check Points")
    security_ids = fields.Many2many("security.person",string="Security Person",tracking=True)
    color = fields.Integer('Color Index', default=0)
    visitor_count = fields.Integer(string="Visitor Count",compute="_compute_visitor_count",store=False)
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)
    block_location_id = fields.Many2one('block.location',string="Block Location")

    block_location_ids = fields.One2many('block.location','security_location_id', string="Block Locations")
    block_location_count = fields.Integer(string="Block Location Count", compute='_compute_block_location_count')
    block_visitor_count = fields.Integer(string="Block Visitor Count",compute="_compute_block_visitor_count",store=False)

    @api.depends('block_location_ids')
    def _compute_block_location_count(self):
        for record in self:
            record.block_location_count = len(record.block_location_ids)


    @api.model
    def create(self, vals):
        if vals.get('location_ref', 'New') == 'New':
            vals['location_ref'] = self.env['ir.sequence'].sudo().next_by_code('security.location') or 'New'
        res = super(SecurityLocation, self).create(vals)
        self.env["block.location"].create({
            "name": res.location_name, 
            "security_location_id": res.id, 
        })
        return res
    
    
    
    @api.constrains('start_date','end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError("End Date cannot be earlier than Start Date.")
    
    
    def _compute_visitor_count(self):
        for location in self:
            location.visitor_count = self.env['visitor.details'].search_count([
                ('location_id', '=', location.id)
            ])

    def _compute_block_visitor_count(self):
        for location in self:
            location.block_visitor_count = self.env['block.list'].search_count([
                ('location_id', '=', location.id)
            ])

    def action_view_visitors(self):
        self.ensure_one()
        return {
            'name': 'Visitors',
            'type': 'ir.actions.act_window',
            'res_model': 'visitor.details',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('location_id', '=', self.id)],  # Filter visitors by current location
            'context': {
                'default_location_id': self.id  # Set the location_id by default when creating a new visitor
            }
        }
    

    def action_block_visitors(self):
        self.ensure_one()
        return {
            'name': 'Block Visitor',
            'type': 'ir.actions.act_window',
            'res_model': 'block.list',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('location_id', '=', self.id)],  # Filter visitors by current location
            'context': {
                'default_location_id': self.id  # Set the location_id by default when creating a new visitor
            }
        }
    
    def action_open_block_locations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Block Locations',
            'res_model': 'block.location',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('security_location_id', '=', self.id)],
        }

    