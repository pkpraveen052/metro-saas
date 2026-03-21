# -*- coding: utf-8 -*-
{
    'name' : "Convert Purchase from Sales Order",
    'version' : "14.0.0.3",
    'category' : "Purchases",
    'summary': 'This apps helps to Covert Purchase order from Sales Order',
    'description' : """
        Convert Purchase from Sales Order
        Convert Purchases from Sales Order
        Convert Purchase order from Sales Order
        Convert Purchases order from Sales Order

        create Purchase from Sales Order
        create Purchases from Sales Order
        create Purchase order from Sales Order
        create Purchases order from Sales Order


        Add Purchase from Sales Order
        Add Purchases from Sales Order
        ADD Purchase order from Sales Order
        ADD Purchases order from Sales Order

     """,
    'author' : "Metro Group Solutions",
    'website'  : "https://metrogroup.solutions",
    'depends'  : [ 'base','sale_management','purchase'],
    'data'     : [  'security/ir.model.access.csv',
                    'wizard/purchase_order_wizard_view.xml',
                    'views/inherit_sale_order_view.xml',
            ],      
    'installable' : True,
    'application' :  False,
    "images":['static/description/Banner.png'],
    # 'live_test_url':'https://youtu.be/wS4f9hEABxY',
}
