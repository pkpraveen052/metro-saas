# -*- coding: utf-8 -*-
{
    'name': "Sales Detail Listing",
    'summary': """""",
    'description': """School Mangement Software""",
    'author': "Metro Group",
    'website': "http://www.metrogroup.com",
    'category': '',
    'version': '0.1',
    'depends': ['base','point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'reports/paper_format.xml',
        'reports/report.xml',
        'reports/template.xml',
        'wizard/sales_detail_listing_wizard.xml',
    ],
    'auto_install': True,
    'application': False,
    'active': False,
    'sequence': 10,
}
