from odoo import models,fields,api,_
from datetime import date

class SecurityContract(models.Model):
    _name = "security.contract"
    _inherit = ['mail.activity.mixin','mail.thread','portal.mixin']
    _description = "Security Contract"
    _order = "id desc"
    _rec_name = "contract_ref"
    
    name = fields.Char(string="Contract Name")
    contract_ref = fields.Char(string="Contract Ref",required=True, readonly=True,default="New",copy=False)
    partner_id = fields.Many2one("res.partner",string="Contact Person",required=True,tracking=True)
    service_buyer = fields.Char(string="Service Buyer Name",required=True)
    description = fields.Text(string="Description")
    state = fields.Selection([('draft', 'Draft'),('running','Running'), ('expired', 'Expired')],default='draft',tracking=True,string="Status")
    active = fields.Boolean(string="Active",default=True)
    location_ids = fields.One2many("security.location","contract_id",string="Location")
    color = fields.Integer('Color Index', default=0)
    location_count = fields.Integer(string='Location Count', compute='_compute_location_count')
    phone = fields.Char(compute="_compute_partner_id",string="Phone",store=True)
    email = fields.Char(compute="_compute_partner_id",string="Email",store=True)
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)
    contract_date = fields.Date(string="Contract Date",default=date.today(),tracking=True)
    expired_date = fields.Date(string="Expired Date",compute="_calculate_expired_date",store=True,readonly=False)

    @api.depends('partner_id')
    def _compute_partner_id(self):
        for record in self:
            if record.partner_id:
                partner = record.partner_id
                if (not partner.phone or not partner.email) and partner.parent_id:
                    record.phone = partner.parent_id.phone
                    record.email = partner.parent_id.email
                else:
                    record.phone = partner.phone
                    record.email = partner.email

    @api.depends('location_ids')
    def _compute_location_count(self):
        for contract in self:
            contract.location_count = len(contract.location_ids)
        
    @api.model
    def create(self, vals):
        if vals.get('contract_ref', 'New') == 'New':
            vals['contract_ref'] = self.env['ir.sequence'].sudo().next_by_code('security.contract') or 'New'
        res = super(SecurityContract, self).create(vals)
        return res
    

    def action_create_new(self):
        ctx = self._context.copy()
        ctx['default_contract_id'] = self.id
        return {
            'name': _('Create Location'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'security.location',
            'view_id': self.env.ref('metro_security_management.security_location_form_view').id,
            'context': ctx,
        }
    
    def action_view_locations(self):
        self.ensure_one()
        return {
            'name': 'Locations',
            'type': 'ir.actions.act_window',
            'res_model': 'security.location',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('contract_id', '=', self.id)],
        }
    

    @api.depends('state')
    def _calculate_expired_date(self):
        """ Automatically sets the expired date when contract state changes to 'expired'. """
        for rec in self:
            if rec.state == 'expired':
                rec.expired_date = date.today()
    

