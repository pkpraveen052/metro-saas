odoo.define('metro_helpdesk.HelpdeskButton', function (require) {
    "use strict";

    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var QWeb = core.qweb;
    var Dialog = require('web.Dialog');
    var rpc = require('web.rpc');
    var Notification = require('web.Notification'); // Import Notification

    var HelpdeskButton = Widget.extend({
        template: 'metro_helpdesk.HelpdeskButton',
        events: {
            'click': '_onHelpdeskButtonClick',
        },
        start: function () {
            this._super.apply(this, arguments);
            this._positionButton();
        },

        _onHelpdeskButtonClick: function () {
            var self = this;
            console.log(self);
            var currentUrl = window.location.href; // Get the current URL
            console.log(currentUrl);

            var urlLink = '<a href="' + currentUrl + '">' + currentUrl + '</a>'; // Create the hyperlink
            
            // Capture screenshot and perform RPC call in sequence
            this._takeScreenshot().then(function (screenshotDataUrl) {
                self._showNotification('Screenshot taken successfully!'); // Show notification
                var binaryData = screenshotDataUrl.split(',')[1]; // Get binary data of the screenshot
                
                return self._rpc({
                    model: 'helpdesk.ticket',
                    method: 'get_helpdesk_ticket_defaults',
                    args: [],
                    kwargs: {
                        'description': 'Issue occurred at: ' + urlLink, // Include URL as hyperlink in description
                        'current_issues_image': binaryData, // Attach the screenshot as binary data
                    },
                });
            }).then(function (action) {
                self.do_action(action);
            }).catch(function (error) {
                console.error("Error occurred:", error);
            });
        },

        _takeScreenshot: function () {
            var screenElement = document.querySelector('.o_web_client');
            return html2canvas(screenElement, {
                logging: false,
                useCORS: true,
                width: screenElement.clientWidth,  // Capture the width of the visible area
                height: screenElement.clientHeight // Capture the height of the visible area
            }).then(function (canvas) {
                return canvas.toDataURL('image/png');
            });
        },

        _showNotification: function (message) {
            this.call('notification', 'notify', {
                message: message,
                type: 'success',
                sticky: false,
            });
        },

        _positionButton: function () {
            var self = this;
            this.$el.detach();
            var mailIcon = $('.o_mail_systray_item');
            if (mailIcon.length) {
                mailIcon.before(this.$el);
            } else {
                setTimeout(function () {
                    self._positionButton();
                }, 100);
            }
        },
    });

    SystrayMenu.Items.unshift(HelpdeskButton);

    return HelpdeskButton;
});

odoo.define('metro_helpdesk.custom_access_error', function (require) {
    "use strict";

    var Dialog = require('web.Dialog');
    var core = require('web.core');
    var rpc = require('web.rpc');  // Import RPC
    var _t = core._t;

    Dialog.include({
        open: function () {
            // Check if this is an AccessError popup
            if (this.title === _t("Access Error")) {
                this.buttons.push({
                    text: _t("Raise Ticket"),
                    classes: 'btn-primary',
                    click: () => {
                        console.log("Helpdesk button clicked");
                        var currentUrl = window.location.href; //window current url
                        var urlLink = '<a href="' + currentUrl + '">' + currentUrl + '</a>'; // url hyperlink
                        // Take screenshot
                        this._takeScreenshot().then((screenshotDataUrl) => {
                            this._showNotification('Screenshot taken successfully!'); // Show notification
                            var binaryData = screenshotDataUrl.split(',')[1];  // Extract binary data from screenshot

                            // Make RPC call to Python method with context data
                            rpc.query({
                                model: 'helpdesk.ticket',
                                method: 'get_helpdesk_ticket_defaults_my_custom',
                                args: [],
                                kwargs: {
                                    description: 'Issue occurred at: ' + urlLink, // Include URL in description
                                    current_issues_image: binaryData, // Attach screenshot as binary data
                                },
                            }).then((result) => {
                                if (result) {
                                    // Trigger the action returned by the Python method
                                    self.do_action(result);
                                }
                            });
                        });
                    },
                });
            }
            return this._super.apply(this, arguments);
        },

        _takeScreenshot: function () {
            var screenElement = document.querySelector('.o_web_client');
            return html2canvas(screenElement, {
                logging: false,
                useCORS: true,
                width: screenElement.clientWidth,  // Capture the width of the visible area
                height: screenElement.clientHeight // Capture the height of the visible area
            }).then((canvas) => {
                return canvas.toDataURL('image/png');
            });
        },

        _showNotification: function (message) {
            this.call('notification', 'notify', {
                message: message,
                type: 'success',
                sticky: false,
            });
        },

    });
});

odoo.define('metro_helpdesk.custom_user_error', function (require) {
    "use strict";

    var Dialog = require('web.Dialog');
    var core = require('web.core');
    var rpc = require('web.rpc');  // Import RPC
    var _t = core._t;

    Dialog.include({
        open: function () {
            // Check if this is an AccessError popup
            if (this.title === _t("User Error")) {
                this.buttons.push({
                    text: _t("Raise Ticket"),
                    classes: 'btn-primary',
                    click: () => {
                        console.log("Helpdesk button clicked");
                        var currentUrl = window.location.href; //window current url
                        var urlLink = '<a href="' + currentUrl + '">' + currentUrl + '</a>'; // url hyperlink
                        // Take screenshot
                        this._takeScreenshot().then((screenshotDataUrl) => {
                            this._showNotification('Screenshot taken successfully!'); // Show notification
                            var binaryData = screenshotDataUrl.split(',')[1];  // Extract binary data from screenshot

                            // Make RPC call to Python method with context data
                            rpc.query({
                                model: 'helpdesk.ticket',
                                method: 'get_helpdesk_ticket_defaults_my_custom',
                                args: [],
                                kwargs: {
                                    description: 'Issue occurred at: ' + urlLink, // Include URL in description
                                    current_issues_image: binaryData, // Attach screenshot as binary data
                                },
                            }).then((result) => {
                                if (result) {
                                    // Trigger the action returned by the Python method
                                    self.do_action(result);
                                }
                            });
                        });
                    },
                });
            }
            return this._super.apply(this, arguments);
        },

        _takeScreenshot: function () {
            var screenElement = document.querySelector('.o_web_client');
            return html2canvas(screenElement, {
                logging: false,
                useCORS: true,
                width: screenElement.clientWidth,  // Capture the width of the visible area
                height: screenElement.clientHeight // Capture the height of the visible area
            }).then((canvas) => {
                return canvas.toDataURL('image/png');
            });
        },

        _showNotification: function (message) {
            this.call('notification', 'notify', {
                message: message,
                type: 'success',
                sticky: false,
            });
        },

    });
});

odoo.define('metro_helpdesk.custom_Validation_error', function (require) {
    "use strict";

    var Dialog = require('web.Dialog');
    var core = require('web.core');
    var rpc = require('web.rpc');  // Import RPC
    var _t = core._t;

    Dialog.include({
        open: function () {
            // Check if this is an AccessError popup
            if (this.title === _t("Validation Error")) {
                this.buttons.push({
                    text: _t("Raise Ticket"),
                    classes: 'btn-primary',
                    click: () => {
                        console.log("Helpdesk button clicked");
                        var currentUrl = window.location.href; //window current url
                        var urlLink = '<a href="' + currentUrl + '">' + currentUrl + '</a>'; // url hyperlink
                        // Take screenshot
                        this._takeScreenshot().then((screenshotDataUrl) => {
                            this._showNotification('Screenshot taken successfully!'); // Show notification
                            var binaryData = screenshotDataUrl.split(',')[1];  // Extract binary data from screenshot

                            // Make RPC call to Python method with context data
                            rpc.query({
                                model: 'helpdesk.ticket',
                                method: 'get_helpdesk_ticket_defaults_my_custom',
                                args: [],
                                kwargs: {
                                    description: 'Issue occurred at: ' + urlLink, // Include URL in description
                                    current_issues_image: binaryData, // Attach screenshot as binary data
                                },
                            }).then((result) => {
                                if (result) {
                                    // Trigger the action returned by the Python method
                                    self.do_action(result);
                                }
                            });
                        });
                    },
                });
            }
            return this._super.apply(this, arguments);
        },

        _takeScreenshot: function () {
            var screenElement = document.querySelector('.o_web_client');
            return html2canvas(screenElement, {
                logging: false,
                useCORS: true,
                width: screenElement.clientWidth,  // Capture the width of the visible area
                height: screenElement.clientHeight // Capture the height of the visible area
            }).then((canvas) => {
                return canvas.toDataURL('image/png');
            });
        },

        _showNotification: function (message) {
            this.call('notification', 'notify', {
                message: message,
                type: 'success',
                sticky: false,
            });
        },

    });
});


odoo.define('metro_helpdesk.Access_Error_Handler', function(require) {
    "use strict";

    var Dialog = require('web.Dialog');
    var Widget = require('web.Widget');

    // Override the display behavior of the error dialog
    Dialog.include({
        init: function(parent, options) {
            this._super.apply(this, arguments);
            if (options && options.fullTraceback) {
                this.tracebackMessage = options.fullTraceback; // Store the full traceback
            }
        },
        start: function() {
            var self = this;
            if (this.tracebackMessage) {
                console.log('Traceback Message:', this.tracebackMessage); // Display the traceback message in console
                // You can also trigger a custom event with this traceback
                this.trigger('error_traceback', { traceback: this.tracebackMessage });
            }
            return this._super.apply(this, arguments);
        }
    });
});

odoo.define('metro_helpdesk.custom_metroerp_traceback_error', function (require) {
    "use strict";

    var Dialog = require('web.Dialog');
    var core = require('web.core');
    var rpc = require('web.rpc');  // Import RPC
    var _t = core._t;

    Dialog.include({
        open: function () {
            // Check if this is an AccessError popup
            if (this.title === _t("MetroERP Error")) {
                this.buttons.push({
                    text: _t("Raise Ticket"),
                    classes: 'btn-primary',
                    click: () => {
                        console.log("Helpdesk button clicked");
                        var currentUrl = window.location.href; //window current url
                        var urlLink = '<a href="' + currentUrl + '">' + currentUrl + '</a>'; // url hyperlink
//                        var errorMessage = this.$el.find('.o_error_detail pre').text(); // Extract traceback message
                        var errorElement = this.$('.o_error_detail pre');
                        var errorMessage = errorElement.length ? errorElement.text() :'No error message available';
                        var formattedErrorMessage = errorMessage.replace(/\n/g, '<br>');
                        // Take screenshot
                        this._takeScreenshot().then((screenshotDataUrl) => {
                            this._showNotification('Screenshot taken successfully!'); // Show notification
                            var binaryData = screenshotDataUrl.split(',')[1];  // Extract binary data from screenshot
                            // Make RPC call to Python method with context data
                            rpc.query({
                                model: 'helpdesk.ticket',
                                method: 'get_helpdesk_ticket_defaults_traceback',
                                args: [],
                                kwargs: {
                                    description: 'Issue occurred at: ' + urlLink, // Include URL in description
                                    current_issues_image: binaryData,
                                    traceback_error: formattedErrorMessage,// Attach screenshot as binary data
                                },
                            }).then((result) => {
                                if (result) {
                                    // Trigger the action returned by the Python method
                                    self.do_action(result);
                                }
                            });
                        });
                    },
                });
            }
            return this._super.apply(this, arguments);
        },

        _takeScreenshot: function () {
            var screenElement = document.querySelector('.o_web_client');
            return html2canvas(screenElement, {
                logging: false,
                useCORS: true,
                width: screenElement.clientWidth,  // Capture the width of the visible area
                height: screenElement.clientHeight,
                 scale: 0.5,// Capture the height of the visible area
            }).then((canvas) => {
                return canvas.toDataURL('image/png', 0.5);
            });
        },

        _showNotification: function (message) {
            this.call('notification', 'notify', {
                message: message,
                type: 'success',
                sticky: false,
            });
        },

    });
});

odoo.define('metro_helpdesk.custom_metroerp_client_error', function (require) {
    "use strict";

    var Dialog = require('web.Dialog');
    var core = require('web.core');
    var rpc = require('web.rpc');  // Import RPC
    var _t = core._t;

    Dialog.include({
        open: function () {
            // Check if this is an AccessError popup
            if (this.title === _t("MetroERP Client Error")) {
                this.buttons.push({
                    text: _t("Raise Ticket"),
                    classes: 'btn-primary',
                    click: () => {
                        console.log("Helpdesk button clicked");
                        var currentUrl = window.location.href; //window current url
                        var urlLink = '<a href="' + currentUrl + '">' + currentUrl + '</a>'; // url hyperlink
//                        var errorMessage = this.$el.find('.o_error_detail pre').text(); // Extract traceback message
                        var errorElement = this.$('.o_error_detail pre');
                        var errorMessage = errorElement.length ? errorElement.text() :'No error message available';
                        var formattedErrorMessage = errorMessage.replace(/\n/g, '<br>');
                        // Take screenshot
                        this._takeScreenshot().then((screenshotDataUrl) => {
                            this._showNotification('Screenshot taken successfully!'); // Show notification
                            var binaryData = screenshotDataUrl.split(',')[1];  // Extract binary data from screenshot
                            // Make RPC call to Python method with context data
                            rpc.query({
                                model: 'helpdesk.ticket',
                                method: 'get_helpdesk_ticket_defaults_traceback',
                                args: [],
                                kwargs: {
                                    description: 'Issue occurred at: ' + urlLink, // Include URL in description
                                    current_issues_image: binaryData,
                                    traceback_error: formattedErrorMessage,// Attach screenshot as binary data
                                },
                            }).then((result) => {
                                if (result) {
                                    // Trigger the action returned by the Python method
                                    self.do_action(result);
                                }
                            });
                        });
                    },
                });
            }
            return this._super.apply(this, arguments);
        },

        _takeScreenshot: function () {
            var screenElement = document.querySelector('.o_web_client');
            return html2canvas(screenElement, {
                logging: false,
                useCORS: true,
                width: screenElement.clientWidth,  // Capture the width of the visible area
                height: screenElement.clientHeight,
                 scale: 0.5,// Capture the height of the visible area
            }).then((canvas) => {
                return canvas.toDataURL('image/png', 0.5);
            });
        },

        _showNotification: function (message) {
            this.call('notification', 'notify', {
                message: message,
                type: 'success',
                sticky: false,
            });
        },

    });
});









