odoo.define('aspl_pos_kitchen_screen.ClientScreenButtonPatch', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const ClientScreenButton = require('point_of_sale.ClientScreenButton');

    const ClientScreenButtonPatch = (ClientScreenButton) =>
        class extends ClientScreenButton {
            mounted() {
                super.mounted();
                // Hide the button if user is a cook
                if (this.env.pos.user.kitchen_screen_user === 'cook') {
                    this.el.style.display = 'none';
                }
            }
        };

    Registries.Component.extend(ClientScreenButton, ClientScreenButtonPatch);

    return ClientScreenButtonPatch;
});


// odoo.define('aspl_pos_kitchen_screen.models', function (require) {
//     'use strict';

//     const models = require('point_of_sale.models');

//     models.load_fields('res.users', ['kitchen_screen_user']);
// });
