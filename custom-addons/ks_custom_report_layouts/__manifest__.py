# -*- coding: utf-8 -*-
{
	'name': 'Metro Custom Reports',

	'summary': """
Metro Custom Reports,Reports,Metro reports,Custom Reports,Customize reports,customize your report,
                   Sales Order report,Purchase Order report,Payment Receipt,Custom Layout Option,report customization,
                   Custom,Report templates,Custom layout,sales report.
""",

	'description': """
odoo custom reports,
        odoo 14 reports,
        odoo14 custom reports,
        odoo 14 reporting apps,
        odoo dynamic reports,
        odoo report customizing,
        odoo report preview,
        odoo custom report module,
        odoo custom report template,
        odoo reports custom headers,
        odoo module for custom reports,
        custom invoice reports,
        custom sales reports,
        business analytics reports,
        custom stocks reports,
        custom sales reports,
        odoo professional reports,
        Financial and Analytical Reports,
        MS Excel format reports,
        sales order reports,
        odoo dynamic reports,
        custom invoice reports,
        delivery order reports,
        custom report layouts,
        report layouts,

""",

	'author': 'Ksolves India Ltd.',

	'license': 'OPL-1',

	'website': 'https://store.ksolves.com',

	'maintainer': 'Ksolves India Ltd.',

	'version': '14.0.2.1.1',

	'support': 'sales@ksolves.com',

	'currency': 'EUR',

	'price': '83.3',

	'category': 'Tools',

	'depends': ['web', 'sale_management', 'purchase', 'account', 'stock', 'metroerp_customizations','metroerp_discount','metroerp_progressive_billing','partner_statement'],

	'live_test_url': 'https://reporttemplates14.kappso.com/',

	'images': ['static/description/Top odoo -Ksolves Diwali SALE.gif'],

	'data': [
		'security/ir.model.access.csv',
		'security/ks_security.xml',
		'data/paper_format_data.xml',
		'data/ks_sale_styles_data.xml',
		'views/ks_assets.xml',
		'views/ks_inherit_sale_order_view.xml',
		'views/ks_report_configuraton_view.xml',
		'views/ks_res_config_settings_views.xml',
		'views/ks_inherit_account_payment.xml',
		'views/ks_watermark.xml',
		'views/ks_dummy_prev.xml',
        'views/res_company_inherited_views.xml',
		'report/ks_sale_styles.xml',
		'report/ks_invoice_styles.xml',
		'report/ks_purchase_styles.xml',
		'report/ks_rfq_report_style.xml',
		'report/ks_deliveryslip_style.xml',
		'report/ks_picking_style.xml',
		'report/ks_invoice_account_payment_style.xml',
		'report/ks_sale_report_templates.xml',
		'report/ks_invoice_report_templates.xml',
		# 'report/ks_bill_report_template.xml',
		'views/ks_inherit_invoice_signature.xml',
		'views/ks_inherit_purchase_signature.xml',
        'views/metro_custom_dummy_preview.xml',
		'report/ks_purchase_report_templates.xml',
		'report/ks_rfq_purchase_report_templates.xml',
		'report/ks_deliveryslip_report_template.xml',
		'report/ks_picking_report_template.xml',
		'report/ks_invoice_account_payment_template.xml',
        'report/metro_custom_sale_report_inherit.xml',
        'report/metro_custom_invoice_report_inherit.xml',
        'report/metro_custom_purchase_report_inherit.xml',
        'report/metro_custom_delivery_report_inherit.xml',
        'report/metro_custom_picking_slip_report.xml',
        'report/metro_custom_payment_receipts_report.xml',
        'report/metro_custom_rfq_reports.xml',
        'report/metro_duplicate_invoice_report_template.xml',
        'report/ks_progressive_quotation_template.xml',
        'report/metro_custom_progressive_quotation_report.xml',
        'report/ks_progressive_invoice_templates.xml',
		'report/metro_custom_progressive_invoice_report.xml',
        'report/metro_custom_invoice_delivery_report.xml',
        'report/metro_invoice_report_with_local_currency.xml',
		'data/ks_email.xml',
	],

	'installable': True,

	'auto_install': False,
	'uninstall_hook': 'ks_report_uninstall_hook',

}
