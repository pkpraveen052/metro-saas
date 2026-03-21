{
    'name': 'Metroerp Inventory Enhancement',
    'version': '1.0',
    'depends': ['stock','sale'],
    'data': [
        'views/stock_move.xml',
        'views/stock_quant_views.xml',
        'views/sale_order.xml',
        'views/stock_picking.xml',
        'views/product_category.xml'
    ],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
}
