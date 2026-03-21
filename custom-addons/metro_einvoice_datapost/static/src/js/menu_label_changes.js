//odoo.define('metro_einvoice_datapost.menu_label_change', function(require) {
//    "use strict";
//
//    const session = require('web.session');
//    const WebClient = require('web.WebClient');
//
//    WebClient.include({
//        show_application: function() {
//            return this._super.apply(this, arguments).then(() => {
//
//                let menu = $('a[data-menu-xmlid="metro_einvoice_datapost.menu_peppol_root"]');
//                console.log('>>>>>>>>>>>>>>.', menu)
//
//                session.user_has_group('metro_einvoice_datapost.group_c5_submitter').then(has_c5 => {
//                    if (has_c5) {
//                        menu.text("GST InvoiceNow");
//                    } else {
//                        menu.text("InvoiceNow");
//                    }
//                });
//
//            });
//        }
//    });
//});

//odoo.define('metro_einvoice_datapost.menu_dynamic_label', function (require) {
//    "use strict";
//
//    const WebClient = require('web.WebClient');
//    const session = require('web.session');
//
//    WebClient.include({
//
//        show_application: function () {
//            const res = this._super.apply(this, arguments);
//
//            setTimeout(() => {
//                this._updateMenuName();
//            }, 1000);
//
//            return res;
//        },
//
//        /**
//         * Change menu name based on user group
//         */
//        _updateMenuName: function () {
//
//            // ✅ Change label based on groups
//            const isC5 = session.user_has_group('metro_einvoice_datapost.group_c5_submitter');
//            const newName = isC5 ? "GST InvoiceNow" : "InvoiceNow";
//
//            // ✅ Update Top Navbar Menu
//            document.querySelectorAll('nav .o_menu_brand').forEach(el => {
//                if (el.textContent.includes("InvoiceNow")) {
//                    el.textContent = newName;
//                }
//            });
//
//            // ✅ Update App Sidebar Menu Entry
//            document.querySelectorAll('.o_menu_entry_lvl_1, .o_app').forEach(el => {
//                if (el.textContent.trim() === "InvoiceNow" || el.textContent.trim() === "GST InvoiceNow") {
//                    el.textContent = newName;
//                }
//            });
//
//        }
//    });
//
//});






//odoo.define('your_module.menu_dynamic_label', function (require) {
//    "use strict";
//
//    const WebClient = require('web.WebClient');
//    const session = require('web.session');
//    const core = require('web.core');
//
//    WebClient.include({
//        show_application: function () {
//            const self = this;
//            // Ensure we call original then run our updater when ready
//            return this._super.apply(this, arguments).then(function () {
//                // Wait a bit to ensure menu DOM exists (menu rendering is async)
//                // but better: try repeatedly until menus are present
//                const tryUpdate = function (attemptsLeft) {
//                    // Query for any element that references the menu via xmlid attribute
//                    const selector = 'a[data-menu-xmlid="metro_einvoice_datapost.menu_peppol_root"], a[data-menu-xmlid="metro_einvoice_datapost.menu_peppol_root"] span';
//                    const nodes = document.querySelectorAll(selector);
//
//                    if (nodes && nodes.length) {
//                        // Check user group (async)
//                        session.user_has_group('metro_einvoice_datapost.group_c5_submitter').then(function (has_c5) {
//                            const newName = has_c5 ? "GST InvoiceNow" : "InvoiceNow";
//
//                            // Update all anchor elements that carry the data-menu-xmlid.
//                            document.querySelectorAll('a[data-menu-xmlid="metro_einvoice_datapost.menu_peppol_root"]').forEach(function (a) {
//                                // If link has children, update the text node that is the visible label
//                                // common patterns:
//                                //  - <a ...><span>Label</span></a>
//                                //  - <a ...>Label</a>
//                                if (a.querySelector('span')) {
//                                    a.querySelectorAll('span').forEach(function (s) {
//                                        // Only change exact matches to avoid clobbering other text
//                                        if (s.textContent.trim() === "InvoiceNow" || s.textContent.trim() === "GST InvoiceNow") {
//                                            s.textContent = newName;
//                                        }
//                                    });
//                                } else {
//                                    if (a.textContent.trim() === "InvoiceNow" || a.textContent.trim() === "GST InvoiceNow") {
//                                        a.textContent = newName;
//                                    }
//                                }
//                            });
//
//                            // Update top-left "app" label (some themes use .o_menu_brand, .o_app_name, or .o_menu_systray .o_menu_brand)
//                            document.querySelectorAll('.o_menu_brand, .o_app .o_app_name, .o_menu_systray .o_menu_brand').forEach(function (el) {
//                                if (el.textContent && (el.textContent.trim() === "InvoiceNow" || el.textContent.trim() === "GST InvoiceNow")) {
//                                    el.textContent = newName;
//                                }
//                            });
//
//                            // Update app list (App Switcher) - the icons area
//                            document.querySelectorAll('.o_app .o_app_name, .o_app').forEach(function (el) {
//                                if (el.textContent && (el.textContent.trim() === "InvoiceNow" || el.textContent.trim() === "GST InvoiceNow")) {
//                                    el.textContent = newName;
//                                }
//                            });
//
//                            // Update left sidebar (if any remaining)
//                            document.querySelectorAll('.o_menu_entry_lvl_1, .o_menu_entry').forEach(function (el) {
//                                if (el.textContent && (el.textContent.trim() === "InvoiceNow" || el.textContent.trim() === "GST InvoiceNow")) {
//                                    el.textContent = newName;
//                                }
//                            });
//                        }).catch(function (err) {
//                            console.error("Error checking group:", err);
//                        });
//
//                    } else if (attemptsLeft > 0) {
//                        // Try again shortly
//                        setTimeout(function () { tryUpdate(attemptsLeft - 1); }, 300);
//                    } else {
//                        console.warn("menu_dynamic_label: menu node not found to update label");
//                    }
//                };
//
//                // Try up to ~10 times (total ~3 seconds) to find menus rendered
//                tryUpdate(10);
//            });
//        }
//    });
//});


//odoo.define('metro_einvoice_datapost.MenuReloadFix', function (require) {
//    'use strict';
//
//    const WebClient = require('web.WebClient');
//    const rpc = require('web.rpc');
//
//    WebClient.include({
//        show_application: async function () {
//            // ✅ Force reload menu items fresh from backend
//            await rpc.query({
//                model: 'ir.ui.menu',
//                method: 'load_menus',
//                args: [false],
//            });
//
//            return this._super.apply(this, arguments);
//        }
//    });
//});


odoo.define('metro_einvoice_datapost.MenuLabelChanger', function (require) {
    "use strict";

    const session = require('web.session');
    const rpc = require('web.rpc');

    rpc.query({
        model: 'res.users',
        method: 'has_group',
        args: ['metro_einvoice_datapost.group_peppol_submitter'],
    }).then(function (is_admin) {
        const menu = document.querySelector('a[data-menu-xmlid="metro_einvoice_datapost.menu_peppol_root"]');
        if (menu) {
            if (is_admin) {
                menu.textContent = "GST InvoiceNow";
            } else {
                menu.textContent = "InvoiceNow";
            }
        }
    });
});



