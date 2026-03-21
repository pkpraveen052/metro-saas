from odoo import models,fields,_,api


class ResPartner(models.Model):
    _inherit = "res.partner"

    def action_save_onboarding_partner_step(self):
        ctx = dict(self._context or {})
        purchase_partner_popup = ctx.get('from_purchase_partner_popup', False)
        if purchase_partner_popup:
            self.env.company.sudo().set_onboarding_step_done('purchase_onboarding_partner_state')
        else:
            self.env.company.sudo().set_onboarding_step_done('sale_onboarding_partner_state')

    def action_skip_onboarding_customer(self):
        self.env.company.sudo().set_onboarding_step_done('sale_onboarding_partner_state')
