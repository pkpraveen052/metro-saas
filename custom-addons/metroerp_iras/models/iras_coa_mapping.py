from odoo import models,fields,api

class IrasCoaMapping(models.Model):
    _name="iras.coa.mapping"
    _rec_name = 'description'

    name = fields.Char(string="Name", required=True)
    description = fields.Text("Description", required=True)
    direct_mapping = fields.Boolean('Direct Mapping', default=True)
    account_ids = fields.Many2many("account.account", compute="_get_account_ids", string="Mapped Accounts")
    date_as_of = fields.Boolean('Date (As of)')
    reverse_sign = fields.Boolean('Reverse the sign')

    def _get_account_ids(self):
    	for obj in self:
    		acc_ids = self.env['account.account'].search([('iras_mapping_ids','in',[obj.id])]).ids
    		obj.account_ids = acc_ids and [(6,0,acc_ids)] or False