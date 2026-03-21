from odoo import models,fields,api,_
from odoo.exceptions import ValidationError,UserError

class BlockLocation(models.Model):
    _name = "block.location"
    _inherit = ["mail.thread", "mail.activity.mixin","portal.mixin"]
    _description = "Block Location"

    name = fields.Char(string="Name",tracking=True)
    ref = fields.Char(string="Reference",tracking=True)
    fsm_parent_id = fields.Many2one("block.location", string="Parent", index=True,tracking=True)
    owner = fields.Char(string="Owner",tracking=True)
    sublocation_count = fields.Integer(string="Sub Locations", compute="_compute_sublocation_ids")
    complete_name = fields.Char(string="Complete Name", compute="_compute_complete_name", store=True)
    security_location_id = fields.Many2one("security.location",ondelete='cascade',string="Location",tracking=True)
    notes = fields.Text(string="Notes")
    address_id = fields.Many2one(related="security_location_id.address_id",readonly=False,store=True,tracking=True)
    phone = fields.Char(string="Phone",tracking=True)
    email = fields.Char(string="Email",tracking=True)
    active = fields.Boolean(string="Active",default=True)
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)
    partner_id = fields.Many2one("res.partner",string="Partner",domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
   
    @api.depends("name", "fsm_parent_id.complete_name", "ref")
    def _compute_complete_name(self):
        for loc in self:
            if loc.fsm_parent_id:
                if loc.ref:
                    loc.complete_name = "{} / [{}] {}".format(
                        loc.fsm_parent_id.complete_name, loc.ref, loc.name
                    )
                else:
                    loc.complete_name = "{} / {}".format(
                        loc.fsm_parent_id.complete_name, loc.name
                    )
            else:
                if loc.ref:
                    loc.complete_name = "[{}] {}".format(loc.ref, loc.name)
                else:
                    loc.complete_name = loc.name

    def name_get(self):
        results = []
        for rec in self:
            # Ensure complete_name is a string before returning
            name = rec.complete_name or ''  # Default to empty string if None
            results.append((rec.id, str(name)))
        return results

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []
        
        # Add all the fields you want to search by
        search_domain = [
            '|', '|', '|', '|', '|',  # Use bitwise OR for multiple conditions
            ('ref', operator, name),
            ('complete_name', operator, name),
            ('name', operator, name),
            ('owner', operator, name),
            ('phone', operator, name),
            ('email', operator, name)
        ] + args
        
        # Search for records based on the extended domain
        recs = self.search(search_domain, limit=limit)
        
        # Return the records found with the name_get method
        return recs.name_get()



   
    @api.onchange("fsm_parent_id")
    def _onchange_fsm_parent_id(self):
        self.owner = self.fsm_parent_id.owner or False
        # self.contact_id = self.fsm_parent_id.contact_id or False
        # self.street = self.fsm_parent_id.street or False
        # self.street2 = self.fsm_parent_id.street2 or False
        # self.city = self.fsm_parent_id.city or False
        # self.zip = self.fsm_parent_id.zip or False
        # self.state_id = self.fsm_parent_id.state_id or False
        # self.country_id = self.fsm_parent_id.country_id or False
       

    
    @api.constrains("fsm_parent_id")
    def _check_location_recursion(self):
        if not self._check_recursion(parent="fsm_parent_id"):
            raise ValidationError(_("You cannot create recursive location."))
        return True

   
    def _compute_sublocation_ids(self):
        for location in self:
            count = self.env['block.location'].search_count([
                ('fsm_parent_id', '=', location.id)
            ])
            location.sublocation_count = count

    def action_view_sublocation(self):
        self.ensure_one()
        return {
            'name': 'Sub Locations',
            'type': 'ir.actions.act_window',
            'res_model': 'block.location',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('fsm_parent_id', '=', self.id)],
        }
    
    def _compute_access_url(self):
        super(BlockLocation, self)._compute_access_url()
        for visitor in self:
            visitor.access_url = '/new/visitor/'



    pre_approve_visitor_count = fields.Integer(string="Pre Approved Visitor Count", compute="_compute_pre_approve_visitor_count", store=False)

    def _compute_pre_approve_visitor_count(self):
        for location in self:
            location.pre_approve_visitor_count = self.env['pre.approved.visitor'].search_count([
                ('unit_location_id', '=', location.id)
            ])


    def action_view_pre_approved_visitor(self):
        self.ensure_one()
        return {
            'name': 'Pre-approved Visitors',
            'type': 'ir.actions.act_window',
            'res_model': 'pre.approved.visitor',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('unit_location_id', '=', self.id)],
            'context': {
                'default_location_id': self.security_location_id.id,
                'default_unit_location_id': self.id,
            }
        }

    

    

    
