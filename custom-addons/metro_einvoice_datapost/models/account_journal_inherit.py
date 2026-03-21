from odoo import models,fields,api,_


class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    def get_journal_dashboard_datas(self):
        res = super(AccountJournal, self).get_journal_dashboard_datas()
        peppol_ready_count = self.env['account.move'].search_count([
            ('journal_id', 'in', self.ids),
            ('state', '=', 'posted'),
            ('outgoing_inv_doc_ref', '=', False)
        ])
        res['peppol_ready_count'] = peppol_ready_count
        return res