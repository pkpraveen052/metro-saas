odoo.define("metro_pos_kitchen_receipt.ReceiptScreen", function (require) {
    "use strict";

    const ReceiptScreen = require("point_of_sale.ReceiptScreen");
    const { Printer } = require('point_of_sale.Printer');
    const Registries = require("point_of_sale.Registries");
    const { useListener } = require("web.custom_hooks");

    const PrintKitchenReceiptScreen = (ReceiptScreen) =>
        class extends ReceiptScreen {
            constructor() {
                super(...arguments);
                useListener("on_click_print_kitchen_receipt", this.on_click_print_kitchen_receipt);
            }

            async on_click_print_kitchen_receipt(event) {
            	console.log("on_click_print_kitchen_receipt()....",this)
                const order = this.env.pos.get_order();
	            if (order.get_orderlines().length > 0) {
	                console.log("order =",order)
	                console.log("order.get_orderlines() =",order.get_orderlines())
	                // order.initialize_validation_date();
	                await this.showTempScreen('KitchenReceiptScreen', { order });
	            } else {
	                await this.showPopup('ErrorPopup', {
	                    title: this.env._t('Nothing to Print'),
	                    body: this.env._t('There are no order lines'),
	                });
	            }
            }
        };

    Registries.Component.extend(ReceiptScreen, PrintKitchenReceiptScreen);

    return ReceiptScreen;
});



