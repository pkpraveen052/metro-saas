odoo.define('sh_pos_transaction_charges.paymentscreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    const ShPaymentScreenScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            mounted(){
                var self = this;
                $('.back').click(function (event) {
                    const selected_ordelrine = self.env.pos.get_order().get_selected_orderline()
                    if (selected_ordelrine && selected_ordelrine.product.sh_is_credit_card_charge){
                        self.env.pos.get_order().remove_orderline(selected_ordelrine)
                    }
                })
            }
            async addNewPaymentLine({ detail: paymentMethod }) {
                var self = this;
                if (paymentMethod.sh_pos_enable_transaction_cherge && paymentMethod.sh_pos_transaction_charge) {
                    var product;
                    await _.each(self.env.pos.db.product_by_id, function (each_product) {
                        if (each_product.sh_is_credit_card_charge){
                            product = each_product
                        }
                    })
                    var sh_BankCharge = 0.00;
                    if (paymentMethod.sh_pos_transaction_charge && paymentMethod.sh_pos_transaction_charge == "percentage"){
                        sh_BankCharge = (self.currentOrder.get_due() * paymentMethod.sh_pos_card_charge) / 100
                    }else{
                        sh_BankCharge = paymentMethod.sh_pos_card_charge
                    }
                    if (product && self.env.pos.get_order().get_selected_orderline() && !self.env.pos.get_order().get_selected_orderline().product.sh_is_credit_card_charge){
                        await self.env.pos.get_order().add_product(product, {
                            price: sh_BankCharge
                        })
                    }
                }
                return super.addNewPaymentLine(...arguments)
            }
            deletePaymentLine(event) {
                var self = this;
                const { cid } = event.detail;
                const selected_paymentline = this.paymentLines.find((line) => line.cid === cid);
                const selected_ordelrine = this.env.pos.get_order().get_selected_orderline()
                
                if (selected_paymentline && selected_paymentline.payment_method && selected_paymentline.payment_method.id && selected_paymentline.payment_method.sh_pos_enable_transaction_cherge && selected_paymentline.payment_method.sh_pos_card_charge) {
                    self.env.pos.get_order().remove_orderline(selected_ordelrine)
                }
                super.deletePaymentLine(event)
            }
        }

    Registries.Component.extend(PaymentScreen, ShPaymentScreenScreen)

})
