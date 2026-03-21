# Part of Softhealer Technologies.
{
    "name": "POS Transaction Charges",

    "author": "Softhealer Technologies",

    "website": "https://www.softhealer.com",

    "support": "support@softhealer.com",

    "category": "point_of_sale",

    "summary": "POS Transaction Charges POS fees Point of Sale charges POS fees Point of Sale Transaction  charges Transaction service fees Transaction service charges POS transaction costs management POS transaction charges module Payment terminal charges software Transaction fee POS transactions cost Credit card processing charges Debit card transaction fees POS Transactions Charge Point Of Sale Transactions Charge Transaction Charges For POS Transaction Charge Of POS many pending analyse on appstore for the same POS Service Charges POS Extra Charges Point of Sale Service Charges Point of Sales Extra Charges POS Additional Charges POS Additional Fees Manage Extra Charges Manage Transactions Charges POS Odoo",

    "description": """With our transaction charge payment module, 
    you can easily handle transaction payments. Choose between a 
    percentage or fixed-amount charge based on your needs. 
    You can view receipts by either printing them or sharing via email. 
    Try out this efficient module and save valuable time.""",

    "version": "14.0.1",

    "license": "OPL-1",

    "depends": ["point_of_sale"],

    "application": True,

    "data": [
        'demo/credit_card_charge.xml',
        'views/assets.xml',
        # 'views/pos_config.xml',
        'views/pos_payment_method.xml',
        'views/product_product.xml'
    ],
    "images": ["static/description/background.png", ],

    "auto_install": False,

    "installable": True,

    "price": 25,

    "currency": "EUR"
}
