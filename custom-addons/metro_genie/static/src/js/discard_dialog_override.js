odoo.define('metro_genie.discard_dialog_override', function (require) {
    "use strict";

    const BasicController = require('web.BasicController');
    const Dialog = require('web.Dialog');
    const core = require('web.core');
    const _t = core._t;

    BasicController.include({
        canBeDiscarded: function (recordID) {
            var self = this;
            if (this.model.loadParams.modelName === "metro.genie.dashboard") {
            // If not dirty, return false; if dirty, discard silently
                return Promise.resolve(!this.isDirty(recordID) ? false : true);
            }

            if (this.discardingDef) {
                // discard dialog is already open
                return this.discardingDef;
            }
            if (!this.isDirty(recordID)) {
                return Promise.resolve(false);
            }

            var message = _t("The record has been modified, your changes will be discarded. Do you want to proceed?");
            this.discardingDef = new Promise(function (resolve, reject) {
                var dialog = Dialog.confirm(self, message, {
                    title: _t("Warning"),
                    confirm_callback: () => {
                        resolve(true);
                        self.discardingDef = null;
                    },
                    cancel_callback: () => {
                        reject();
                        self.discardingDef = null;
                    },
                });
                dialog.on('closed', self.discardingDef, reject);
            });
            return this.discardingDef;
        }
    });
});
