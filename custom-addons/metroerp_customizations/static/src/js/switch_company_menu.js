odoo.define('metroerp_customizations.switch_company_menu', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');

var _t = core._t;

var SwitchCompanyMenu = require('web.SwitchCompanyMenu')

SwitchCompanyMenu.include({
    /**
     * @override
     * Overidden to hide the checkboxes on the Multi-company selection for the Users other than Admins
     */
    willStart: function () {
        var self = this;
        this.hide_checkboxes = session.is_system
        this.allowed_company_ids = String(session.user_context.allowed_company_ids)
                                    .split(',')
                                    .map(function (id) {return parseInt(id);});
        this.user_companies = session.user_companies.allowed_companies;
        this.current_company = this.allowed_company_ids[0];
        this.current_company_name = _.find(session.user_companies.allowed_companies, function (company) {
            return company[0] === self.current_company;
        })[1];
        return this._super.apply(this, arguments);
    },
});

});