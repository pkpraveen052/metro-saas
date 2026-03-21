odoo.define("metroerp_userguide.ListClickRedirection", function (require) {
    "use strict";

    var ListRenderer = require("web.ListRenderer");
    var core = require("web.core");

    var _t = core._t;

    ListRenderer.include({
        _renderRow: function (record) {
            var $row = this._super(record);
            var self = this;
            if (record.model === "user.guide.url") {
                $row.addClass('o_list_no_open');
                // add click event
                $row.on('click', function (ev) {
                    ev.preventDefault();
                    ev.stopPropagation();
                    var url = record.data.href; // Change 'product_url' to the actual field containing the URL
                    if (url) {
                        window.open(url, '_blank');
                    } else {
                        self.do_warn(_t('Warning'), _t('No URL found for this record.'));
                    }
                });
            }
            return $row;
        },
    });
});
