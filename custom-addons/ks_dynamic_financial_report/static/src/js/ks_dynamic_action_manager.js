odoo.define('ks_dynamic_financial_reports.ActionManager', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var framework = require('web.framework');
var session = require('web.session');

ActionManager.include({

    _ksDownloadExcelReport: function (action) {
        var self = this;
        framework.blockUI();
        return new Promise(function (resolve, reject) {
            session.get_file({
                url: '/ks_dynamic_financial_report',
                data: action.data,
                success: resolve,
                error: (error) => {
                    self.call('crash_manager', 'rpc_error', error);
                    reject();
                },
                complete: framework.unblockUI,
            });
        });
    },

    _handleAction: function (action, options) {
        if (action.type === 'ir_actions_account_report_download') {
            return this._ksDownloadExcelReport(action, options);
        }
        return this._super.apply(this, arguments);
    },
});

});
