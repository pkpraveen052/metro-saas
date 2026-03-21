{
    'name': 'MetroERP FS',
    'version': '1.0',
    'depends': ['account','docx_report_generation'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/menus.xml',
        'views/director_statement_template.xml',
        'views/director_statement_config.xml',
        'views/director_statement.xml',
        'views/corporate_doc.xml',
        'data/report.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
}
