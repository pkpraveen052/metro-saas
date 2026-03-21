# -*- coding: utf-8 -*-
{
    "name" : "Assign Sales Person on POS - Point of Sales Sales Person",
    "author": "Metro Group",
    "version" : "14.0.1.0",
    "images":["static/description/main_screenshot.png"],
    'summary': 'POS salesperson for pos order sales person point of sales sales person pos sales person for pos saleperson for point of sales assign sales person for pos assign sales person for point of sale sale person pos salesman assign salesman on point of sale orders.',
    "description": """
        This app used to add sales person from the pos screen.

    """,
    "license" : "OPL-1",
    "depends" : ['base','point_of_sale'],
    "data": [
        'views/pos_view.xml',
    ],
    'qweb': [
        'static/src/xml/pos.xml',
    ],
    "auto_install": False,
    "installable": True,
    "category" : "Point of Sale",
}

