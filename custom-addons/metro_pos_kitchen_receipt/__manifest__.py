# -*- coding: utf-8 -*-
{
    'name': "MetroERP POS Kitchen Receipt",
    'version': '1.0.0',
    'author': 'Metro Group',
    'category': 'Point of Sale',
    'summary': 'MetroERP POS Kitchen Receipt',
    'description': "",
    'website': 'https://metrogroup.solutions/',
    'depends': [
                'point_of_sale',
                ],
    'data': [
        'views/assets.xml',
        'views/pos_config_views.xml',
    ],
    'qweb': [
        'static/src/xml/PreviewKitchenReceiptButton.xml',
        'static/src/xml/KitchenReceiptScreen.xml'
    ],
    # 'assets': {
    #     'point_of_sale.assets': [
    #         'metro_pos_kitchen_receipt/static/src/xml/PreviewKitchenReceiptButton.xml',
    #         'metro_pos_kitchen_receipt/static/src/xml/KitchenReceipt.xml',
    #     ],
    # },
    'installable': True,
    'application': True,
    'auto_install': False,
}
