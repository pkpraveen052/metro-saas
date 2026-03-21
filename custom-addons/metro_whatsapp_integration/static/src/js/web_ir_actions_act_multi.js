odoo.define('metro_whatsapp_integration.action_send_whatsapps', function (require) {
    "use strict";
    console.log('yyyyyyyyyyyyyyy')

    var ActionManager = require('web.ActionManager');
    console.log('yyyyyyyyyyyyyyy')
    ActionManager.include({
        ir_actions_act_url: function (action, options) {
            var self = this;
            if (action.target === 'new' && action.type === 'ir.actions.act_url') {
                var openedWindow = window.open(action.url, '_blank');
                if (openedWindow) {
                    openedWindow.onload = function () {
                        openedWindow.focus();
                        // Close the current window after opening the URL
                        window.close();
                    };
                }
            } else {
                return this._super.apply(this, arguments);
            }
        },
    });
});
