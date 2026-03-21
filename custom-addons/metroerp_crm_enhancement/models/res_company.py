from odoo import models,fields,api,_

class ResCompany(models.Model):
    _inherit = "res.company"


    @api.model
    def create(self, vals):
        print(">>>>>>>>>>>>>>>>>>>>>>>create method called")
        obj = super(ResCompany, self).create(vals)
        obj.sudo().create_crm_stages()
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>obj",obj)
        return obj
    


    def create_crm_stages(self):
        existing_crm_stages = self.env['crm.stage'].sudo().search([('company_id', '=', self.id)])
        if existing_crm_stages:
            print("/n/n/n/n/n crm stages exist for this company.")
            return
        
        crm_stages_data = [
            {
                'name': 'New',
                'sequence': 1,
                'company_id': self.id,
            },
            {
                'name': 'Qualified',
                'company_id': self.id,
                'sequence': 2,
            },
            {
                'name': 'Proposition',
                'company_id': self.id,
                'sequence': 3,
            },
            {
                'name': 'Won',
                'company_id': self.id,
                'is_won': True,
                'sequence': 70,
            },

            
        ]
        crm_stages_model = self.env['crm.stage']
        for stages in crm_stages_data:
            crm_stages_model.create(stages)




           
      