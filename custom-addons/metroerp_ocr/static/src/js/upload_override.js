odoo.define('metroerp_ocr.upload.override', function (require) {
"use strict";

const UploadBillMixin = require('account.upload.bill.mixin');

UploadBillMixin._onUpload = function (event) {
    const self = this;

    // Open your custom wizard instead of file uploader
    this.do_action({
        type: 'ir.actions.act_window',
        name: 'Upload Bill',
        res_model: 'invoice.upload.wizard',
        view_mode: 'form',
        views: [[false, 'form']],
        target: 'new',
        context: this.initialState.context,
    });
};

});