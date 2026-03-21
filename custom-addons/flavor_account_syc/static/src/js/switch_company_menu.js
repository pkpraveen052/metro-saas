odoo.define('flavor_account_syc.switch_company_menu', function (require) {
"use strict";

var core = require('web.core');
var session = require('web.session');
var ajax = require('web.ajax');

var _t = core._t;

var SwitchCompanyMenu = require('web.SwitchCompanyMenu')

SwitchCompanyMenu.include({

    rpc: function (url, params, options) {
        return ajax.jsonRpc(url, "call", params, options);
    },

    /**
     * @private
     * @param {MouseEvent|KeyEvent} ev
     * Overidden to add that rpc call
     */
    _onSwitchCompanyClick: function (ev) {
        if (ev.type == 'keydown' && ev.which != $.ui.keyCode.ENTER && ev.which != $.ui.keyCode.SPACE) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        var dropdownItem = $(ev.currentTarget).parent();
        var dropdownMenu = dropdownItem.parent();
        var companyID = dropdownItem.data('company-id');
        var allowed_company_ids = this.allowed_company_ids;
        if (dropdownItem.find('.fa-square-o').length) {
            // 1 enabled company: Stay in single company mode
            if (this.allowed_company_ids.length === 1) {
                if (this.isMobile) {
                    dropdownMenu = dropdownMenu.parent();
                }
                dropdownMenu.find('.fa-check-square').removeClass('fa-check-square').addClass('fa-square-o');
                dropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
                allowed_company_ids = [companyID];
            } else { // Multi company mode
                allowed_company_ids.push(companyID);
                dropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
            }
        }
        $(ev.currentTarget).attr('aria-pressed', 'true');
        // Metro code starts
        this.rpc('/web/session/write_flavor_grp', {'company_id': companyID}).then(function (result) {
            session.setCompanies(companyID, allowed_company_ids);
        });
        // // Metro code ends
    },
});

});