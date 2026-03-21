{
    'name': 'Service Management',
    'summary': """ """,
    'company': 'Metro Group Solution',
    'author': 'Metro',
    'website': '',
    'category': 'Extra Tools,Tools',
    'version': '17.0.1.0',
    'license': 'OPL-1',
    'depends': ['base', 'web', 'product', 'all_in_one_dynamic_custom_fields', 'metro_whatsapp_integration', 'portal'],
    'data': [
          'security/service_management_security.xml',
          'security/security.xml',
          'security/ir.model.access.csv',
          'data/data.xml',
          'views/service_management_views.xml',
          'views/service_template_view.xml',
          'views/assets.xml',
          'views/service_dashboard_views.xml',
          'views/res_partner_view.xml',
          'views/service_menu_views.xml',
          'wizard/service_assignment_wizard.xml',
          'views/service_management_portal_template.xml',
          'views/res_users.xml',
          'data/mail_template.xml'
    ],
    'description': """
    """
}
