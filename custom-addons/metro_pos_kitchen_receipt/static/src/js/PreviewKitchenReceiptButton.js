// odoo.define('pos_kitchen_preview.PreviewKitchenReceiptButton', function (require) {
//     'use strict';

//     const { Gui } = require('point_of_sale.Gui');
//     const OrderWidget = require('point_of_sale.OrderWidget');
//     const Registries = require('point_of_sale.Registries');

//     const PreviewKitchenReceiptOrderWidget = (OrderWidget) =>
//         class extends OrderWidget {
//             constructor() {
//                 console.log("constructor() of PreviewKitchenReceiptOrderWidget....")
//                 super(...arguments);
//             }

//             async previewKitchenReceipt() {
//                 console.log("previewKitchenReceipt().....")
//                 const receipt = this.env.pos.env.qweb.render('KitchenReceipt', {
//                     order: this.props.order,
//                     widget: this,
//                 });

//                 Gui.showPopup('ConfirmPopup', {
//                     title: 'Kitchen Receipt Preview',
//                     body: receipt,
//                     confirmText: 'Print',
//                     cancelText: 'Close',
//                     confirm: () => this.printKitchenReceipt(receipt),
//                 });
//             }

//             printKitchenReceipt(receipt) {
//                 console.log("printKitchenReceipt().....")
//                 const popup = window.open('', '_blank');
//                 popup.document.write(receipt);
//                 popup.print();
//                 popup.close();
//             }
//         };

//     Registries.Component.extend(OrderWidget, PreviewKitchenReceiptOrderWidget);
//     return PreviewKitchenReceiptOrderWidget;
// });


odoo.define('metro_pos_kitchen_receipt.PreviewKitchenReceiptButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const { Gui } = require('point_of_sale.Gui');

    class PreviewKitchenReceiptButton extends PosComponent {

        constructor() {
            console.log("constructor() of PreviewKitchenReceiptButton....")
            super(...arguments);
            useListener('click', this.onClick);
            this._currentOrder = this.env.pos.get_order();
        }

        async onClick() {
            const order = this.env.pos.get_order();
            if (order.get_orderlines().length > 0) {
                console.log("order =",order)
                console.log("order.get_orderlines() =",order.get_orderlines())
                order.initialize_validation_date();
                await this.showTempScreen('KitchenReceiptScreen', { order });
            } else {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Nothing to Print'),
                    body: this.env._t('There are no order lines'),
                });
            }
        }

    }
    PreviewKitchenReceiptButton.template = 'PreviewKitchenReceiptButton';

    ProductScreen.addControlButton({
        component: PreviewKitchenReceiptButton,
        condition: function() {
            return this.env.pos.user.kitchen_screen_user === 'manager' &&
                   this.env.pos.config.restaurant_mode == 'full_service';
        },
    });

    Registries.Component.add(PreviewKitchenReceiptButton);

    return PreviewKitchenReceiptButton;
});
