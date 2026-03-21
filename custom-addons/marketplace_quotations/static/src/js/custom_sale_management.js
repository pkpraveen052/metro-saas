odoo.define('marketplace_quotations.custom_sale_management', function (require) {
"use strict";

var publicWidget = require('web.public.widget');

publicWidget.registry.SaleUpdateLineButton.include({

    /**
     * @override
     */
    async start() {
        console.log("CUSTOM sale_management ...... start()")
        await this._super(...arguments);
        this.orderDetail = this.$el.find('table#sales_order_table').data();
        this.elems = this._getUpdatableElements();
        var orderAmountTotal = $('[data-id="total_untaxed"]').find('span, span').text()
        if (parseFloat(orderAmountTotal) <= 0.0) {
            var acceptSignBtn = $('[data-target="#modalaccept"]')
            console.log("acceptSignBtn ==",acceptSignBtn)
            acceptSignBtn.css({
              "display": "none"
            });
        }
    },

    /**
     * Processes data from the server to update the UI
     *
     * @private
     * @param {Object} data: contains order and line updated values
     */
    _updateOrderValues(data) {
        console.log("CUSTOM _updateOrderValues() >>> data ==",data)
        if (data.order_amount_total > 0.0) {
            var acceptSignBtn = $('[data-target="#modalaccept"]')
            console.log("acceptSignBtn ==",acceptSignBtn)
            acceptSignBtn.css({
              "display": ""
            });
        } else if (data.order_amount_total <= 0.0) {
            var acceptSignBtn = $('[data-target="#modalaccept"]')
            console.log("acceptSignBtn ==",acceptSignBtn)
            acceptSignBtn.css({
              "display": "none"
            });
        }
        let orderAmountTotal = data.order_amount_total,
            orderAmountUntaxed = data.order_amount_untaxed,
            orderAmountUndiscounted = data.order_amount_undiscounted,
            $orderTotalsTable = $(data.order_totals_table);
        if (orderAmountUntaxed !== undefined) {
            this.elems.$orderAmountUntaxed.text(orderAmountUntaxed);
        }

        if (orderAmountTotal !== undefined) {
            this.elems.$orderAmountTotal.text(orderAmountTotal);
        }

        if (orderAmountUndiscounted !== undefined) {
            this.elems.$orderAmountUndiscounted.text(orderAmountUndiscounted);
        }
        if ($orderTotalsTable.length) {
            this.elems.$orderTotalsTable.find('table').replaceWith($orderTotalsTable);
        }
    },

});

});