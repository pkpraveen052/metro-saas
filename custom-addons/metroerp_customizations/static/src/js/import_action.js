odoo.define('metroerp_customizations.base_import', function (require) {
'use strict';


	var DataImport = require('base_import.import');

	var DataImport = DataImport.DataImport

    DataImport.include({
        /**
         * Inherited start() to hide the 'Import FAQ' link on the import page.
        */
        start: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.$('a[href$="import_faq.html"]').each(function(){
                	$(this).attr('style','display:none')
            	})
            });
        },
    });

});