odoo.define('aspl_pos_kitchen_screen.ProductScreen', function(require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen')
    const PosComponent = require('point_of_sale.PosComponent');
    const ControlButtonsMixin = require('point_of_sale.ControlButtonsMixin');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const { onChangeOrder, useBarcodeReader } = require('point_of_sale.custom_hooks');
    const { useState } = owl.hooks;


    const AsplKitchenProductScreen = ProductScreen =>
        class extends ProductScreen {
            constructor() {
                super(...arguments);
                useListener('set-order-type-mode', this._setOrderTypeMode);
            }
            _setOrderTypeMode(event) {
                const { mode } = event.detail;
                this.state.orderTypeMode = mode;
            }
            async _setValue(val){
                let line = this.currentOrder.get_selected_orderline();
                if(line === undefined){
                    super._setValue(...arguments);
                    return;
                }
                if (line.state === 'Waiting' || !line.state) {
                    super._setValue(...arguments);
                } else if (['Preparing', 'Deliver', 'Done'].includes(line.state)) {
                    alert(this.env._t('You cannot edit this order line in its current state!'));
                    return;
                } else {
                    super._setValue(...arguments);
                }
            }
        };

    Registries.Component.extend(ProductScreen, AsplKitchenProductScreen);

    return ProductScreen;
});
