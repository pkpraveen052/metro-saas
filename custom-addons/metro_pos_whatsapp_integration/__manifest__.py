# -*- coding: utf-8 -*-
{
    "name" : "Metro POS What's up Integration",
    "author": "Metro Group",
    "version" : "14.0.1.0",
    'summary': '',
    "category" : "Point of Sale",
    "description": """
        This app used to send what's up on pos screen.

    """,
    "depends" : ['base','point_of_sale','metroerp_pos','mail','portal'],
    "data": [
        'views/res_users_inherit_view.xml',
        'views/pos_config_views.xml',
        'views/templates.xml',
    ],
    'qweb': [
        'static/src/xml/pos.xml',
    ],
    "auto_install": False,
    "installable": True,
    "license" : "OPL-1",
}
