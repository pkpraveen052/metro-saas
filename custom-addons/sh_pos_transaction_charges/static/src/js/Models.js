odoo.define('sh_pos_transaction_charges.models' , function(require) {
    'use strict';
    
    var models = require("point_of_sale.models");

    models.load_fields('product.product', ['sh_is_credit_card_charge'])
    models.load_fields('pos.payment.method', ['sh_pos_enable_transaction_cherge','sh_pos_transaction_charge','sh_pos_card_charge'])

    var _super_Orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({

        export_for_printing: function () {
            var receipt = _super_Orderline.export_for_printing.call(this);
            receipt['is_transaction_charge_product'] = this.get_product().sh_is_credit_card_charge
            return receipt;
        }
        
    })

});