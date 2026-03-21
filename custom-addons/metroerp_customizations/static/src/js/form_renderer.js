odoo.define('metroerp_customizations.form_renderer', function (require) {
"use strict";


	var FormRenderer = require('web.FormRenderer');

	FormRenderer.include({
		/** 
		* Overidden
		*/
	    _renderView: function () {
	    	if ( this.viewType == "form") { 
	    		var self = this;
	    		if ( this.state.model == "res.config.settings" ) {
	    			return this._super.apply(this, arguments).then(function () {
	    				// To set the <a/> links void
		        		self.$('a[class$="o_doc_link"]').each(function() {
		                    var hrefVal = $(this).attr('href')
		                    if ( typeof (hrefVal) == 'string' && hrefVal.includes("odoo")) { 
		                		$(this).removeAttr("href")	
		            		}
		                })
		                self.$('a[class$="oe_link"]').each(function() {
		                    var hrefVal = $(this).attr('href')
		                    if ( typeof (hrefVal) == 'string' && hrefVal.includes("odoo")) { 
		                		$(this).removeAttr("href")
		            		}
		                })
		                // To Disable the Buy Credits Link
		                self.$('button[class^="btn btn-link buy_credits"]').each(function() {
		                	$(this).attr("disabled","disabled")
		                })
		    		});
	    		} 
	    		// To hide the <img/> in the mail templates as it displays the Odoo logo
	    		// if ( this.state.model == "mail.template" ) {
	    		// 	return this._super.apply(this, arguments).then(function () {
	    		// 		if ( self.$( 'div[class="note-editor panel panel-default"]' ).length == 0 ) {
			    //     		self.$('img[id="mail_template_images"]').each(function() {
		     //            		$(this).removeAttr("src")
		     //            		$(this).removeAttr("alt")
			    //             })
		     //            }
		    	// 	});
	    		// }
	        	return this._super.apply(this, arguments).then(function () {
	        		// To replace the www.odoo.com with custom values
	        		self.$('input[class$="o_field_url o_field_widget o_input"]').each(function() {
	                    var placeHolder = $(this).attr('placeholder')
	                    if ( typeof (placeHolder) == 'string' && placeHolder.includes("odoo")) { 
	                		$(this).attr("placeholder","e.g. https://www.website.com")	
	            		}
	                })
	    		});
	        } else {
	            return this._super.apply(this, arguments);
	        }
	    },
	});

});
