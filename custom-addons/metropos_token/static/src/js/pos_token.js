odoo.define('metropos_token.models', function (require) {
    "use strict";
    
    var models = require('point_of_sale.models');
    var _super_order = models.Order.prototype;
    var rpc = require('web.rpc');

    models.load_fields("pos.order", ['pos_receipt_sequence']);

    models.Order = models.Order.extend({
        initialize: function (attributes, options) {
            _super_order.initialize.apply(this, arguments);
            
            // Log the initialization of the order
            console.log('Order initialized:', this);

            // Fetch the pos_receipt_sequence from the server if not already set
            if (this.pos.config.display_token_no == true && !this.pos_receipt_sequence) {
                var self = this;
                rpc.query({
                    model: 'pos.order',
                    method: 'get_next_token',
                    args: [],
                    context: {'session_id': self.pos_session_id}
                }).then(function (token) {
                    self.pos_receipt_sequence = token;
                }).catch(function (error) {
                    console.error('Error fetching token:', error);
                });
            }
        },
        export_as_JSON: function() {
            var json = _super_order.export_as_JSON.apply(this, arguments);
            // Include the pos_receipt_sequence in the exported order data
            json.pos_receipt_sequence = this.pos_receipt_sequence;
            return json;
        },
        export_for_printing: function() {
            var result = _super_order.export_for_printing.apply(this, arguments);
            // Include the pos_receipt_sequence in the printed order data
            result.pos_receipt_sequence = this.pos_receipt_sequence;
            return result;
        }
    });
});
