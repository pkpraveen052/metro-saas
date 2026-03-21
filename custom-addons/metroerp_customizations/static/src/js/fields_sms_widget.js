odoo.define('metroerp_customizations.sms_widget', function (require) {
"use strict";

var core = require('web.core');
var SmsWidget = require('sms.sms_widget')
var _t = core._t;

SmsWidget.include({
    /**
    * Overidden _renderIAPButton() to hide the <a/> sms info icon
    */
    _renderIAPButton: function () {
        return $('<a>', {
            'href': 'https://iap-services.odoo.com/iap/sms/pricing',
            'target': '_blank',
            'title': _t('SMS Pricing'),
            'aria-label': _t('SMS Pricing'),
            'class': 'fa fa-lg fa-info-circle',
            'style': 'display:none'
        });
    },
});

});