odoo.define('metroerp_ocr.ocr_bill_warning', function (require) {
"use strict";




var FormController = require('web.FormController');
var core = require('web.core');
    var Dialog = require('web.Dialog');



    FormController.include({
        start: function () {

            var self = this;

            return this._super.apply(this, arguments).then(function () {
            const showWarning = self.initialState && self.initialState.context && self.initialState.context.show_ocr_warning;
            const modelName = self.modelName;
            if (showWarning && modelName === 'account.move'){
                alert("⚠️ Warning: The total amount extracted from the invoice does not match the total on the created vendor bill. Please review and verify the bill details before validation.");
            }
            });
        }
    });
});