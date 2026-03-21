
odoo.define('res.partner.kanban.search', function (require) {
"use strict";
    var core = require('web.core');
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var UploadBillMixin = require('account.upload.bill.mixin');
    var viewRegistry = require('web.view_registry');

    var SearchButtonKanbannViewContoller = KanbanController.extend({
        buttons_template: 'SearchKanbanView.buttons',
        events: _.extend({}, KanbanController.prototype.events, {
            'click .o_button_search_partner': '_onClickPeppolDirectoryButton',
        }),

        _onClickPeppolDirectoryButton: function (event) {
          event.preventDefault();
          var self = this;

          switch (self.initialState.context.res_partner_search_mode) {
              case "supplier":
              self.do_action('metro_einvoice_datapost.peppol_api_dictionary_call_in_purchases', {
              });
                  break;
              case "customer":

              self.do_action('metro_einvoice_datapost.peppol_api_dictionary_call_in_sales', {
              });
                  break;
              default:
              self.do_action('metro_einvoice_datapost.peppol_api_dictionary_call_in_sales', {
              });
          }

        }
    });

    var SearchButtonKanbannView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: SearchButtonKanbannViewContoller,
        }),
    });

    viewRegistry.add('kanban_res_partner_search_button', SearchButtonKanbannView);
});
