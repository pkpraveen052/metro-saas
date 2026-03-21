# -*- coding: utf-8 -*-
{
    'name': 'Metroerp Discount',
    'version': '14.0.1',
    'author': 'Metroerp Discount',
    'category': 'All',
    'summary': 'Metroerp Discount',
    'description': "",
    'depends': ['base','account','sale','sale_management'],
    'auto_install': True,
    'data': [
        "views/account_move_view.xml",
        "views/sale_order_view.xml",
        'views/sale_portal_template.xml',
        "views/purchase_order_view.xml",
    ],
    "qweb": [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
