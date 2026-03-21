odoo.define('metroerp_customizations.AbstractRenderer', function (require) {
"use strict";

	var AbstractRenderer = require('web.AbstractRenderer');

	AbstractRenderer.include({

		init: function(parent, state, params) {
			var odoo_text_replacement = '';
            if(odoo.debranding_settings && odoo.debranding_settings.odoo_text_replacement) 
                odoo_text_replacement = odoo.debranding_settings.odoo_text_replacement.trim();
            if (params.noContentHelp && typeof(params.noContentHelp) =='string'){
                params.noContentHelp = params.noContentHelp.replace(/odoo/gi, odoo_text_replacement);
            }
            this._super.apply(this, arguments);
		},
	});
});