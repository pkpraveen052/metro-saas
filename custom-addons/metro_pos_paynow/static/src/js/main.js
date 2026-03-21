/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
odoo.define('metro_pos_paynow.pos_customer_cart_screen', function(require) {
	"use strict";
	var models = require('point_of_sale.models');
	var core = require('web.core');
	var QWeb = core.qweb;
	var Session = require('web.Session');
	const TicketScreen = require('point_of_sale.TicketScreen');
	const PaymentScreen = require('point_of_sale.PaymentScreen');
	const ProductScreen = require('point_of_sale.ProductScreen');
	const ReceiptScreen = require('point_of_sale.ReceiptScreen');
	const HeaderButton = require('point_of_sale.HeaderButton');
    const Registries = require('point_of_sale.Registries');
	var SuperOrder = models.Order.prototype;
	var SuperPosModel = models.PosModel;
	var rpc = require('web.rpc')
    const NumberBuffer = require('point_of_sale.NumberBuffer');

    var _t = core._t;


    var PosProductScreen = ProductScreen =>
        class extends ProductScreen {

        constructor() {
            super(...arguments);
            var self= this
            self.env.pos.send_current_order_to_customer_facing_display();
        }

	}

	Registries.Component.extend(ProductScreen, PosProductScreen);
	Registries.Component.freeze();


    var PosResPaymentScreen = PaymentScreen =>
        class extends PaymentScreen {
			send_data_to_cart_screen(){
				var self = this
				var order = this.currentOrder
        		var line = order.selected_paymentline;
        		order.paynow_image_str = false
        		if (line !== undefined && line.payment_method.use_payment_terminal == 'paynow_static') {        			
        			// Get today's date
					const today = new Date();

					// Get tomorrow's date by adding one day (in milliseconds)
					const tomorrow = new Date(today);
					tomorrow.setDate(today.getDate() + 1);

					// Extract year, month, and day from the tomorrow date
					const year = tomorrow.getFullYear();
					const month = tomorrow.getMonth() + 1;
					const day = tomorrow.getDate();

					const expiry = `${year}/${day.toString().padStart(2, '0')}/${month.toString().padStart(2, '0')}`;

        			let qrcode = new PaynowQR({
                        uen: self.env.pos.company.l10n_sg_unique_entity_number,
                        amount : order.selected_paymentline.amount,
                        editable: false,
                        expiry: expiry,
                        refNumber: order.uid,
                        company:  self.env.pos.company.name
                    });
                    let QRstring = qrcode.output();

                    rpc.query({
                        route: '/pos/payment/paynow',
                        params: {
                            "string":QRstring,
                            "amount": order.selected_paymentline.amount,
                            "company": self.env.pos.company,
                            "refNumber": order.uid
                        }
                    }).then(function (data) {
                    	if (typeof data.img_str === 'string') {
                    		order.paynow_img_str = data.img_str
                    	} else {
                    		order.paynow_img_str = false
                    	}
                    	self.env.pos.send_current_order_to_customer_facing_display();
                    });

        		} else {
        			order.paynow_img_str = false
        			this.env.pos.send_current_order_to_customer_facing_display();
        		}
				
			}

        constructor() {
            super(...arguments);
            var self = this
            var paynowPresent = false
            for (const paymentLine of this.paymentLines) {
			    console.log('	paymentLine:', paymentLine);			    
			    if (paymentLine.payment_method && paymentLine.payment_method.use_payment_terminal && paymentLine.payment_method.use_payment_terminal == "paynow_static") {
			    	paynowPresent = true  
			    	break;              
			    }
			}
			if (paynowPresent == true) {
				setTimeout(function() {
				    console.log('This code runs after 1 second');
				    $('.button.paynow_qr').show();
				}, 1000);
				
			}
        }

        addNewPaymentLine({ detail: paymentMethod }) {
            var self = this
            if (paymentMethod.use_payment_terminal && paymentMethod.use_payment_terminal == "paynow_static") {
                $('.button.paynow_qr').show();

            } 
            return super.addNewPaymentLine(...arguments)         
        }

        deletePaymentLine(event) {
            var self = this;
            const { cid } = event.detail;
            const line = this.paymentLines.find((line) => line.cid === cid);

            var paynowPresent = false
            for (const paymentLine of this.paymentLines) {
			    if (line.cid !== paymentLine.cid && paymentLine.payment_method && paymentLine.payment_method.use_payment_terminal && paymentLine.payment_method.use_payment_terminal == "paynow_static") {
			    	paynowPresent = true  
			    	break;              
			    }
			}
			if (paynowPresent == false) {
				$('.button.paynow_qr').hide();
                this.currentOrder.paynow_img_str = false
                self.env.pos.send_current_order_to_customer_facing_display();
			}

			super.deletePaymentLine(event);
        }
	}

	Registries.Component.extend(PaymentScreen, PosResPaymentScreen);
	Registries.Component.freeze();

	models.PosModel = models.PosModel.extend({

	    send_current_order_to_customer_facing_display: function() {
	        console.log("\nCUSTOM  send_current_order_to_customer_facing_display() >>>>")
	        var self = this;
	        var current_order = self.get_order();
	        console.log(current_order.paynow_img_str)
	        this.render_html_for_customer_facing_display().then(function (rendered_html) {
	            if (self.env.pos.customer_display) {
	                var $renderedHtml = $('<div>').html(rendered_html);
	                $(self.env.pos.customer_display.document.body).html($renderedHtml.find('.pos-customer_facing_display'));
	                var orderlines = $(self.env.pos.customer_display.document.body).find('.pos_orderlines_list');
	                orderlines.scrollTop(orderlines.prop("scrollHeight"));
	            } else if (self.env.pos.proxy.posbox_supports_display) {
	                self.proxy.update_customer_facing_display(rendered_html);
	            }
	        });
	    },

	  })

});
// vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
