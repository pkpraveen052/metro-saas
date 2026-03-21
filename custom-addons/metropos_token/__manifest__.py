# -*- coding: utf-8 -*-
{
    'name': "MetroERP POS Token",
    'version': '1.0.0',
    'author': 'Metro Group',
    'category': 'Sales/Point of Sale',
    'summary': 'MetroERP POS Token',
    'description': "",
    'website': 'https://metrogroup.solutions/',
    'depends': [
                'metroerp_customizations',
                'point_of_sale',
                'web',
                ],
    'data': [
        'views/pos_config.xml',
        'views/assets.xml',
    ],
     'qweb': [
        'static/src/xml/pos_token.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
