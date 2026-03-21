from odoo import models,fields,_,api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def action_save_onboarding_product_step(self):
        # ctx = dict(self._context or {})
        # purchase_popup = ctx.get('from_purchase_product_popup', False)
        # if purchase_popup:
        #     self.env.company.sudo().set_onboarding_step_done('purchase_onboarding_product_state')
        # else:
        self.env.company.sudo().set_onboarding_step_done('sale_onboarding_product_state')

    def action_skip_onboarding_product(self):
        self.env.company.sudo().set_onboarding_step_done('sale_onboarding_product_state')
