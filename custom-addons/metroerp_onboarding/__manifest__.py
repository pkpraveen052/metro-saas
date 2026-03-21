# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Accouting Onboarding',
    'version' : '1.0',
    'summary': '',
    'sequence': 30,
    'description': """
Core mechanisms for the accounting modules. To display the menuitems, install the module account_invoicing.
    """,
    'category': '',
    'website': '',
    'depends' : ['base','account','metroerp_iras'],
    'data': [ 'security/ir.model.access.csv',
             'views/account_onboarding_panel_template_inherit.xml',
             'wizard/sales_tc_wizard.xml',
             'views/res_company_views.xml',
              'wizard/account_fiscal_year_wizard_view.xml',
              'views/sales_onboarding_panel_template_inherit.xml',
              'views/product_view_inherit.xml',
              'views/res_partner_view_inherit.xml',
              'views/ks_configuration_form_inherit.xml',
              'views/purchase_view_inherit.xml',
              'views/purchase_onboarding_panel_template.xml',
              'views/charts_of_account_view_inherit.xml',
              'wizard/purchase_tc_wizard.xml',
    ],
    'demo': [

    ],
    'qweb': [

    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}