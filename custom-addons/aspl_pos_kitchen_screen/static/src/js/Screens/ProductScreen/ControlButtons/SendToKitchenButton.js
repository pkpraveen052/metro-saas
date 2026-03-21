odoo.define('aspl_pos_kitchen_screen.SendToKitchenButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class SendToKitchenButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
            this._currentOrder = this.env.pos.get_order();
            this._sending = false; // 🚀 NEW FLAG to prevent multiple sends
        }

        async onClick() {
            if (this._sending) {
                console.warn("Send to Kitchen already in progress...");
                return;
            }

            this._sending = true; // lock
            try {
                console.log("\nSendToKitchenButton() >>>>>");
                this._currentOrder.initialize_validation_date();
                if (this._currentOrder.is_empty()) {
                    this.showNotification('Please select product!!');
                    return;
                }

                this._currentOrder.set_send_to_kitchen(true);
                this._currentOrder.set_delete_product(false);

                //Metro changes started from here
                this._currentOrder.get_orderlines().forEach(line => {
                    if (!line.state) { // Only set if no state exists
                        line.set_line_state('Waiting');
                    }
                    line.set_send_to_kitchen(true);
                });
                //Metro changes ended

                let orderId = await this.env.pos.push_orders(this._currentOrder, { draft: true });
                this._currentOrder.set_server_id(orderId[0]);

                let orderLineIds = await this.orderLineIds(orderId[0]);
                console.log("\norderLineIds ===", orderLineIds);
                for (let line of this._currentOrder.get_orderlines()) {
                    for (let lineID of orderLineIds) {
                        if (line.cid === lineID.line_cid || line.server_id == lineID.server_id) {
                            line.set_server_id(lineID.id);
                            line.set_line_state(lineID.state);
                            line.set_send_to_kitchen(true); // Metro
                        }
                    }
                }

            } catch (err) {
                console.error("Error in SendToKitchen:", err);
            } finally {
                // release lock after small delay to avoid spam clicks
                setTimeout(() => { this._sending = false; }, 500);
            }
        }

        orderLineIds(orderId) {
            return this.rpc({
                model: 'pos.order.line',
                method: 'search_read',
                fields: ['line_cid', 'state'],
                domain: [['order_id', '=', orderId]]
            });
        }
    }

    SendToKitchenButton.template = 'SendToKitchenButton';

    ProductScreen.addControlButton({
        component: SendToKitchenButton,
        condition: function() {
            return this.env.pos.user.kitchen_screen_user === 'manager' &&
                   this.env.pos.config.restaurant_mode == 'full_service';
        },
    });

    Registries.Component.add(SendToKitchenButton);

    return SendToKitchenButton;
});
