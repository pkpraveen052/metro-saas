odoo.define('metroerp_pos.CustomTicketScreen', function (require) {
    'use strict';

    var time = require('web.time');
    const TicketScreen = require('point_of_sale.TicketScreen');  
    const Registries = require('point_of_sale.Registries');     

    const CustomTicketScreen = (TicketScreen) => class extends TicketScreen {
        getDate(order) {
            var userLang = odoo.session_info.user_context.lang; 
            var dateFormat = time.getLangDateFormat(userLang);   
            return moment(order.creation_date).format(dateFormat + ' hh:mm A');
        }
    };

    Registries.Component.extend(TicketScreen, CustomTicketScreen);

    return CustomTicketScreen;
});
