odoo.define('aspl_pos_kitchen_screen.Chrome', function(require) {
    'use strict';

    const Chrome = require('point_of_sale.Chrome');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const core = require('web.core');
    var rpc = require('web.rpc');
    const { Gui } = require('point_of_sale.Gui');
    const { useListener } = require('web.custom_hooks');

    require('bus.BusService');
    var bus = require('bus.Longpolling');
    var cross_tab = require('bus.CrossTab').prototype;
    var session = require('web.session');


    const AsplKitchenChrome = (Chrome) =>
        class extends Chrome {
            constructor(){
                super(...arguments);
                useListener('click-kitchen-screen', this._clickKitchenScreen);
                this.state.orderData = [];
                this.state.lastScreen = '';
            }
            showScreen(name, props = {}) {
                if (this.env.pos.user.kitchen_screen_user === 'cook' && name !== 'KitchenScreen') {
                    // Prevent switching away from KitchenScreen
                    return;
                }
                super.showScreen(name, props);
            }
            get isTicketButtonShown(){
                return this.mainScreen.name !== 'KitchenScreen';
            }
            get isKitchenScreen(){
                return this.mainScreen.name === 'KitchenScreen';
            }
            get startScreen(){
                if(this.env.pos.user.kitchen_screen_user === 'cook'){
                    return { name: 'KitchenScreen'};
                }else{
                    return super.startScreen;
                }
            }
            get isManager(){
                return this.env.pos.user.kitchen_screen_user === 'manager';
            }
            async start(){
                await super.start();
                this.state.orderData = await this.env.pos.kitchenScreenData;
                this._pollData();
            }
            _pollData(){
                this.env.services['bus_service'].updateOption('pos.order.line',session.uid);
                this.env.services['bus_service'].onNotification(this,this._onNotification);
                this.env.services['bus_service'].startPolling();
                cross_tab._isRegistered = true;
                cross_tab._isMasterTab = true;
            }
            _onNotification(notifications){
                var self = this;
                for (var item of notifications) {
                    if(item[1].screen_display_data){
                        if(item[1].new_order){
                            Gui.playSound('bell');
                        }
                        var order_data = [];
                        var allOrderLines = {};
                        let categoryList = this.env.pos.user.pos_category_ids;
                        _.each(item[1].screen_display_data, function(order){
                            let localTime =  moment.utc(order.order_time).toDate();
                            order['order_time'] =  moment(localTime).format('HH:mm:ss');
                            var order_line_data = [];
                            _.each(order.order_lines,function(line){
                                allOrderLines[line.id] = line.state;
                                let domain = _.contains(['Done','Cancel'], line.state);
                                if(!domain && _.contains(categoryList, line.categ_id) && !item[1].manager){
                                    order_line_data.push(line);
                                }else if(!domain && item[1].manager){
                                    order_line_data.push(line);
                                }
                            });
                            order.order_lines = order_line_data;
                            order['display'] = true;
                            if(order.order_lines.length > 0){
                                order_data.push(order);
                            }
                        });
                    }
                    this.state.orderData = order_data;
                    if(allOrderLines){
                        self.updatePosScreenOrder(allOrderLines);
                    }
                }
            }
            // updatePosScreenOrder(order_line_data){
            //     if(this.env.pos.get_order_list().length > 0){
            //         var collection_orders = this.env.pos.get_order_list()[0].collection.models;
            //         for (let i = 0; i < collection_orders.length; i++){
            //             let collectionOrder = collection_orders[i];
            //             if(collectionOrder.server_id){
            //                 for(let line of collectionOrder.orderlines.models){
            //                     if(line && line.server_id && order_line_data[line.server_id]){
            //                         line.set_line_state(order_line_data[line.server_id]);
            //                     }
            //                 }
            //             }
            //         }
            //     }
            // }
            updatePosScreenOrder(order_line_data){
                // Nothing to do if no orders or no payload
                if (!order_line_data || this.env.pos.get_order_list().length === 0) return;

                // In Restaurant mode get_order_list() returns orders of current table;
                // we still iterate through the internal collection to touch each one.
                const collection_orders = this.env.pos.get_order_list()[0]?.collection?.models || [];
                for (let i = 0; i < collection_orders.length; i++){
                    const collectionOrder = collection_orders[i];

                    // Never touch finalized orders
                    if (!collectionOrder || collectionOrder.finalized) continue;

                    if (collectionOrder.server_id){
                        for (let line of collectionOrder.orderlines.models){
                            // Also guard each line in case of race conditions
                            if (!line || !line.server_id) continue;

                            const newState = order_line_data[line.server_id];
                            if (typeof newState !== 'undefined' && line.get_line_state() !== newState){
                                try {
                                    // This will not save when order is finalized (guarded in set_line_state)
                                    line.set_line_state(newState);
                                } catch (e) {
                                    // Extra safety: never let a single line break the bus update loop
                                    console.warn('Skip updating line state due to error:', e);
                                }
                            }
                        }
                    }
                }
            }

            async _closePos(){
                if(this.env.pos.user.kitchen_screen_user === 'cook'){
                    this.state.uiState = 'CLOSING';
                    this.loading.skipButtonIsShown = false;
                    this.setLoadingMessage(this.env._t('Closing ...'));
                    window.location = '/web/session/logout';
                }
                else{
                    await super._closePos();
                }
            }
            async _clickKitchenScreen(){
                if(this.mainScreen.name === 'KitchenScreen'){
                    this.showScreen(this.start.lastScreen);
                }else{
                    this.start.lastScreen = this.mainScreen.name;
                    this.showScreen('KitchenScreen', await this.env.pos.kitchenScreenData);
                }
            }
        };

    Registries.Component.extend(Chrome, AsplKitchenChrome);

    return Chrome;
});
