from odoo import models,fields,api,_

class SecurityContractCheckPoint(models.Model):
    _name = "security.contract.checkpoint"
    _inherit = ['mail.activity.mixin','mail.thread','portal.mixin']
    _description = "Security Contract Checkpoint"
     
    name = fields.Char(string="Name",required=True,tracking=True)
    item_type = fields.Selection([('point','Point'),('plat','Plat')],default="point",string="Item Type",tracking=True)
    device_id = fields.Char(string="Device ID",required=True,tracking=True)
    location_id = fields.Many2one("security.location",string="Location",tracking=True,ondelete='restrict', required=True)
    contract_id = fields.Many2one(related="location_id.contract_id",store=True,string="Contract",tracking=True)
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)
    sequence = fields.Char(string="Sequence",required=True,help="Order in which checkpoints should be scanned",tracking=True)
