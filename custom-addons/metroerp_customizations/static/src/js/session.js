odoo.define('metroerp_customizations.session', function (require) {
"use strict";

var ajax = require('web.ajax');
var concurrency = require('web.concurrency');
var core = require('web.core');
var mixins = require('web.mixins');
var utils = require('web.utils');

var _t = core._t;
var qweb = core.qweb;

var Session = require('web.Session')

Session.include({
    /**
     * @override
     * Overidden to reload to the action of the current url to avoid the Access Errors
     */
    setCompanies: function (main_company_id, company_ids) {
        var hash = $.bbq.getState()
        hash.cids = company_ids.sort(function(a, b) {
            if (a === main_company_id) {
                return -1;
            } else if (b === main_company_id) {
                return 1;
            } else {
                return a - b;
            }
        }).join(',');
        utils.set_cookie('cids', hash.cids || String(main_company_id));
        $.bbq.pushState({'cids': hash.cids}, 0);
        // Metro Code starts
        var currentUrl = window.location.href
        console.log("currentUrl ===",currentUrl)
        console.log("this ===",this)

        var regex = /^(https?:\/\/[^/]+)/i;
        var mainUrl = currentUrl.match(regex)[1];

        var actionRegex = /action=(\d+)/;
        var actionMatch = currentUrl.match(actionRegex);

        if (actionMatch) {
            const actionValue = actionMatch[1];
            var newUrl = mainUrl + '/web#action=' + actionValue
            console.log("newUrl:", newUrl);
            window.location.href = newUrl
            window.location.reload();
        } else {
            window.location.reload();
        }
        // Metro Code ends
    },
});

});