{
    'name': "Send Low Stock Alert To Inventory Manager",
    'summary': """Send Low Stock Alert To Inventory Manager""",
    'description': """
        This module is used to Send Low Stock Alert To Inventory Manager.
    """,
    'author': "Metro Group",
    'website': "https://metrogroup.solutions/",
    'license': '',
    'version': '14.0.1',
    'depends': ['stock'],

    'data': [
        'data/ir_cron.xml',
        'security/security.xml',
        'views/config_view.xml',
        'views/stock_location_view.xml',
    ],
    'demo': [],

    'installable': True,
    'application': True,
    'auto_install': False,
    
}
