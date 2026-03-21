# -*- coding: utf-8 -*-

{
    "name": "Cancel Purchase Orders | Cancel PO",
    "author": "Metro Group",
    "website": "https://metrogroup.solutions/",
    "category": "Purchases",
    "license": "LGPL-3",
    "summary": "Cancel Purchase Orders, Cancel Purchase Order, Cancel PO,Purchase Order Cancel, Purchase Orders Cancel, Cancel RFQ, Cancel Request For Quotation,Purchase Cancel, Cancel RFQs, Delete Purchase Order,Delete PO,Delete RFQ",
    "description": """
This module helps to cancel created purchase orders. You can also cancel multiple purchase orders from the tree view. You can cancel the purchase order in 3 ways,

1) Cancel Only: When you cancel a purchase order then the purchase order is cancelled and the state is changed to "cancelled".
2) Cancel and Reset to Draft: When you cancel purchase order, first purchase order is cancelled and then reset to the draft state.
3) Cancel and Delete: When you cancel a purchase order then first purchase order is cancelled and then purchase order will be deleted.

We provide 2 options in the cancel purchase orders,

1) Cancel Receipt: When you want to cancel purchase orders and receipt then you can choose this option.
2) Cancel Bill and Payment: When you want to cancel purchase orders and bill then you can choose this option.

If you want to cancel purchase orders, receipts & bill then you can choose both options "Cancel Receipt" & "Cancel Bill and Payment".""",
    "version": "14.0.1.0",
    "depends": [
                "purchase",

    ],
    "application": True,
    "data": [
        'security/purchase_security.xml',
        'data/data.xml',
        'views/purchase_config_settings.xml',
        'views/views.xml',
    ],
    "auto_install": False,
    "installable": True,
    "price": 20,
    "currency": "EUR"
}
