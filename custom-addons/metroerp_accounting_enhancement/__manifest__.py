{
    'name': 'Metroerp Accouting Enhancement',
    'version': '1.0',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/paper_format.xml',
        'data/account_financial_report_data.xml',
        'views/assets.xml',
        'report/payment_voucher_report.xml',
        'views/account_move_views.xml',
        'report/custom_header_report.xml',
        'report/payment_voucher_report_payer.xml',
        'views/account_bank_statement_views.xml',
        'views/account_journal_dashboard_view.xml',
        'views/report_financial.xml',
        'views/search_template_view.xml',

    ],
    'qweb': [
        'static/src/xml/account_report_template.xml',
    ],
    'installable': True,
    'auto_install': False,
}
