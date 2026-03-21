/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
odoo.define('pos_change_logo.pos_change_logo', function (require) {
	"use strict";
	var Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');

    var PosResChrome = Chrome =>
        class extends Chrome {
			get_logo(){

				var self = this;
				if(self.env.pos && self.env.pos.config && !self.env.pos.config.pos_logo)
					return false;
				var img = new Image();
				img.onload = function() {
					var ratio = 1;
					var targetwidth = 300;
					var maxheight = 150;
					if( img.width !== targetwidth ){
						ratio = targetwidth / img.width;
					}
					if( img.height * ratio > maxheight ){
						ratio = maxheight / img.height;
					}
					var width  = Math.floor(img.width * ratio);
					var height = Math.floor(img.height * ratio);
					var c = document.createElement('canvas');
						c.width  = width;
						c.height = height;
					var ctx = c.getContext('2d');
						ctx.drawImage(img,0,0, width, height);
					self.env.pos.pos_logo_base_64 = c.toDataURL();
				};
				if(self.env.pos && self.env.pos.config && self.env.pos.config.id){
					img.src = window.location.origin + '/web/image?model=pos.config&field=pos_logo&id='+self.env.pos.config.id;
					return window.location.origin + '/web/image?model=pos.config&field=pos_logo&id='+self.env.pos.config.id
				}
				else
					return false
			}
		}

    Registries.Component.extend(Chrome, PosResChrome);

	Registries.Component.freeze();
	return Chrome;
	
});