odoo.define('pos_cash_drawer.PaymentValidateCashDrawer', function(require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    const PaymentValidateCashDrawer = PaymentScreen =>
        class extends PaymentScreen {
            /**
             * @override
             */
            async validateOrder(isForceValidate) {
                await super.validateOrder(isForceValidate);
                console.log("\n\nCustom validateOrder(isForceValidate) >>>>>  this",this,"\nisForceValidate ====",isForceValidate)
	        	console.log("this.currentOrder.is_paid_with_cash() ==",this.currentOrder.is_paid_with_cash(),"\nthis.currentOrder.get_change() ==",this.currentOrder.get_change())
	        	if ((this.currentOrder.is_paid_with_cash() || this.currentOrder.get_change()) && this.env.pos.config.cashdrawer_url) {
	        		console.log("this.env.pos.config.cashdrawer_url ====",cashdrawer_url)
	        		var cashdrawer_url = this.env.pos.config.cashdrawer_url
	        		$.get(cashdrawer_url, function(data, status){
	                    console.log("Data: " + data + "\nStatus: " + status);
	                    if(status !== 200) {
	                    	alert("Unable to open the Cash Drawer.\n Status: " + status);
	                    }
	                });
	        	}
            }
        };

    Registries.Component.extend(PaymentScreen, PaymentValidateCashDrawer);

    return PaymentScreen;
});
