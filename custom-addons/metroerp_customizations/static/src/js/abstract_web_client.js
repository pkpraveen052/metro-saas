odoo.define('metroerp_customizations.web_client', function (require) {
"use strict";
    // var WebClient = require('web.WebClient');
    var AbstractWebClient = require('web.AbstractWebClient');
    var KeyboardNavigationMixin = require('web.KeyboardNavigationMixin');
    var core = require('web.core');
    var concurrency = require('web.concurrency');
    var config = require('web.config');
    var session = require('web.session');
    var utils = require('web.utils');
    var rpc = require('web.rpc');
    var _t = core._t;
    var new_title = "";

    const env = require('web.env');

    AbstractWebClient.include({
        
        init: function(parent) {
            odoo.isReady = false;
            this.client_options = {};
            this._super(parent);
            KeyboardNavigationMixin.init.call(this);
            this.origin = undefined;
            this._current_state = null;
            this.menu_dp = new concurrency.DropPrevious();
            this.action_mutex = new concurrency.Mutex();
            self = this;
            rpc.query({
                model: "res.config.settings",
                method: 'get_debranding_settings',
            }, {
                shadow: true
            }).then(function(debranding_settings){
                odoo.debranding_settings = debranding_settings;
                self.set('title_part', {"zopenerp": odoo.title_brand && odoo.title_brand.trim() || ''});
                new_title = debranding_settings.title_brand;
            });
            self.env = env;
            self.env.bus.on('set_title_part', this, this._onSetTitlePart);
        },


        start: function () {
            KeyboardNavigationMixin.start.call(this);
            var self = this;
            this.$el.toggleClass('o_touch_device', config.device.touch);
            this.on("change:title_part", this, this._title_changed);
            this._title_changed();
            var state = $.bbq.getState();
            var current_company_id = session.user_companies.current_company[0]
            if (!state.cids) {
                state.cids = utils.get_cookie('cids') !== null ? utils.get_cookie('cids') : String(current_company_id);
            }
            const cids = Array.isArray(state.cids) ? state.cids[0] : state.cids;
            let stateCompanyIDS = cids.split(',').map(cid => parseInt(cid, 10));
            var userCompanyIDS = _.map(session.user_companies.allowed_companies, function(company) {return company[0]});
            if (!_.isEmpty(_.difference(stateCompanyIDS, userCompanyIDS))) {
                state.cids = String(current_company_id);
                stateCompanyIDS = [current_company_id]
            }
            session.user_context.allowed_company_ids = stateCompanyIDS;
            $.bbq.pushState(state);
            self._rpc({
                model: "res.config.settings",
                method: 'get_debranding_settings',
            }, {
                shadow: true
            }).then(function(debranding_settings){
                odoo.debranding_settings = debranding_settings;
                $("link[type='image/x-icon']").attr('href', odoo.debranding_settings.favicon_url)
            });

            return session.is_bound
                .then(function () {
                    self.$el.toggleClass('o_rtl', _t.database.parameters.direction === "rtl");
                    self.bind_events();
                    return Promise.all([
                        self.set_action_manager(),
                        self.set_loading()
                    ]);
                }).then(function () {
                    if (session.session_is_valid()) {
                        return self.show_application();
                    } else {
                        return Promise.resolve();
                    }
                });
        },

        _title_changed: function () {
            var parts = _.sortBy(_.keys(this.get("title_part")), function (x) { return x; });
            var tmp = new_title;
            _.each(parts, function (part) {
                var str = this.get("title_part")[part];
                if (str) {
                    tmp = tmp ? str + " - " + tmp : str;
                }
            }, this);
            document.title = tmp;
        },
    
    });
});