odoo.define('pos_cash_drawer.chrome', function (require) {
    'use strict';

    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    const PosComponent = require('point_of_sale.PosComponent');

    const PosCashDrawerChrome = (Chrome) =>
        class extends Chrome {
            constructor() {
            	console.log("\nPosCashDrawerChrome >>>>>>> constructor()")
	            super(...arguments);
	            useListener('cash-drawer-open', this.__cashDrawerOpen);
	        }
	        __cashDrawerOpen(event) {
	            console.log("\n__cashDrawerOpen .....this =",this)
	            var cashdrawer_url = this.env.pos.config.cashdrawer_url
	            if (cashdrawer_url !== false || cashdrawer_url !== undefined) {
	            	console.log("cashdrawer_url ====",cashdrawer_url)
	                $.get(cashdrawer_url, function(data, status){
	                    console.log("Data: " + data + "\nStatus: " + status);
	                    if(status !== 200) {
	                    	alert("Unable to open the Cash Drawer.\n Status: " + status);
	                    }
	                });
	            }
	        }
	        // get cashDrawerButtonIsShown() {
	        // 	console.log("\ncashDrawerButtonIsShown()....this",this)
	        //     return (
	        //         this.env.pos.config.cashdrawer_url
	        //     );
	        // }
        };

    Registries.Component.extend(Chrome, PosCashDrawerChrome);

    return Chrome;
});