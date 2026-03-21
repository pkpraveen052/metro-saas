odoo.define('metro_pos_kitchen_receipt.KitchenReceiptScreen', function (require) {
    'use strict';

    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const Registries = require('point_of_sale.Registries');

    const KitchenReceiptScreen = (ReceiptScreen) => {
        class KitchenReceiptScreen extends ReceiptScreen {
            confirm() {
                console.log("\nconfirm() ...",this)
                this.props.resolve({ confirmed: true, payload: null });
                this.trigger('close-temp-screen');
            }
            whenClosing() {
                console.log("\nwhenClosing() ...",this)
                this.confirm();
            }
            /**
             * @override
             */
            async printReceipt() {
                await super.printReceipt();
                this.currentOrder._printed = false;
            }
        }
        KitchenReceiptScreen.template = 'KitchenReceiptScreen';
        return KitchenReceiptScreen;
    };

    Registries.Component.addByExtending(KitchenReceiptScreen, ReceiptScreen);

    return KitchenReceiptScreen;
});
