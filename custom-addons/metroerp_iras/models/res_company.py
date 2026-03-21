from odoo import models,fields,_

class ResCompanyInherit(models.Model):
    _inherit = "res.company"
    
    target_moves = fields.Selection([('posted', "All Posted Entries"), ('all', "All Entries")], default='all', string='Target moves')
    target_moves_f7 = fields.Selection([('posted', "All Posted Entries"), ('all', "All Entries")], default='all', string='Target moves')
    uenType = fields.Selection([('6', 'ROC'), ('35', 'UENO'), ('8', 'ASGD'), ('10', 'ITR')], default='6',string="UEN Type")    
    target_moves_formcs = fields.Selection([('posted', "All Posted Entries"), ('all', "All Entries")], default='all', string='Target moves')

    def install_chart_of_accounts(self):
        result = super(ResCompanyInherit, self).install_chart_of_accounts()
        self.map_iras_fields_to_accounts()
        return result

    def map_iras_fields_to_accounts(self):
        """Method to map IRAS fields to account accounts based on account template codes"""
        iras_template = self.env['iras.default.accounts.mapping'].search([], limit=1)
        
        if iras_template and self.env.company.chart_template_id:
            self.env.company.chart_template_id.iras_template_id = iras_template.id
            for line in iras_template.line_ids:
                account_template = line.account_template_id  
                iras_field = line.iras_field_id  
                matching_accounts = self.env['account.account'].search([
                    ('code', '=', account_template.code),
                    ('company_id', '=', self.env.company.id)
                ])

                if matching_accounts:
                    for matching_account in matching_accounts:
                        if iras_field:
                            matching_account.iras_mapping_ids = [(4, iras_field.id)]  
            return True 
        return False  
    
    