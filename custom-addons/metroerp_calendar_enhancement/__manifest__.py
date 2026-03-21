# -*- coding: utf-8 -*-
{
    'name': "MetroERP Calendar Enhancement",
    'version': '1.0',
    'author': 'Metro Group',
    'category': '',
    'summary': 'MetroERP Calendar Enhancement',
    'description': "",
    'website': 'https://metrogroup.solutions/',
    'depends': ['calendar',],
    'data': [
        'security/ir_rule.xml',
        'views/calendar_event_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,    
}
