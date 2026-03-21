# -*- coding: utf-8 -*-
{
    'name': "Market Place Quotations",
    "author": "Metro Group Pte. Ltd.",
    "license": "OPL-1",
    "website": "https://metrogroup.solutions",
    'category': 'Website',
    'summary': """
        Market Place Quotations
    """,
    'description': """
        Market Place Quotations
    """,
    'version': '14.0',
    'depends': ['sale_management'],
    'data': [
        'views/product_views.xml',
        'views/sale_portal_template.xml',
        'data/data.xml',
        'data/mail_template.xml',
        'views/res_config_settings.xml',
      
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
