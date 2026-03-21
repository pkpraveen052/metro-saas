from odoo import models,fields,api,_

class BlockList(models.Model):
    _name = "block.list"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Block List"
    _rec_name = "location_id"

    location_id = fields.Many2one("security.location", string="Location",required=True,tracking=True)
    visitor_company_id = fields.Many2one("visitor.company",string="Company",traking=True)
    visitor_vehicle_id = fields.Many2one("visitor.vehicle", string="Vehicle",traking=True)
    visitor_ic_num_id = fields.Many2one("ic.number", string="IC Number",traking=True)
    block_reason = fields.Selection(
        [('ic_number', 'IC Number'), ('vehicle', 'Vehicle'), ('company', 'Company')],
        string="Blocked By",traking=True
    )
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company.id)
    is_blocked = fields.Boolean("Is Blocked",default=True,traking=True)