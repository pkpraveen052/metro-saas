# -*- coding: utf-8 -*-
{
    'name': "MetroERP Assistro Whatsapp",
    'version': '1.2.1',
    'author': 'Metro Group',
    'category': 'All',
    'summary': 'MetroERP  Assistro Whatsapp',
    'description': "",
    'website': 'https://metrogroup.solutions/',
    'depends': [
                'base','metroerp_customizations','account','purchase','sale','stock',
                ],
    'data': [
        'data/ir_cron_data.xml',
        'data/demo_data.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/assistro_whatsapp_template_views.xml',
        'views/res_config_settings.xml',
        'views/sale_order_inherited_views.xml',
        'views/account_move_views.xml',
        'views/stock_picking_views.xml',
        'views/purchase_order_views.xml',
        'views/whatsapp_log_views.xml',
        'wizard/whatsapp_composer_views.xml',
        'wizard/whatsapp_placeholder_views.xml',
        
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
