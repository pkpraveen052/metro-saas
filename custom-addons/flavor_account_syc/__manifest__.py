# -*- coding: utf-8 -*-
{
    'name': 'Flavor Account Syc',
    'version': '1.1.1',
    'author': 'Flavor Group',
    'category': 'All',
    'summary': 'Flavor',
    'description': "",
    'depends': ['base','account','metroerp_discount'],
    'auto_install': True,
    'data': [
        # "data/flavor.xml",
        "data/res_groups.xml",
        'views/templates.xml',
        "views/res_config_settings.xml",
        "views/account_move_view.xml",
    ],
    "qweb": [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
