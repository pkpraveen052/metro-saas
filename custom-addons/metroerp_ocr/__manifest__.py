# -*- coding: utf-8 -*-
{
    'name': "MetroERP OCR",
    'version': '1.0.0',
    'author': 'Metro Group',
    'category': 'All',
    'summary': 'MetroERP OCR',
    'description': "",
    'website': 'https://metrogroup.solutions/',
    'depends': [
        'base','account', 'purchase','sale','contacts'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
        'wizard/invoice_ocr_upload_wizard_views.xml',
        'wizard/vendor_creation_wizard_views.xml',
        'views/account_setting_views.xml',
        'wizard/mismatch_warning_wizard_views.xml',
        'views/invoice_ocr_logs_view.xml',
        'views/account_move_views.xml'
    ],
    "qweb": [
        
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3'
}
