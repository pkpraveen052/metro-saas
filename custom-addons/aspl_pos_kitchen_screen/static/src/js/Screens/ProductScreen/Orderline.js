odoo.define('aspl_pos_kitchen_screen.Orderline', function(require) {
    'use strict';

    const OrderLine = require('point_of_sale.Orderline');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    const OrderLineInherit = OrderLine =>
        class extends OrderLine {
            constructor() {
                super(...arguments);
                this._currentOrder = this.env.pos.get_order();
            }
            // Metro Method
            get isSentToKitchen() {
                console.log("\nisSentToKitchen() >>>",this)
                return this.props.line.get_send_to_kitchen();
            }
            get addStateColor(){
                if(this.props.line.state == 'Waiting'){
                    return '#555555';
                }else if(this.props.line.state == 'Preparing'){
                    return '#f44336';
                }else if(this.props.line.state == 'Delivering'){
                    return '#795548';
                //Below is Metro Line    
                }else{
                    return '';
                }
            }
            async DeleteLineFromOrder(line){
                if (this.env.pos.user.delete_order_line_reason){
                    const loadedReason = this.env.pos.remove_product_reason;
                    const reasonLinesForRemove = []
                    for (let reasonPos of loadedReason) {
                        reasonLinesForRemove.push({
                            id: reasonPos.id,
                            label: reasonPos.name,
                            item: reasonPos,
                        });
                    }
                    const { confirmed, payload } = await this.showPopup('SelectionPopup',
                                                    {title: this.env._t('Select Reason'), list: reasonLinesForRemove});
                    if (confirmed) {
                        const reason = Object.assign({},
                                {'product': line.product.id, 'reason_id': payload.id, 'description': ''});
                        if (payload.description){
                            const { confirmed, payload: inputNote } = await this.showPopup('TextAreaPopup', {
                                title: this.env._t('Add Reason'),
                            });
                            if (confirmed) {
                                reason['description'] = inputNote;
                            }
                        }
                        this._currentOrder.set_cancel_product_reason(reason);
                        this._currentOrder.set_delete_product(true);
                        line.set_quantity('remove');
                        await this.env.pos.push_orders(this._currentOrder, {draft:true});
                    }
                }
            }
        };

    Registries.Component.extend(OrderLine, OrderLineInherit);

    return OrderLine;
});
