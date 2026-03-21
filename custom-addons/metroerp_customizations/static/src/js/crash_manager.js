odoo.define('metroerp_customizations.crash_manager', function (require) {
"use strict";
	
	var core = require('web.core');
    var CrashManager = require('web.CrashManager');

    var _t = core._t;

    /**
    * Overidden session_expired() to modify the message content in order to hide the Odoo
    */
    function session_expired(cm) {
	    return {
	        display: function () {
	            const notif = {
	                type: _t("Session Expired"),
	                message: _t("Session got expired. The current page is about to be refreshed."),
	            };
	            const options = {
	                buttons: [{
	                    text: _t("Ok"),
	                    click: () => window.location.reload(true),
	                    close: true
	                }],
	            };
	            cm.show_warning(notif, options);
	        }
	    }
	}
	core.crash_registry.add('odoo.http.SessionExpiredException', session_expired);
    
  //   CrashManager.include({

  //       function session_expired(cm) {
		//     return {
		//         display: function () {
		//             const notif = {
		//                 type: _t("Odooq Session Expired"),
		//                 message: _t("Your Odooq session expired. The current page is about to be refreshed."),
		//             };
		//             const options = {
		//                 buttons: [{
		//                     text: _t("Ok"),
		//                     click: () => window.location.reload(true),
		//                     close: true
		//                 }],
		//             };
		//             cm.show_warning(notif, options);
		//         }
		//     }
		// }
		// core.crash_registry.add('odoo.http.SessionExpiredException', session_expired);


  //   });

});