odoo.define('metroerp_customizations/static/src/js/notification_request.js', function (require) {
'use strict';

   const NotificationRequest = require('mail/static/src/components/notification_request/notification_request.js')

   const { patch } = require('web.utils');

   // Overidden code below
   patch(NotificationRequest, 'metroerp_customizations/static/src/js/notification_request.js', {
		_handleResponseNotificationPermission(value) {
		// manually force recompute because the permission is not in the store
			this.env.messaging.messagingMenu.update();
			if(odoo.debranding_settings && odoo.debranding_settings.odoo_text_replacement) {
				var msg = odoo.debranding_settings.odoo_text_replacement + " will not have the permission to send native notifications on this device."
			} else {
				var msg = "ERP will not have the permission to send native notifications on this device."
			}
			if (value !== 'granted') {
			    this.env.services['bus_service'].sendNotification(
			        this.env._t("Permission denied"),
			        this.env._t(msg)
			    );
			}
		}
   });

});
