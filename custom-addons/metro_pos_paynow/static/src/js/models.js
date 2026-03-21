odoo.define('metro_pos_paynow.models', function (require) {
"use strict";

    var models = require('point_of_sale.models');

    models.load_fields("pos.payment.method", ['use_payment_terminal']);
    models.load_fields("res.company", ['l10n_sg_unique_entity_number'])

});
