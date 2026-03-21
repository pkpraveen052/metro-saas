odoo.define('metro_genie.textarea_autoresize', function (require) {
    'use strict';

    // Attach the autoResize function to the global window object
    window.autoResize = function (textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = (textarea.scrollHeight) + 'px';
    };

});


odoo.define('metro_genie.genie_action_autocomplete_text', function (require) {
    "use strict";

    const fieldRegistry = require('web.field_registry');
//    const FieldChar = require('web.basic_fields').FieldChar;
    const FieldText = require('web.basic_fields').FieldText;
    const rpc = require('web.rpc');

    const GenieActionAutocompleteText = FieldText.extend({
        events: _.extend({}, FieldText.prototype.events, {
            'input': '_onInput',
            'keydown': '_onKeydown',
            'blur': '_onBlur',
        }),

        init: function () {
            this._super.apply(this, arguments);
            this.suggestions = [];
            this.filtered = [];
            this.selectedIndex = -1;
        },

        start: function () {
            const self = this;
            this.$input = this.$el.find('textarea');
            console.log('strat function')
            this.dropdown = $('<ul>', {
                class: 'dropdown-suggestions',
                css: {
                    position: 'absolute',
                    background: '#fff',
                    border: '1px solid #ccc',
                    zIndex: 9999,
                    listStyle: 'none',
                    padding: '5px',
                    margin: 0,
                    maxHeight: '200px',
                    overflowY: 'auto',
                    width: this.$input.outerWidth()
                }
            }).hide();

            $('body').append(this.dropdown);

            // 👇 Send icon click handler
            // ✅ Send icon click handler
//            $(document).on('click', '#genie-send-button', function () {
//                const inputVal = self.$input.val().toLowerCase();
//                console.log('Send Button Clicked. Input:', inputVal);
//
//                const matched = self.suggestions.find(s => s.name.toLowerCase() === inputVal);
//                if (matched) {
//                    // ⚠️ DO NOT use _setValue to avoid discard warning
//                    self.$input.val(matched.name);  // Just update visible input
//                    self.dropdown.hide();
//                    self._navigateToAction(matched.action_xml_id);  // Navigate directly
//                } else {
//                    alert("No matching action found for: " + inputVal);
//                }
//            });

            return Promise.all([
                this._super(...arguments),
                this._rpc({
                    model: 'metro.genie.suggestion',
                    method: 'search_read',
                    kwargs: {
                        domain: [],
                        fields: ['name', 'action_id', 'menu_id', 'view_types', 'model'],
                        limit: 10,
                    },
                }),
            ]).then(([res, data]) => {
                console.log('LLLLLIST', res)
                console.log('datadata', data)
                this.suggestions = data;
                return res;
            });
        },

        _onInput: function (ev) {
            const term = ev.target.value.toLowerCase();
            this.filtered = this.suggestions.filter(s =>
                s.name.toLowerCase().includes(term)
            );
            this.selectedIndex = -1;
            this._renderDropdown();
        },

        _renderDropdown: function () {
            const self = this;
            const offset = this.$input.offset();

            this.dropdown.empty().show().css({
                top: offset.top + this.$input.outerHeight(),
                left: offset.left,
                width: this.$input.outerWidth()
            });

            if (!this.filtered.length) {
                this.dropdown.hide();
                return;
            }

            this.filtered.forEach((item, index) => {
                const li = $('<li>', {
                    text: item.name,
                    css: {
                        padding: '4px 8px',
                        cursor: 'pointer',
                        background: index === this.selectedIndex ? '#eee' : '#fff'
                    },
                    click: function () {
                        self._navigateToAction(item.action_xml_id);
                        self.dropdown.hide();
                    }
                });
                self.dropdown.append(li);
            });
        },

        _onKeydown: function (ev) {
            if (!this.filtered.length) return;

            if (ev.key === 'ArrowDown') {
                ev.preventDefault();
                this.selectedIndex = (this.selectedIndex + 1) % this.filtered.length;
                this._renderDropdown();
            } else if (ev.key === 'ArrowUp') {
                ev.preventDefault();
                this.selectedIndex = (this.selectedIndex - 1 + this.filtered.length) % this.filtered.length;
                this._renderDropdown();
            } else if (ev.key === 'Enter') {
                ev.preventDefault();
                if (this.selectedIndex >= 0) {
                    const item = this.filtered[this.selectedIndex];
                    this.$input.val(item.name);
                    this.dropdown.hide();
                    console.log('item', item)
                    console.log('action_xml_id', item.action_xml_id)
                    this._navigateToAction(item.action_xml_id);
                }
            } else if (ev.key === 'Escape') {
                this.dropdown.hide();
            }
        },

        _onBlur: function () {
            setTimeout(() => this.dropdown.hide(), 200);
        },
        _navigateToAction: function (xml_id) {
            const self = this;
            this._rpc({
                model: 'ir.model.data',
                method: 'xmlid_to_res_model_res_id',
                args: [xml_id],
            }).then(([model, res_id]) => {
                if (model === 'ir.actions.act_window') {
                    // Read action data
                    self._rpc({
                        model: 'ir.actions.act_window',
                        method: 'read',
                        args: [[res_id], ['res_model']],
                    }).then(actions => {
                        const action = actions[0];
                        const suggestion = self.filtered.find(s => s.action_xml_id === xml_id);
                        console.log('suggestion', suggestion)
                        if (!suggestion) return;

                        const menu_xml_id = suggestion.menu_xml_id;
                        const view_types = suggestion.view_types;
                        console.log('menu_xml_id', menu_xml_id)
                        if (menu_xml_id) {
                            // resolve menu XML ID to ID
                            self._rpc({
                                model: 'ir.model.data',
                                method: 'xmlid_to_res_id',
                                args: [menu_xml_id],
                            }).then(menu_id => {
                                let url = `/web#action=${res_id}&model=${action.res_model}&view_type=${view_types}`;
                                if (menu_xml_id) {
                                    url += `&menu_id=${menu_id}`;
                                }
                                if (view_types === 'form') {
                                    // Force reload for correct breadcrumb behavior in form views
                                    window.location.replace(url);
                                     setTimeout(function () {
                                            window.location.reload();  // ⏱️ Reload again after short delay
                                        }, 100);// ✅ Full reload
                                } else {
                                    window.location.href = url;
                                     setTimeout(function () {
                                            window.location.reload();  // ⏱️ Reload again after short delay
                                        }, 100);// Normal navigation
                                }
//                                const url = `/web#action=${res_id}&model=${action.res_model}&view_type=${view_types}&menu_id=${menu_id}`;
//                                console.log('urlll', url)
//                                window.location.href = url;
                            });
                        } else {
                            // fallback if no menu ID
                            const url = `/web#action=${res_id}&model=${action.res_model}&view_type=${view_types}`;
                            console.log('else_urlll', url)
                            window.location.href = url;
                        }
                    });
                } else {
                    alert("Only window actions are supported.");
                }
            });
        }
    });
    fieldRegistry.add('genie_action_autocomplete_text', GenieActionAutocompleteText);
    return GenieActionAutocompleteText;
});

odoo.define('metro_genie.genie_button_click_navigator', function (require) {
    "use strict";

    const rpc = require('web.rpc');

    $(document).ready(function () {
        // Bind click for all buttons with class 'genie-nav-btn'
        $(document).on('click', '.genie-nav-btn', function () {
            const suggestionName = $(this).data('suggestion');
            console.log('suggestionName', suggestionName);
            if (!suggestionName) return;

            // Step 1: Search for matching suggestion
            rpc.query({
                model: 'metro.genie.suggestion',
                method: 'search_read',
                domain: [['name', '=', suggestionName], ['is_button', '=', true]],
                fields: ['action_xml_id', 'menu_xml_id', 'view_types', 'is_button'],
                limit: 1,
            }).then(function (records) {
                if (!records.length) {
                    alert("No action found for: " + suggestionName);
                    return;
                }

                const suggestion = records[0];

                // Step 2: Resolve action ID from XML ID
                rpc.query({
                    model: 'ir.model.data',
                    method: 'xmlid_to_res_model_res_id',
                    args: [suggestion.action_xml_id],
                }).then(function ([model, res_id]) {
                    if (model !== 'ir.actions.act_window') {
                        alert("Unsupported action type.");
                        return;
                    }

                    // Step 3: Read the action to get model name
                    rpc.query({
                        model: 'ir.actions.act_window',
                        method: 'read',
                        args: [[res_id], ['res_model']],
                    }).then(function (actions) {
                        const res_model = actions[0].res_model;
                        const view_type = suggestion.view_types;

                        // Step 4: Resolve menu ID
                        if (suggestion.menu_xml_id) {
                            rpc.query({
                                model: 'ir.model.data',
                                method: 'xmlid_to_res_id',
                                args: [suggestion.menu_xml_id],
                            }).then(function (menu_id) {
                                const url = `/web#action=${res_id}&model=${res_model}&view_type=${view_type}&menu_id=${menu_id}`;
                                window.location.href = url;
                                setTimeout(function () {
                                    window.location.reload();
                                }, 100);
                            });
                        } else {
                            const url = `/web#action=${res_id}&model=${res_model}&view_type=${view_type}`;
                            window.location.href = url;
                            setTimeout(function () {
                                window.location.reload();
                            }, 100);
                        }
                    });
                });
            });
        });
    });
});

//JUL 30 4 PM

//odoo.define('metro_genie.genie_button_click_navigator', function (require) {
//    "use strict";
//
//    const rpc = require('web.rpc');
//
//    $(document).ready(function () {
//        // Bind click for all buttons with class 'genie-nav-btn'
//        $(document).on('click', '.genie-nav-btn', function () {
//            const suggestionName = $(this).data('suggestion');
//            console.log('suggestionName', suggestionName);
//            if (!suggestionName) return;
//
//            // Step 1: Search for matching suggestion
//            rpc.query({
//                model: 'metro.genie.suggestion',
//                method: 'search_read',
//                domain: [['name', '=', suggestionName], ['is_button', '=', true]],
//                fields: ['action_xml_id', 'menu_xml_id', 'view_types', 'is_button'],
//                limit: 1,
//            }).then(function (records) {
//                if (!records.length) {
//                    alert("No action found for: " + suggestionName);
//                    return;
//                }
//
//                const suggestion = records[0];
//
//                // Step 2: Resolve action ID from XML ID
//                rpc.query({
//                    model: 'ir.model.data',
//                    method: 'xmlid_to_res_model_res_id',
//                    args: [suggestion.action_xml_id],
//                }).then(function ([model, res_id]) {
//                    if (model !== 'ir.actions.act_window') {
//                        alert("Unsupported action type.");
//                        return;
//                    }
//
//                    // Step 3: Read the action to get model name
//                    rpc.query({
//                        model: 'ir.actions.act_window',
//                        method: 'read',
//                        args: [[res_id], ['res_model']],
//                    }).then(function (actions) {
//                        const res_model = actions[0].res_model;
//                        const view_type = suggestion.view_types;
//
//                        // Step 4: Resolve menu ID
//                        if (suggestion.menu_xml_id) {
//                            rpc.query({
//                                model: 'ir.model.data',
//                                method: 'xmlid_to_res_id',
//                                args: [suggestion.menu_xml_id],
//                            }).then(function (menu_id) {
//                                const url = `/web#action=${res_id}&model=${res_model}&view_type=${view_type}&menu_id=${menu_id}`;
//                                window.location.href = url;
//                                setTimeout(function () {
//                                    window.location.reload();
//                                }, 100);
//                            });
//                        } else {
//                            const url = `/web#action=${res_id}&model=${res_model}&view_type=${view_type}`;
//                            window.location.href = url;
//                            setTimeout(function () {
//                                window.location.reload();
//                            }, 100);
//                        }
//                    });
//                });
//            });
//        });
//    });
//});

//odoo.define('metro_genie.genie_button_click_navigator', function (require) {
//    "use strict";
//
//    const rpc = require('web.rpc');
//
//    $(document).ready(function () {
//        $(document).on('click', '.genie-nav-btn', function () {
//            const suggestionName = $(this).data('suggestion');
//            if (!suggestionName) return;
//
//            // Step 1: Search for matching suggestion using M2O fields
//            rpc.query({
//                model: 'metro.genie.suggestion',
//                method: 'search_read',
//                domain: [['name', '=', suggestionName], ['is_button', '=', true]],
//                fields: ['window_action_id', 'client_actions_id', 'menu_id', 'view_types', 'model'],
//                limit: 1,
//            }).then(function (records) {
//                if (!records.length) {
//                    alert("No action found for: " + suggestionName);
//                    return;
//                }
//                const suggestion = records[0];
//                console.log('suggestion', suggestion)
//                const window_action_id = suggestion.window_action_id && suggestion.window_action_id[0];
//                const client_actions_id = suggestion.client_actions_id && suggestion.client_actions_id[0];
//                const model = suggestion.model;
//                const menu_id = suggestion.menu_id && suggestion.menu_id[0];
//                const view_type = suggestion.view_types;
//
//                if (!window_action_id && !client_actions_id) {
//                    alert("Missing action ID (window or client).");
//                    return;
//                }
//
//                let url = '/web#';
//                const urlParts = [];
//
//                if (window_action_id) urlParts.push(`action=${window_action_id}`);
//                if (client_actions_id) urlParts.push(`action=${client_actions_id}`);
//                if (model) urlParts.push(`model=${model}`);
//                if (view_type) urlParts.push(`view_type=${view_type}`);
//                if (menu_id) urlParts.push(`menu_id=${menu_id}`);
//
//                url += urlParts.join('&');
//                console.log('url', url)
//                window.location.href = url;
////                 Optional reload last breadcrumb removed
////                setTimeout(function () {
////                    window.location.reload();
////                }, 100);
//            });
//        });
//    });
//});

//odoo.define('metro_genie.genie_button_click_navigator', function (require) {
//    "use strict";
//
//    const rpc = require('web.rpc');
//    console.log('rpcrpcrpcrpcrpc', rpc)
//    const publicWidget = require('web.public.widget');
//
//    publicWidget.registry.GenieNavButtons = publicWidget.Widget.extend({
//        selector: '.genie-nav-btn',
//        events: {
//            'click': '_onClick',
//        },
//
//        _onClick: function (ev) {
//            ev.preventDefault();
//            const $btn = $(ev.currentTarget);
//            const suggestionName = $btn.data('suggestion');
//
//            if (!suggestionName) {
//                alert("No suggestion name provided.");
//                return;
//            }
//
//            rpc.query({
//                model: 'metro.genie.suggestion',
//                method: 'search_read',
//                domain: [['name', '=', suggestionName], ['is_button', '=', true]],
//                fields: ['window_action_id', 'client_actions_id', 'menu_id', 'view_types', 'model'],
//                limit: 1,
//            }).then(function (records) {
//                if (!records.length) {
//                    alert("No action found for: " + suggestionName);
//                    return;
//                }
//
//                const suggestion = records[0];
//                const window_action_id = suggestion.window_action_id && suggestion.window_action_id[0];
//                const client_actions_id = suggestion.client_actions_id && suggestion.client_actions_id[0];
//                const model = suggestion.model;
//                const menu_id = suggestion.menu_id && suggestion.menu_id[0];
//                const view_type = suggestion.view_types;
//
//                let url = '/web#';
//                const urlParts = [];
//
//                if (window_action_id) urlParts.push(`action=${window_action_id}`);
//                if (client_actions_id) urlParts.push(`action=${client_actions_id}`);
//                if (model) urlParts.push(`model=${model}`);
//                if (view_type) urlParts.push(`view_type=${view_type}`);
//                if (menu_id) urlParts.push(`menu_id=${menu_id}`);
//
//                url += urlParts.join('&');
//                window.location.href = url;
//            });
//        },
//    });
//});

//odoo.define('metro_genie.genie_button_click_navigator', function (require) {
//    "use strict";
//
//    const rpc = require('web.rpc');
//
//    $(document).ready(function () {
//        // Load suggestions once when the page is ready
//        rpc.query({
//            model: 'metro.genie.suggestion',
//            method: 'get_group_filtered_suggestions',
//        }).then(function (suggestions) {
//            console.log("Loaded Suggestions:", suggestions);
//
//            // Attach button click handler
//            $(document).on('click', '.genie-nav-btn', function () {
//                const suggestionName = $(this).data('suggestion');
//                const matched = suggestions.find(s => s.name === suggestionName);
//
//                if (matched) {
//                    console.log('Matched Suggestion:', matched);
//
//                    const urlParts = [];
//                    if (matched.window_action_id) urlParts.push(`action=${matched.window_action_id}`);
//                    if (matched.client_actions_id) urlParts.push(`action=${matched.client_actions_id}`);
//                    if (matched.model) urlParts.push(`model=${matched.model}`);
//                    if (matched.view_types) urlParts.push(`view_type=${matched.view_types}`);
//                    if (matched.menu_id) urlParts.push(`menu_id=${matched.menu_id}`);
//
//                    const url = '/web#' + urlParts.join('&');
//                    window.location.href = url;
//
////                    setTimeout(function () {
////                        window.location.reload();
////                    }, 100);
//                    window.location.href = url;
//                } else {
//                    alert("No matching suggestion found for: " + suggestionName);
//                }
//            });
//        });
//    });
//});