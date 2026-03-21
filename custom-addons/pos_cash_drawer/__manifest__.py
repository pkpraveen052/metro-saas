# -*- coding: utf-8 -*-
{
    'name': "Metro - POS Cash Drawer",
    "author": "Metro Group Pte Ltd",
    'category': 'Point of Sale',
    'summary': """
        Metro - POS Cash Drawer
    """,
    'description': """
        Metro - POS Cash Drawer
    """,
    'version': '14.0.0.1',
    'depends': ['point_of_sale'],
    'data': [
        'views/assets.xml',
        "views/pos_config.xml"
    ],
    "qweb":  [
        'static/src/xml/Chrome.xml',
        ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
