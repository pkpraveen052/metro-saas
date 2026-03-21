odoo.define('aspl_pos_kitchen_screen.models', function (require) {
"use strict";

     var models = require('point_of_sale.models');
     var _super_Order = models.Order.prototype;

    models.load_fields("res.users", ['kitchen_screen_user','pos_category_ids','is_delete_order_line','delete_order_line_reason']);

    models.PosModel.prototype.models.push({
        model:  'remove.product.reason',
        fields: ['name', 'description'],
        loaded: function(self,remove_product_reason){
            self.remove_product_reason = remove_product_reason;
        },
    });

    var posmodel_super = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: function(attr, options) {
            posmodel_super.initialize.call(this,attr,options);
            this.kitchenScreenData = [];
        },
        load_server_data:  function () {
            var self = this;
            return posmodel_super.load_server_data.apply(this, arguments).then(function () {
                var records = self.rpc({
                    model: 'pos.order',
                    method: 'broadcast_order_data',
                    args: [false]
                });
                return records.then(function (records) {
                    self.kitchenScreenData = records;
                });
            });
        },
        set_kitchen_screen_data: function(data){
            this.kitchenScreenData = data;
            this.trigger('change',this);
        },
        get_kitchen_screen_data: function(){
            return this.kitchenScreenData;
        },
    })

    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function(attr, options){
            _super_order.initialize.call(this,attr,options);
            this.cancel_product_reason = [];
            this.delete_product = false;
            this.send_to_kitchen = this.send_to_kitchen || false;
            this.server_id = this.server_id || false;
            this.order_state = this.order_state || 'Start';
        },
        set_send_to_kitchen: function(flag){
            this.send_to_kitchen = flag;
            this.trigger('change',this);
        },
        get_send_to_kitchen: function(){
            return this.send_to_kitchen;
        },
        set_server_id: function(server_id){
            this.server_id = server_id;
        },
        get_server_id: function(server_id){
            return this.server_id;
        },
        set_order_status: function(status){
            this.order_state = status;
        },
        get_order_status: function(){
            return this.order_state;
        },
        set_cancel_product_reason:function(cancel_product_reason){
            this.cancel_product_reason = cancel_product_reason;
            this.trigger('change',this);
        },
        get_cancel_product_reason:function(){
            return this.cancel_product_reason;
        },
        set_delete_product:function(delete_product){
            this.delete_product = delete_product;
            this.trigger('change',this);
        },
        get_delete_product:function(){
            return this.delete_product;
        },
        init_from_JSON: function(json) {
            _super_order.init_from_JSON.apply(this,arguments);
            this.cancel_product_reason = json.cancel_product_reason;
            this.send_to_kitchen = json.send_to_kitchen;
            this.server_id = json.server_id;
            this.order_state = json.order_state;
        },
        export_as_JSON: function() {
            var json = _super_order.export_as_JSON.call(this);
            json.cancel_product_reason = this.get_cancel_product_reason();
            json.delete_product = this.get_delete_product();
            json.server_id = this.server_id;
            json.send_to_kitchen = this.get_send_to_kitchen() ? this.send_to_kitchen : false;
            json.order_state = this.order_state;
            return json;
        },
    });
    var _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({

        initialize: function(attr, options){
            _super_orderline.initialize.call(this,attr,options);
            this.state = this.state || null; // Metro changes 'Waiting' to null value. 
            this.server_id = this.server_id || false;
            this.line_cid = this.cid || false;
            this.send_to_kitchen = this.send_to_kitchen || false; // Metro
        },
        set_send_to_kitchen: function(flag){ // Metro
            this.send_to_kitchen = flag;
            this.trigger('change',this);
        },
        get_send_to_kitchen: function(){ // Metro
            return this.send_to_kitchen;
        },
        clone: function(){
            var orderline = _super_orderline.clone.call(this);
            orderline.state = this.state;
            orderline.server_id = this.server_id;
            orderline.line_cid = this.line_cid;
            return orderline;
        },
        can_be_merged_with: function(orderline) {
            if (this.state != orderline.state){
                return false
            }else{
                return _super_orderline.can_be_merged_with.apply(this,arguments);
            }
        },
        set_server_id: function(server_id){
            this.server_id = server_id;
        },
        get_server_id: function(server_id){
            return this.server_id;
        },
        init_from_JSON: function(json) {
            _super_orderline.init_from_JSON.apply(this,arguments);
            this.server_id = json.server_id;
            this.line_cid = json.line_cid;
            this.state = json.state;
            this.send_to_kitchen = json.send_to_kitchen; // Metro
        },
        export_as_JSON: function() {
            var json = _super_orderline.export_as_JSON.call(this);
            json.state = this.get_line_state();
            json.server_id = this.server_id;
            json.line_cid = this.line_cid;
            json.send_to_kitchen = this.get_send_to_kitchen() ? this.send_to_kitchen : false; // Metro
            return json;
        },
        // set_line_state:function(state){
        //     this.state = state;
        //     this.trigger('change',this);
        // },
        set_line_state: function (state) {
            this.state = state;
            // 🔒 Do not trigger change (which saves) when the order is finalized
            const parentOrder = this.order;
            if (parentOrder && !parentOrder.finalized) {
                this.trigger('change', this);
            }
        },
        get_line_state:function(){
            return this.state;
        },
    });

});
