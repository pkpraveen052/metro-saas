# -*- coding: utf-8 -*-

{
    'name': 'Metro - All In One Financial Documents',
    'version': '1.0',
    'category': 'Accounting',
    'sequence': 110,
    'summary': 'All in one place FS, XBRL, GST, FORM CS etc.',
    'website': 'https://metrogroup.solutions/',
    'depends': [
        'metroerp_fs',
        'metroerp_iras'
    ],
    'description': """
    """,
    'data': [
        'security/ir.model.access.csv',
        'security/res_groups.xml',
        'data/data.xml',
        'views/financial_documents.xml',
        'views/assets.xml',
    ],
    'qweb': [
    ],
    'demo': [],
    'application': True,
}
