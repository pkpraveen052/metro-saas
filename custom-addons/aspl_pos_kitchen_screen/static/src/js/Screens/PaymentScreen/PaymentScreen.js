odoo.define('aspl_pos_kitchen_screen.PaymentScreen', function(require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen')
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');


    const PaymentScreenInh = PaymentScreen =>
        class extends PaymentScreen {
            constructor() {
                super(...arguments);
            }
            async _finalizeValidation() {
                if(this.env.pos.config.restaurant_mode == 'quick_service'){
                    this.currentOrder.set_send_to_kitchen(true);
                }
                await super._finalizeValidation()
            }
        };

    Registries.Component.extend(PaymentScreen, PaymentScreenInh);

    return PaymentScreen;
});
