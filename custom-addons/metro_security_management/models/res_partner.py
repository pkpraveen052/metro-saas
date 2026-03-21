# from odoo import models,fields,api,_

# class ResPartner(models.Model):
#     _inherit = "res.partner"

#     ic_number = fields.Char(string="IC Number")

#     service_location_id = fields.Many2one(
#         "fsm.location", string="Primary Service Location"
#     )

#     # @api.model
#     # def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
#     #     args = args or []
#     #     domain = []
        
#     #     if name:  
#     #         domain = ['|', '|', '|', 
#     #                   ('name', operator, name), 
#     #                   ('ic_number', operator, name), 
#     #                   ('phone', operator, name), 
#     #                   ('email', operator, name)]
        
#     #     return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)