# -*- coding: utf-8 -*-
{
    'name': "POS - Metro Paynow",
    "author": "Metro Group",
    "license": "OPL-1",
    "website": "https://metrogroup.solutions/",
    'category': 'Website',
    'summary': """
        POS - Metro Paynow
    """,
    'description': """
        POS - Metro Paynow
    """,
    'version': '14.0.0.1',
    'depends': ['point_of_sale', 'l10n_sg'],
    'data': [
        'views/assets.xml',
    ],
    "qweb":  [
        'static/src/xml/CustomerScreen.xml',
        ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
