
odoo.define('partner.autocomplete.fieldchar.peppol', function (require) {
'use strict';

var basic_fields = require('web.basic_fields');
var core = require('web.core');
var field_registry = require('web.field_registry');
var Widget = require("web.Widget");
var _t = core._t;

var QWeb = core.qweb;

var FieldChar = basic_fields.FieldChar;
var FieldAutocompletePeppol = FieldChar.extend( {
    className: 'o_field_partner_autocomplete_peppol',
    debounceSuggestions: 400,
    resetOnAnyFieldChange: true,

    jsLibs: [
        '/partner_autocomplete/static/lib/jsvat.js'
    ],

    events: _.extend({}, FieldChar.prototype.events, {
        'keyup': '_onKeyup',
        'mousedown .o_partner_autocomplete_suggestion_peppol': '_onMousedown',
        'focusout': '_onFocusout',
        'mouseenter .o_partner_autocomplete_suggestion_peppol': '_onHoverDropdown',
        'click .o_partner_autocomplete_suggestion_peppol': '_onSuggestionClicked',
    }),

    init: function () {
        this._super.apply(this, arguments);
        if (this.mode === 'edit') {
            this.tagName = 'div';
            this.className += ' dropdown open peppol';
        }

        if (this.debounceSuggestions > 0) {
            this._suggestCompanies = _.debounce(this._suggestCompanies.bind(this), this.debounceSuggestions);
        }
    },

    _isActive: function () {
        return this.model === 'res.company' ||
            (
                this.model === 'res.partner'
                && this.record.data.is_company
                && !(this.record.data && this.record.data.id)
            );
    },


    _removeDropdown: function () {
        if (this.$dropdown) {
            this.$dropdown.remove();
            this.$dropdown = undefined;
        }
    },
    _renderEdit: function () {
        this.$el.empty();
        // Prepare and add the input
        this._prepareInput().appendTo(this.$el);
    },

    _selectCompany: function (company) {
      var self = this;
      var values ={};

      values ['name'] = company.description;
      values ['country_id'] = "SG";
      // var timestamp = 1607110465663
      var date = new Date(company.registered);

      values["peppol_registered_date"] = date.getFullYear()+"-"+(date.getMonth()+1)+"-"+date.getDate();
      var self = this;
      this._rpc({
          model: 'res.partner',
          method: 'update_country_regdate',
          args: [values.country_id,values.peppol_registered_date],

      }).then(function (result) {
              self.trigger_up('field_changed', {
                  dataPointID: self.dataPointID,
                  changes: {
                      country_id: {id: result.country_id},
                      name:company.description,
                      // peppol_identifier:company.label,
                      // peppol_registered_date:"2021-10-28",
                      // peppol_registered_date:"2021/10/28",
                      },
                  viewType: self.viewType,
                  onSuccess: function () {
                               self.$input.val(self._formatValue(company.label));


                  },
              });
      });
      // this.trigger_up('field_changed',
      // {
      // dataPointID: this.dataPointID,
      // changes: values,
      // viewType: this.viewType,
      // onSuccess: function () {
      //         self.$input.val(self._formatValue(company.label));
      // },
      // });
        this._removeDropdown();
    },
    _showDropdown: function (data_peppl) {
        this._removeDropdown();
        if (data_peppl['participants'].length > 0) {

          var suggestions_a = [];
          let matches = data_peppl['participants']
          for (var i = 0, l = matches.length; i < l; i++) {
            var sgdict = {};
            sgdict['description'] = matches[i]['businessEntityDtos'][0]['multilingualNameDtos'][0]['name']
            sgdict['label'] = matches[i]['participantIdentifier']['participantIdentifierValue'];
            sgdict['country'] = matches[i]['businessEntityDtos'][0]['countryCode'];
            sgdict['registered'] = matches[i]['registered'];
            suggestions_a.push(sgdict);
          }
            this.suggestions_obj = suggestions_a

            this.$dropdown = $(QWeb.render('partner_peppol_autocomplete.dropdown', {
                suggestions: suggestions_a,
            }));
            this.$dropdown.appendTo(this.$el);
        }
        else{
            this._removeDropdown();
            this.do_warn( false,_t("Matches Not Found") );
        }
    },

    _suggestCompanies: function (value) {
        var self = this;

        var request = new XMLHttpRequest();
//        let  url_peppol = "https://directory.peppol.eu/search/1.0/json?q="+value;
        let url_peppol = "https://api.peppoldirectory.sg/public/web/search?sortBy=registered&sortDirection=DESC&freeText="+value+"&limit=100"
        try {
          request.open('GET', url_peppol, true)
          request.onload = function () {

            if (request.status == 200 ) {
              var data_peppl = JSON.parse(this.response);
              if (data_peppl && data_peppl.count > 0) {
                  self._showDropdown(data_peppl);
              } else {
                  self._removeDropdown();
              }

            } else {
              self.do_warn( _t("Service Not working"), ('<ul><li>Service Not working</li></ul>'));
            }
          }
        } catch (e) {
          self.do_warn( _t("Service Not working"), ('<ul><li>Service Not working</li></ul>'));
        }


        request.send()


    },
    _onFocusout: function () {
        this._removeDropdown();
    },

    _onHoverDropdown: function (e) {
        this.$dropdown.find('.active').removeClass('active');
        $(e.currentTarget).parent().addClass('active');
    },

    _onInput: function () {
        this._super.apply(this, arguments);
        if (this._isActive()) {
            let w = this.$input.val()
            this._suggestCompanies(w);
        }
    },


    _onKeydown: function (e) {
        switch (e.which) {
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
                if (!this.$dropdown) {
                    break;
                }
                e.preventDefault();
                var $suggestions = this.$dropdown.children();
                var $active = $suggestions.filter('.active');
                var $to;
                if ($active.length) {
                    $to = e.which === $.ui.keyCode.DOWN ?
                        $active.next() :
                        $active.prev();
                } else {
                    $to = $suggestions.first();
                }
                if ($to.length) {
                    $active.removeClass('active');
                    $to.addClass('active');
                }
                return;
        }
        this._super.apply(this, arguments);
    },

    _onKeyup: function (e) {
        switch (e.which) {
            case $.ui.keyCode.ESCAPE:
                e.preventDefault();
                this._removeDropdown();
                break;
            case $.ui.keyCode.ENTER:

                if (!this.$dropdown) {
                    break;
                }

                e.preventDefault();
                var $active = this.$dropdown.find('.o_partner_autocomplete_suggestion_peppol.active');
                if (!$active.length) {
                    return;
                }
                this._selectCompany(this.suggestions_obj[$active.data('index')]);
                break;
        }
    },

    _onMousedown: function (e) {
        e.preventDefault(); // prevent losing focus on suggestion click
    },

    _onSuggestionClicked: function (e) {
        e.preventDefault();
        this._selectCompany(this.suggestions_obj[$(e.currentTarget).data('index')]);
    },
});

field_registry.add('field_peppol_autocomplete', FieldAutocompletePeppol);

return FieldAutocompletePeppol;
});
