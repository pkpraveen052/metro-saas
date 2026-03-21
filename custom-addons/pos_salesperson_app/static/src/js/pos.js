odoo.define('pos_reserve_order_app.pos_reserve_order', function(require) {
	"use strict";

	const { onChangeOrder } = require('point_of_sale.custom_hooks');
	const PosComponent = require('point_of_sale.PosComponent');
	const Registries = require('point_of_sale.Registries');
	const Orderline = require('point_of_sale.Orderline');
	const OrderWidget = require('point_of_sale.OrderWidget');
	const models = require('point_of_sale.models');
	const { useState, useRef } = owl.hooks;
	const { useListener } = require('web.custom_hooks');
	const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
	var core = require('web.core');
	var QWeb = core.qweb;
	var _t = core._t;


	var OrderlineSuper = models.Orderline;
	models.Orderline = models.Orderline.extend({
		initialize: function (attr, options) {
            OrderlineSuper.prototype.initialize.apply(this, arguments);
            this.sales_person_id = false;  // Initialize the sales person ID
            this.sales_person_name = '';    // Initialize the sales person name
            this.image = '';
        },
        set_sales_person: function (sales_person_id, user_name) {
            this.sales_person_id = sales_person_id;
            this.sales_person_name = user_name || ''; // Set the sales person name
            this.image = sales_person_id ? `/web/image?model=res.users&field=image_128&id=${sales_person_id}` : '';
            this.trigger('change', this);
        },
        export_as_JSON: function () {
            var loaded = OrderlineSuper.prototype.export_as_JSON.call(this);
            loaded.sales_person_id = this.sales_person_id || false;  // Correctly assign the sales person ID
            loaded.sales_person_name = this.sales_person_name || '';  // Include the sales person's name
            return loaded;
        },
	});

	const PosSalesOrderline = (Orderline) =>
		class extends Orderline{
			constructor() {
				super(...arguments);
			}
			addUser(){
				var self = this;
				var sales_user = {};
				for (var i = 0; i < self.env.pos.users.length; i++){
					sales_user[self.env.pos.users[i].id] = self.env.pos.users[i].name
				}
				var current_line = this.props.line
				this.showPopup('SalesPersonPopupWidget', {
					title: this.env._t('Sales Person'),
					startingValue: sales_user,
					list: current_line,
				});
			}
			removeUser(){
				var self = this;
				var order = this.env.pos.get_order();
				this.trigger('select-line', { orderline: this.props.line });
				order.get_selected_orderline().set_sales_person(false, false);
				var add_user = $('.add_salesuser');
				var info_user = $('.user_info');
				for (var i = 0; i < add_user.length; i++){
					if ($(add_user[i]).find('.user_add_id').val() == this.props.line.id){
						$(add_user[i]).show();
					}
				}
				for (var i = 0; i < info_user.length; i++){
					if ($(info_user[i]).find('.user_info_id').val() == this.props.line.id){
						$(info_user[i]).hide();
					}
				}
			}
		};
	Registries.Component.extend(Orderline, PosSalesOrderline);

	class SalesPersonPopupWidget extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.sales_persons = this.env.pos.users; // Assuming you have users loaded
        }
        client_click_event(event) {
            const selected_user_id = parseInt($(event.currentTarget).data('id'));
            const selected_user_name = $(event.currentTarget).data('name');

            const order = this.env.pos.get_order();
            const orderline = order.get_selected_orderline();
            if (orderline) {
                orderline.set_sales_person(selected_user_id, selected_user_name); // Set salesperson on the selected order line
                this.trigger('close-popup');
            }
        }
        cancel() {
            this.trigger('close-popup');
        }
    }

    SalesPersonPopupWidget.template = 'SalesPersonPopupWidget';

    Registries.Component.add(SalesPersonPopupWidget);

    return {
        SalesPersonPopupWidget,
    }
});
