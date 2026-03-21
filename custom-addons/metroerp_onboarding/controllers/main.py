from odoo import http
from odoo.http import request


class OnboardingPurchaseController(http.Controller):

    @http.route('/metroerp_onboarding/purchase_dashboard_onboarding', auth='user', type='json')
    def purchase_dashboard_onboarding(self):
        """ Returns the `banner` for the account dashboard onboarding panel.
            It can be empty if the user has closed it or if he doesn't have
            the permission to see it. """
        company = request.env.company

        if not request.env.is_admin() or \
                company.purchase_dashboard_onboarding_state == 'closed':
            return {}

        return {
            'html': request.env.ref('metroerp_onboarding.purchase_dashboard_onboarding_panel')._render({
                'company': company,
                'state': company.get_and_update_purchase_onboarding_state()
            })
        }
