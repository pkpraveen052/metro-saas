# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
{
    'name': 'POS Kitchen screen (Community)',
    'version': '1.0.4',
    'category': 'Point of Sale',
    'website': 'http://www.acespritech.com',
    'price': 70.0,
    'currency': 'EUR',
    'summary': "A Screen for kitchen staff.",
    'description': "POS kitchen Screen shows orders and their state to Cook and Manager",
    'author': "Acespritech Solutions Pvt. Ltd.",
    'website': "www.acespritech.com",
    'depends': ['point_of_sale', 'bus', 'pos_restaurant'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_config.xml',
        'views/remove_product_resion_view.xml',
        'views/pos_order_view.xml',
        'views/res_users_view.xml',
        'views/pos_assets.xml',
    ],
    'qweb': [
        'static/src/xml/Chrome.xml',
        'static/src/xml/ChromeWidgets/KitchenScreenButton.xml',
        'static/src/xml/Screens/KitchenScreen/KitchenScreen.xml',
        'static/src/xml/Screens/KitchenScreen/OrderCard.xml',
        'static/src/xml/Screens/KitchenScreen/OrderCardLine.xml',
        'static/src/xml/Screens/KitchenScreen/OrderLinePrint.xml',
        'static/src/xml/Screens/KitchenScreen/OrderPrint.xml',
        'static/src/xml/Screens/ProductScreen/Orderline.xml',
        'static/src/xml/Screens/ProductScreen/ControlButtons/SendToKitchenButton.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': False
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
