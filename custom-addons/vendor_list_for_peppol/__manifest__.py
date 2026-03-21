# -*- coding: utf-8 -*-
{
    'name': "Vendor List For Peppol",
    "author": "Metro Group Pte. Ltd.",
    "license": "OPL-1",
    "website": "https://metrogroup.solutions",
    'category': 'sales',
    'summary': """
        Vendor List For Peppol
    """,
    'description': """
        Vendor List For Peppol
    """,
    'version': '14.0',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/menus.xml',
        'views/vendor_list_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
