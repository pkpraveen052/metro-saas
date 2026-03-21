# -*- coding: utf-8 -*-

{
    'name': "User Guide",
    'version': '1.14.0.1',
    'author': 'Metro Group',
    'category': 'All',
    'summary': 'MetroERP UserGuide',
    'description': "",
    'website': 'https://metrogroup.solutions/',
    'depends': ['base', 'web', 'mail', 'account', 'sale', 'purchase', 'stock', 'metro_einvoice_datapost', 'contacts'],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'data/user_guide_tags.xml',
        'views/user_guide.xml',
        'views/user_guide_url.xml',
        'views/user_guide_tags.xml',
        'views/templates.xml',
        'views/menu.xml',
    ],
    "qweb": [
        "static/src/xml/tree_button.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
