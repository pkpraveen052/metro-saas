# -*- coding: utf-8 -*-

{
    'name' : 'Recurring Invoice Subscription odoo',
    'author': "Edge Technologies",
    'version' : '14.0.1.0',
    'live_test_url':'https://youtu.be/8GkPVucbUZk',
    "images":["static/description/main_screenshot.png"],
    'summary' : 'Apps for invoice recurring orders invoice subscription recurring invoice recurring subscription customer invoice subscription process subscription on invoice recurring customer subscription on invoice subscription recurring process subscription management',
    'description' : """
        User can make recurring invoice manually or automatically as per duration configured.
    """,
    "license" : "OPL-1",
    'depends' : ['base','account'],
    'data': [
            'security/ir.model.access.csv',
            'security/ir_rule.xml',
            'data/email_template.xml',
            'data/ir_cron.xml',
            'views/invoice_view.xml',
            'wizard/recurring_invoice.xml',
            'views/recurring_invoice_view.xml',
            ],
    'qweb' : [],
    'demo' : [],
    'installable' : True,
    'auto_install' : False,
    'price': 18,
    'category' : 'Accounting',
    'currency': "EUR",
}
