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
                    method: 'get_group_filtered_suggestions',
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
                        self._navigateToAction(item);
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
                    this._navigateToAction(item);
                }
            } else if (ev.key === 'Escape') {
                this.dropdown.hide();
            }
        },

        _onBlur: function () {
            setTimeout(() => this.dropdown.hide(), 200);
        },
        _navigateToAction: function (item) {
            const window_action_id = item.window_action_id;
            const client_actions_id = item.client_actions_id;
            const model = item.model;
            const menu_id = item.menu_id;
            const view_type = item.view_types;

            if (!window_action_id && !client_actions_id) {
                    alert("Missing action ID (window or client).");
                    return;
                }

            let url = '/web#';
            const urlParts = [];

            if (window_action_id) urlParts.push(`action=${window_action_id}`);
            if (client_actions_id) urlParts.push(`action=${client_actions_id}`);
            if (model) urlParts.push(`model=${model}`);
            if (view_type) urlParts.push(`view_type=${view_type}`);
            if (menu_id) urlParts.push(`menu_id=${menu_id}`);

            url += urlParts.join('&'); // joined full url
            window.location.href = url; // url loaded
          // Optional reload last breadcrumb removed
//            if (view_type) {
//                setTimeout(function () {
//                    window.location.reload();
//                }, 100);
//            }
        }
    });
    fieldRegistry.add('genie_action_autocomplete_text', GenieActionAutocompleteText);
    return GenieActionAutocompleteText;
});


//odoo.define('metro_genie.genie_button_click_navigator', function (require) {
//    "use strict";
//
//    const rpc = require('web.rpc');
//
//    let cachedSuggestions = [];
//
//    rpc.query({
//        model: 'metro.genie.suggestion',
//        method: 'get_group_filtered_suggestions',
//    }).then(function (data) {
//        cachedSuggestions = data;
//    });
//
//    $(document).ready(function () {
//        $(document).on('click', '.genie-nav-btn', function (event) {
//            event.preventDefault();
//
//            const suggestionName = $(this).data('suggestion');
//            const matched = cachedSuggestions.find(s => s.name === suggestionName && s.is_button);
//
//            if (!matched || (!matched.window_action_id && !matched.client_actions_id)) {
//                alert("No action found!");
//                return;
//            }
//
//            const urlParts = [];
//            if (matched.window_action_id) urlParts.push(`action=${matched.window_action_id}`);
//            if (matched.client_actions_id) urlParts.push(`action=${matched.client_actions_id}`);
//            if (matched.menu_id) urlParts.push(`menu_id=${matched.menu_id}`);
//            if (matched.model) urlParts.push(`model=${matched.model}`);
//            if (matched.view_types) urlParts.push(`view_type=${matched.view_types}`);
//            const url = '/web#' + urlParts.join('&');
//            setTimeout(function () {
//                window.location.replace(url);
//
//                // Optional reload if needed for 'form' view
//                if (matched.view_types) {
//                    setTimeout(function () {
//                        window.location.reload();
//                    }, 300);
//                }
//            }, 100);
//        });
//    });
//});

//odoo.define('metro_genie.genie_button_click_navigator', function (require) {
//    "use strict";
//
//    const rpc = require('web.rpc');
//
//    rpc.query({
//        model: 'metro.genie.suggestion',
//        method: 'get_group_filtered_suggestions',
//    }).then(function (data) {
//        const cachedSuggestions = data;
//
//        // Only attach event listener *after* suggestions are loaded
//        $(document).ready(function () {
//            $(document).on('click', '.genie-nav-btn', function (event) {
//                event.preventDefault();
//
//                const suggestionName = $(this).data('suggestion');
//                const matched = cachedSuggestions.find(s => s.name === suggestionName && s.is_button);
//
//                if (!matched || (!matched.window_action_id && !matched.client_actions_id)) {
//                    alert("No action found!");
//                    return;
//                }
//
//                const urlParts = [];
//                if (matched.window_action_id) urlParts.push(`action=${matched.window_action_id}`);
//                if (matched.client_actions_id) urlParts.push(`action=${matched.client_actions_id}`);
//                if (matched.menu_id) urlParts.push(`menu_id=${matched.menu_id}`);
//                if (matched.model) urlParts.push(`model=${matched.model}`);
//                if (matched.view_types) urlParts.push(`view_type=${matched.view_types}`);
//                const url = '/web#' + urlParts.join('&');
//
//                setTimeout(function () {
//                    window.location.replace(url);
//
//                    // Optional reload if needed for view
//                    if (matched.view_types) {
//                        setTimeout(function () {
//                            window.location.reload();
//                        }, 300);
//                    }
//                }, 100);
//            });
//        });
//    });
//});




odoo.define('metro_genie.genie_button_click_navigator', function (require) {
    "use strict";

    const rpc = require('web.rpc');

    rpc.query({
        model: 'metro.genie.suggestion',
        method: 'get_group_filtered_suggestions',
    }).then(function (data) {
        const cachedSuggestions = data;
        console.log('cachedSuggestions', cachedSuggestions)

        // Attach click handler immediately (outside of $(document).ready)
        $(document).on('click', '.genie-nav-btn', function (event) {
            event.preventDefault();

            const suggestionName = $(this).data('suggestion');
            console.log('suggestionName', suggestionName)
            const matched = cachedSuggestions.find(s => s.name === suggestionName && s.is_button);
            console.log('matched', matched)
            if (!matched || (!matched.window_action_id && !matched.client_actions_id)) {
                alert("No action found!");
                return;
            }

            const urlParts = [];
            if (matched.window_action_id) urlParts.push(`action=${matched.window_action_id}`);
            if (matched.client_actions_id) urlParts.push(`action=${matched.client_actions_id}`);
            if (matched.menu_id) urlParts.push(`menu_id=${matched.menu_id}`);
            if (matched.model) urlParts.push(`model=${matched.model}`);
            if (matched.view_types) urlParts.push(`view_type=${matched.view_types}`);
            const url = '/web#' + urlParts.join('&');
            console.log('url', url)
            window.location.replace(url);
            setTimeout(function () {
                window.location.replace(url);

                // Optional reload if needed for view
                if (matched.view_types) {
                    setTimeout(function () {
                        window.location.reload();
                    }, 300);
                }
            }, 100);
        });
    });
});










