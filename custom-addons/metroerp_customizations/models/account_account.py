from odoo import models

class AccountAccount(models.Model):
    _inherit = "account.account"

    def action_open_journal_items(self):
        self.ensure_one()
        action = self.env.ref("account.action_move_line_select").read()[0]
        action['context'] = dict(self.env.context or {})
        action['context'].update({
            'search_default_account_id': [self.id],  # safe replacement for active_id
            'search_default_posted': 1,
        })
        return action
