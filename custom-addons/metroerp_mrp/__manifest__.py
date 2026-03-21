{
    'name': "MetroERP MRP Customizations",
    'version': '1.0.0',
    'author': 'Metro Group',
    'category': 'MRP',
    'summary': 'MetroERP MRP Customizations',
    'description': "",
    'website': 'https://metrogroup.solutions/',
    'depends': [
                'metroerp_customizations',
                'mrp',
                'stock',
                'sale_mrp'
                ],
    'data': [
        'data/data.xml',
        'views/mrp_immediate_production_views.xml',
        'views/res_users.xml',
        'views/menu.xml',
        'views/mrp_production_views.xml',
        'views/res_config_settings.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
# -*- coding: utf-8 -*-
