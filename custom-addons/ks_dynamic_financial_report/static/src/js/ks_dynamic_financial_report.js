odoo.define('ks_dynamic_financial_report.dynamic_report', function (require) {
    'use strict';
    var core = require('web.core');
    var Context = require('web.Context');
    var AbstractAction = require('web.AbstractAction');
    var Dialog = require('web.Dialog');
    var datepicker = require('web.datepicker');
    var session = require('web.session');
    var ajax = require('web.ajax');
    var field_utils = require('web.field_utils');
    var RelationalFields = require('web.relational_fields');
    var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
    var WarningDialog = require('web.CrashManager').WarningDialog;
    var Widget = require('web.Widget');



    var QWeb = core.qweb;
    var _t = core._t;


    var ksMany2ManyWidget = Widget.extend(StandaloneFieldManagerMixin, {
        /**
         * @override
         * @method to set fields
         */
        init: function (parent, fields) {
            this._super.apply(this, arguments);
            StandaloneFieldManagerMixin.init.call(this);
            this.fields = fields;
            this.widgets = {};

        },
        /**
         * @override
         * @method to initialise the many2many widget
         */
        willStart: function () {
            var self = this;
            var defs = [this._super.apply(this, arguments)];
            _.each(this.fields, function (field, fieldName) {
                defs.push(self._ksInitMany2ManyWidget(field, fieldName));
            });
            return Promise.all(defs);
        },

        /**
         * @override
         * @method to render many2many widget
         */
        start: function () {
            var self = this;
            var $content = $(QWeb.render("ksMany2ManyWidgetStructure", {
                fields: this.fields
            }));
            self.$el.append($content);
            _.each(this.fields, function (field, fieldName) {
                self.widgets[fieldName].appendTo($content.find('#' + fieldName + '_field'));
            });
            return this._super.apply(this, arguments);
        },

        _confirmChange: function () {
            var self = this;
            var result = StandaloneFieldManagerMixin._confirmChange.apply(this, arguments);
            var data = {};
            _.each(this.fields, function (filter, fieldName) {
                data[fieldName] = self.widgets[fieldName].value.res_ids;
            });
            this.trigger_up('ks_value_modified', data);
            return result;
        },

        /**
         * This method will create a record and initialize M2M widget.
         *
         * @private
         * @param {Object} fieldInfo
         * @param {string} fieldName
         * @returns {Promise}
         */
        _ksInitMany2ManyWidget: function (fieldInfo, fieldName) {
            var self = this;
            var options = {};
            options[fieldName] = {
                options: {
                    no_create_edit: true,
                    no_create: true,
                }
            };
            return this.model.makeRecord(fieldInfo.modelName, [{
                fields: [{
                    name: 'id',
                    type: 'integer',
                }, {
                    name: 'display_name',
                    type: 'char',
                }],
                name: fieldName,
                relation: fieldInfo.modelName,
                type: 'many2many',
                value: fieldInfo.value,
            }], options).then(function (recordID) {
                self.widgets[fieldName] = new RelationalFields.FieldMany2ManyTags(self,
                    fieldName,
                    self.model.get(recordID), {
                        mode: 'edit',
                    }
                );
                self._registerWidget(recordID, fieldName, self.widgets[fieldName]);
            });
        },
    });


    var ksDynamicReportsWidget = AbstractAction.extend({
        hasControlPanel: true,
        events: {
            'click .ks_py-mline': 'ksGetMoveLines',
            'click .ks_py-mline-page': 'ksGetMoveLines',
            'click .ks_pl-py-mline': 'ksGetPlMoveLines',
            'click .ks_pr-py-mline': 'ksGetAgedLinesInfo',
            'click .ks_cj-py-mline': 'ksGetConsolidateInfo',
            'click .ks_report_pdf': 'ksReportPrintPdf',
            'click .ks_report_xlsx': 'ksPrintReportXlsx',
            'click [action]': 'ksGetAction',
            'click .ks_send_email': "ksReportSendEmail",
            'hide.bs.dropdown': "ksHideDropDown",
            'click .o_control_panel': 'ksRemoveDisplayClass',
            'click .ks_thead': 'ksRemoveDisplayClass',
            'click .o_main_navbar': 'ksRemoveDisplayClass',
            'keyup .ks_input': 'onKsSearchFilter',
            'click .ks_load_previous': 'ksLoadPreviousRecords',
            'click .ks_load_next': 'ksLoadMoreRecords',
            'click .ks_new_text': '_onEdit',
            'change .ks_input_text': 'ksGetAgedLinesInfo',
            'blur .ks_input_text' :'ks_input_text_blur',
            'click .ks_upper_pager_count':'_onEdit',
            'blur .ks_input_text_upper' :'ks_input_text_blur',
            'change .ks_input_text_upper': 'ks_load_pager_rec',
            'change .ks_input_text-pl': 'ksGetPlMoveLines',
            'change .ks_input_text-py':'ksGetMoveLines',

            'click .agedlines_child': 'agedLinesOpenForm',
        },

        ksRemoveDisplayClass: function(evt){
            $('.o_filter_menu').removeClass('ks_d_block')
        },

        custom_events: {
            ks_value_modified :'ksPerformOnchange',
        },
        onKsSearchFilter: function(ev){

            var ks_input = ev.currentTarget.value;
            var ks_filter = ks_input.toUpperCase();

            var ks_accounts = $(ev.currentTarget.parentElement).find('.js_account_report_choice_filter');
            for (var i = 0; i < ks_accounts.length; i++) {
                var txtValue = ks_accounts[i].textContent || ks_accounts[i].innerText;
                if (txtValue.toUpperCase().indexOf(ks_filter) > -1) {
                    $($(ev.currentTarget.parentElement).find('.js_account_report_choice_filter')[i]).removeClass('ks_d_none')
                } else {
                    $($(ev.currentTarget.parentElement).find('.js_account_report_choice_filter')[i]).addClass('ks_d_none')
                }
            }
        },

        /**
         * @override
         */
        init: function (parent, action) {
            console.log("\ninit() >>>>>>>")
            var self = this;
            self.ksSetInitObjects(parent, action);
            self.ksStorageKeyOpt(action);
            return self._super.apply(self, arguments);
        },

        /**
         * @override
         */
        willStart: async function () {
            console.log("\nwillStart() >>>>>>")
            const ksDynRepInfoProm = this._rpc({
                model: this.ks_dyn_fin_model,
                method: 'ks_get_dynamic_fin_info',
                args: [this.ks_report_id, this.ks_df_report_opt],
                context: this.ks_df_context,
            }).then(res => this.ksSetDfRepInfo(res));
            const ksParentProm = this._super(...arguments);
            return Promise.all([ksDynRepInfoProm, ksParentProm]);
        },

        /**
         * @override
         * @default method of widget to update control-panel and render view
         */
        start: async function () {
            console.log("\nstart() >>>>>>>")
            this.controlPanelProps.cp_content = {
                $searchview_buttons: this.$ks_searchview_buttons,
                $pager: this.$pager,
                $searchview: this.$searchview,
            };
            await this._super(...arguments);
            this.ksRenderReport();
        },

        /**
         * @method to set init objects
         */
        ksSetInitObjects: function (parent, action) {
            this.actionManager = parent;
            this.ks_dyn_fin_model = action.context.model;
            if (this.ks_dyn_fin_model === undefined) {
                this.ks_dyn_fin_model = 'ks.dynamic.financial.base';
            }
            this.ks_report_id = false;
            if (action.context.id) {
                this.ks_report_id = action.context.id;
            }
            this.ks_df_context = action.context;
            this.ks_df_report_opt = action.ks_df_informations || false;
            this.ignore_session = action.ignore_session;
        },

        /**
         * @method to stop-propagation of inner dropdown
         */
        ksHideDropDown: function (event) {
            if (!event.clickEvent) {
                return true;
            }
            var target = $(event.clickEvent.target);
            return !(target.hasClass('ks_stop_propagation') || target.parents('.ks_stop_propagation').length);
        },

        /**
         * @method to perform onchange on values
         */
        ksPerformOnchange: function (ev) {
            var self = this;
            self.ks_df_report_opt.ks_partner_ids = ev.data.ks_partner_ids;
            self.ks_df_report_opt.analytic_accounts = ev.data.ks_analytic_ids;
            self.ks_df_report_opt.analytic_tags = ev.data.ks_analytic_tag_ids;
            return self.ksReloadReport().then(function () {
                self.$ks_searchview_buttons.find('.ks_df_partner_filter').click();
                self.$ks_searchview_buttons.find('.ks_df_analytic_filter').click();
            });
        },

        /**
         * @method to set/get Storage keys
        */
        ksStorageKeyOpt: function (action = false) {
            let action_this = action || this;
            let self = this;
            if ((action_this.ignore_session === 'read' || action_this.ignore_session === 'both') !== true) {
                var ks_df_report_key = 'report:' + self.ks_dyn_fin_model + ':' + self.ks_report_id + ':' + session.company_id;
                action ? self.ksGetStorageKey(ks_df_report_key) : self.ksSetStorageKey(ks_df_report_key);
            }
        },

        /**
         * @method to print the report pdf
        */
        ksReportPrintPdf: function (e) {
            console.log("\n1111ksReportPrintPdf() >>>>")
            var self = this;
               if ((this.controlPanelProps.action.xml_id == _t('ks_dynamic_financial_report.ks_df_gl_action'))||
            (this.controlPanelProps.action.xml_id == _t("ks_dynamic_financial_report.ks_df_rec_action")) ||
             (this.controlPanelProps.action.xml_id == _t('ks_dynamic_financial_report.ks_df_pl_action'))||
            (this.controlPanelProps.action.xml_id == _t("ks_dynamic_financial_report.ks_df_pay_action"))) {

                this.ks_df_context['OFFSET']=true
                }
            this._rpc({
                model: this.ks_dyn_fin_model,
                method: 'ks_get_dynamic_fin_info',
                args: [this.ks_report_id, this.ks_df_report_opt],
                context: this.ks_df_context,
            }).then(function (data) {
                console.log("\ndata====",data)
                var report_name = self.ksGetReportName();
                console.log(report_name)
                if ((report_name == 'ks_dynamic_financial_report.ks_account_balance_sheet_lines' || report_name == 'ks_dynamic_financial_report.ks_account_profit_and_loss_lines') && data.ks_report_lines) {
                    // Metro Code starts
                    data.ks_report_lines.forEach(function (line) {
                        if (line.hasOwnProperty('account') && line.account) {
                            let st = line.ks_name
                            line.ks_name = st.slice(st.indexOf(' ') + 1);
                        }                    
                    });                
                    // Ends
                }
                var action = self.ksGetReportAction(report_name,data);
                return self.do_action(action);
            });
        },

        /**
         * @method to get report name
        */
        ksGetReportName: function(){
            var self = this;
            if (self._title == _t('Trial Balance')) {
                return 'ks_dynamic_financial_report.ks_account_report_trial_balance';
            } else if (self._title == _t('General Ledger')) {
                return 'ks_dynamic_financial_report.ks_dynamic_financial_general_ledger';
            } else if (self._title == _t('Partner Ledger')) {
                return 'ks_dynamic_financial_report.ks_dynamic_financial_partner_ledger';
            } else if (self._title == _t('Age Receivable')) {
                return 'ks_dynamic_financial_report.ks_dynamic_financial_age_receivable';
            } else if (self._title == _t('Age Payable')) {
                return 'ks_dynamic_financial_report.ks_dynamic_financial_age_payable';
            } else if (self._title == _t('Consolidate Journal')) {
                return 'ks_dynamic_financial_report.ks_dynamic_financial_consolidate_journal';
            } else if (self._title == _t('Tax Report')) {
                return 'ks_dynamic_financial_report.ks_dynamic_financial_tax_report';
            } else if (self._title == _t('Executive Summary')) {
                return 'ks_dynamic_financial_report.ks_df_executive_summary';
            } else if (self._title == _t('Profit and Loss')) {
                return 'ks_dynamic_financial_report.ks_account_profit_and_loss_lines';
            } else if (self._title == _t('Balance Sheet')) {
                return 'ks_dynamic_financial_report.ks_account_balance_sheet_lines';
            } else {
                return 'ks_dynamic_financial_report.ks_account_report_lines';
            }
        },

        /**
         * @method to get report action
        */
        ksGetReportAction: function(report_name,data)   {
            var self = this;
            return {
                'type': 'ir.actions.report',
                'report_type': 'qweb-pdf',
                'report_name': report_name,
                'report_file': report_name,
                'data': {
                    'js_data': data
                },
                'context': {
                    'active_model': self.ks_dyn_fin_model,
                    'landscape': 0,
                    'from_js': true
                },
                'display_name': self._title,
            };
        },
        
        /**
         * @method to send report email to user 
        */
        ksReportSendEmail: function (e) {
            e.preventDefault();
            var self = this;
            this._rpc({
                model: this.ks_dyn_fin_model,
                method: 'ks_get_dynamic_fin_info',
                args: [this.ks_report_id, this.ks_df_report_opt],
                context: this.ks_df_context,
            }).then(function (data) {
                var ks_report_action = self.ksGetReportActionName();
                self._rpc({
                    model: self.ks_dyn_fin_model,
                    method: 'ks_action_send_email',
                    args: [self.ks_report_id, data, ks_report_action],
                    context: data['context'],
                });
            });
        },
        
        /**
         * @method to get report action name
        */
        ksGetReportActionName: function(){
            var self = this;
            
            if (self._title == _t('Trial Balance')) {
                return 'ks_dynamic_financial_report.ks_dynamic_financial_trial_bal_action';
            } else if (self._title == _t('General Ledger')) {
                return 'ks_dynamic_financial_report.ks_dynamic_financial_gel_bal_action';
            } else if (self._title == _t('Partner Ledger')) {
                return 'ks_dynamic_financial_report.ks_dynamic_financial_partner_led_action';
            } else if (self._title == _t('Age Receivable')) {
                return 'ks_dynamic_financial_report.ks_dynamic_financial_age_rec_action';
            } else if (self._title == _t('Age Payable')) {
                return 'ks_dynamic_financial_report.ks_dynamic_financial_age_pay_action';
            } else if (self._title == _t('Consolidate Journal')) {
                return 'ks_dynamic_financial_report.ks_dynamic_financial_cons_journal_action';
            } else if (self._title == _t('Tax Report')) {
                return 'ks_dynamic_financial_report.ks_dynamic_financial_tax_action';
            } else if (self._title == _t('Executive Summary')) {
                return 'ks_dynamic_financial_report.ks_dynamic_financial_executive_action';
            } else if (self._title == _t('Profit and Loss')) {
                return 'ks_dynamic_financial_report.ks_profit_and_loss_financial_report_action';
            } else if (self._title == _t('Balance Sheet')) {
                return 'ks_dynamic_financial_report.ks_balance_sheet_financial_report_action';
            } else {
                return 'ks_dynamic_financial_report.ks_dynamic_financial_report_action';
            }
        },
        
        /**
         * @method to print report excel
        */
        ksPrintReportXlsx: function () {
            var self = this;
            self._rpc({
                model: this.ks_dyn_fin_model,
                method: 'ks_print_xlsx',
                args: [this.ks_report_id, this.ks_df_report_opt],
                context: this.ks_df_context
            }).then(function (action) {
                return self.do_action(action);
            });
        },

        /**
         * @method to set report Information
        */
        ksSetReportInfo: function (values) {
            console.log("\nksSetReportInfo() >>> values = ",values.ks_df_informations)
            this.ks_df_reports_ids= values.ks_df_reports_ids;
            this.ks_df_report_opt = values.ks_df_informations;
            this.ks_df_context = values.context;
            this.ks_report_manager_id = values.ks_report_manager_id;
            this.ks_remarks = values.ks_remarks;
            this.$ks_buttons = $(values.ks_buttons);
            this.$ks_searchview_buttons = $(values.ks_searchview_html);
            this.ks_currency = values.ks_currency;
            this.ks_report_lines = values.ks_report_lines;
            this.ks_enable_ledger_in_bal = values.ks_enable_ledger_in_bal;
            this.ks_initial_balance = values.ks_initial_balance;
            this.ks_current_balance = values.ks_current_balance;
            this.ks_ending_balance = values.ks_ending_balance;
            this.ks_diff_filter = values.ks_diff_filter;
            this.ks_retained = values.ks_retained;
            this.ks_subtotal = values.ks_subtotal;
            this.ks_partner_dict = values.ks_partner_dict
            this.ks_period_list = values.ks_period_list
            this.ks_period_dict = values.ks_period_dict
            this.ks_month_lines = values.ks_month_lines
            this.ksSaveReportInfo();
        },
        
        /**
         * @method to save the report Information in current session
        */
        ksSaveReportInfo: function () {
            if ((this.ignore_session === 'write' || this.ignore_session === 'both') !== true) {
                var ks_df_report_key = 'report:' + this.ks_dyn_fin_model + ':' + this.ks_report_id + ':' + session.company_id;
                sessionStorage.setItem(ks_df_report_key, JSON.stringify(this.ks_df_report_opt));
            }
        },
        
        /**
         * @override
         * @method to rerender the control panel when going back in the breadcrumb
        */
        do_show: function () {
            this._super.apply(this, arguments);
            this.ksUpdateControlPanel();
        },
        
        /**
         * @method to render the elements that have yet to be rendered
        */ 
        ksUpdateControlPanel: function () {
            var status = {
                cp_content: {
                    $buttons: this.$ks_buttons,
                    $searchview_buttons: this.$ks_searchview_buttons,
                    $pager: this.$pager,
                    $searchview: this.$searchview,
                },
            };
            return this.updateControlPanel(status);
        },
        
        /**
         * @method to reload the report content
        */ 
        ksReloadReport: function () {
            console.log("\n\nksReloadReport() >>>>>")
            console.log(this)
            var self = this;
            return this._rpc({
                    model: this.ks_dyn_fin_model,
                    method: 'ks_get_dynamic_fin_info',
                    args: [self.ks_report_id, self.ks_df_report_opt],
                    context: self.ks_df_context,
                })
                .then(function (result) {
                    console.log("   rpc then result ===",result)
                    self.ksSetReportInfo(result);
                    self.ksRenderReport();
                    return self.ksUpdateControlPanel();
                });
        },
        
        /**
         * @method to render report body
         */
        ksRenderReport: function () {
            console.log("\n\nksRenderReport() >>>>")
            var self = this;
            this.ksRenderMainTemplate();
            this.ksRenderSearchViewButtons();
            this.ksUpdateControlPanel();
        },

        /**
         * @method to get general ledger line by page
        */
        ksGetGlLineByPage: function (offset, account_id) {
            var self = this;

            return self._rpc({
                model: self.ks_dyn_fin_model,
                method: 'ks_build_detailed_gen_move_lines',
                args: [self.ks_report_id, offset, account_id, self.ks_df_report_opt],
            });
        },

        /**
         * @method to get move line by page
        */
        ksGetMoveLines: function (event) {
            console.log("\nksGetMoveLines() >>>>>")
            event.preventDefault();

            $('.o_filter_menu').removeClass('ks_d_block')
            var self = this;
            var account_id = $(event.currentTarget).data('account-id');
            var account = $(event.currentTarget).data('account')
            var offset =0;
            if ($(event.target).hasClass('ks_input_text-py')){
                offset = parseInt(event.target.value)-1;
                $(event.target).addClass("d-none");
                $(event.target).parent().find(".ks_new_text").removeClass("d-none");
                $(event.currentTarget).parent().find(".ks_new_text")[0].innerText = event.target.value
                if (offset>0 && offset<this.ks_report_lines[account]['pages'].length){
                    $(event.currentTarget).parent().find(".ks_load_previous_new").removeClass("ks_event_offer_list_new")
                }else{
                    $(event.currentTarget).parent().find(".ks_load_previous_new").addClass("ks_event_offer_list_new")
                }
                if (parseInt(event.target.value) === this.ks_report_lines[account]['pages'].length ){
                    $(event.currentTarget).parent().find(".ks_load_next_new").addClass("ks_event_offer_list_new")
                }else{
                    $(event.currentTarget).parent().find(".ks_load_next_new").removeClass("ks_event_offer_list_new")
                }
            }
            if ($(event.currentTarget).hasClass("ks_load_next_new")||$(event.currentTarget).hasClass("ks_load_previous_new")){
                console.log("this.ks_report_lines[account]['pages'].length ==",this.ks_report_lines[account]['pages'].length)
                var pages_length = this.ks_report_lines[account]['pages'].length
                var ks_page_number = parseInt($(event.currentTarget).parent().parent().find(".ks_new_text")[0].innerText);
                console.log("ks_page_number ===",ks_page_number)
                console.log("pages_length > ks_page_number ===",pages_length > ks_page_number)
                if ($(event.currentTarget).hasClass("ks_load_next_new")){
                    if (ks_page_number >= pages_length) {
                        console.log("returning.....")
                        return
                    } else {
                        $(event.currentTarget).parent().find(".ks_event_offer_list_new").removeClass("ks_event_offer_list_new")
                        $(event.currentTarget).parent().parent().find(".ks_new_text")[0].innerText = `${ks_page_number+1}`
                        console.log("Settinggggggggg")
                        offset = ks_page_number
                    }
                }else if ($(event.currentTarget).hasClass("ks_load_previous_new")){
                    if (ks_page_number <= 1) {
                        return
                    } else {
                        $(event.currentTarget).parent().parent().find(".ks_new_text")[0].innerText = `${ks_page_number-1}`
                        offset = ks_page_number-2;
                    }
                }

            }
            if ($(event.currentTarget).hasClass("ks_load_next_new")||$(event.currentTarget).hasClass("ks_load_previous_new")){
                if (ks_page_number ==2 && $(event.currentTarget).hasClass("ks_load_previous_new")){
                    $(event.currentTarget).parent().find(".ks_load_previous_new").addClass("ks_event_offer_list_new")
                }
                if (ks_page_number+1 === this.ks_report_lines[account]['pages'].length){
                    $(event.currentTarget).parent().find(".ks_load_next_new").addClass("ks_event_offer_list_new")
                }else{
                    $(event.currentTarget).parent().find(".ks_load_next_new").removeClass("ks_event_offer_list_new")
                }
            }
//            var offset = $(event.currentTarget).data('offset');
            var td = $(event.currentTarget).next('tr').find('td');

            if ((td.length == 1 || $(event.target).hasClass('ks_py-mline-page') ||$(event.target).hasClass('ks_input_text-py')) && (offset>=0 && offset<this.ks_report_lines[account]['pages'].length))  {
                self.ksGetGlLineByPage(offset, account_id).then(function (datas) {
                    _.each(datas[2], function (k, v) {
                        var ksFormatConfigurations = {
                            currency_id: k.company_currency_id,
                            noSymbol: true,
                        };
                        k.debit = self.ksFormatCurrencySign(k.debit, ksFormatConfigurations, k.debit < 0 ? '-' : '');
                        k.credit = self.ksFormatCurrencySign(k.credit, ksFormatConfigurations, k.credit < 0 ? '-' : '');
                        k.balance = self.ksFormatCurrencySign(k.balance, ksFormatConfigurations, k.balance < 0 ? '-' : '');
                        k.initial_balance = self.ksFormatCurrencySign(k.initial_balance, ksFormatConfigurations, k.initial_balance < 0 ? '-' : '');
                        k.ldate = field_utils.format.date(field_utils.parse.date(k.ldate, {}, {
                            isUTC: true
                        }));
                    });

                   if ($(event.target).hasClass('ks_py-mline-page') || $(event.target).hasClass('ks_input_text-py')) {
                        var $ks_el = QWeb.render('ks_df_gl_subsection', {
                                count: datas[0],
                                offset: datas[1],
                                account_data: datas[2],
                                account_id:account_id,
                                ks_enable_ledger_in_bal: self.ks_enable_ledger_in_bal,
                            })
                        $('.ks_py-mline-page').removeClass('ks_high_light_page')
                        $(".ks_py-mline-table-div" +account_id).replaceWith($ks_el)
                        $(event.target).addClass('ks_high_light_page')
                    }else {
                        $(event.currentTarget).next('tr').find('td .ks_py-mline-table-div').remove();
                        $(event.currentTarget).next('tr').find('td ul').after(
                            QWeb.render('ks_df_gl_subsection', {
                                count: datas[0],
                                offset: datas[1],
                                account_data: datas[2],
                                account_id : account_id,
                                ks_enable_ledger_in_bal: self.ks_enable_ledger_in_bal,
                            }))
                        $(event.currentTarget).next('tr').find('td ul li:first a').addClass("ks_high_light_page")
                    }
                })
            }
        },

        /**
         * @method to get profit and loss lines by page
        */
        ksGetPlLinesByPage: function (offset, account_id) {
            var self = this;
            return self._rpc({
                model: self.ks_dyn_fin_model,
                method: 'ks_build_detailed_move_lines',
                args: [self.ks_report_id, offset, account_id, self.ks_df_report_opt, self.$ks_searchview_buttons.find('.ks_search_account_filter').length],
            })

        },

        /**
         * @method to get profit and loss move lines
        */
        ksGetPlMoveLines: function (event) {
             $('.o_filter_menu').removeClass('ks_d_block')

            event.preventDefault();
            var self = this;
            var account_id = $(event.currentTarget).data('account-id');
            var offset = 0;
            var td = $(event.currentTarget).next('tr').find('td');
            if (td.length == 1) {
                self.ksGetPlLinesByPage(offset, account_id).then(function (datas) {
                    _.each(datas[2], function (k, v) {
                        var ksFormatConfigurations = {
                            currency_id: k.company_currency_id,
                            noSymbol: true,
                        };
                        k.debit = self.ksFormatCurrencySign(k.debit, ksFormatConfigurations, k.debit < 0 ? '-' : '');
                        k.credit = self.ksFormatCurrencySign(k.credit, ksFormatConfigurations, k.credit < 0 ? '-' : '');
                        k.balance = self.ksFormatCurrencySign(k.balance, ksFormatConfigurations, k.balance < 0 ? '-' : '');
                        k.initial_balance = self.ksFormatCurrencySign(k.initial_balance, ksFormatConfigurations, k.initial_balance < 0 ? '-' : '');
                        k.ldate = field_utils.format.date(field_utils.parse.date(k.ldate, {}, {
                            isUTC: true
                        }));
                    });
                    $(event.currentTarget).next('tr').find('td .ks_py-mline-table-div').remove();
                    $(event.currentTarget).next('tr').find('td ul').after(
                        QWeb.render('ks_df_sub_pl0', {
                            count: datas[0],
                            offset: datas[1],
                            account_data: datas[2],
                            ks_enable_ledger_in_bal: self.ks_enable_ledger_in_bal,
                        }))
                    $(event.currentTarget).next('tr').find('td ul li:first a').css({
                        'background-color': '#00ede8',
                        'font-weight': 'bold',
                    });
                })
            }
        },
        
        /**
         * @method to get Aged Report move lines detailed information
        */
        ksGetAgedReportDetailedInfo: function (offset, partner_id) {
            var self = this;
            return self._rpc({
                model: self.ks_dyn_fin_model,
                method: 'ks_process_aging_data',
                args: [self.ks_report_id, self.ks_df_report_opt, offset, partner_id],
            })
        },

        /**
         * @method to get Aged Report lines information
        */
        ksGetAgedLinesInfo: function (event) {
             $('.o_filter_menu').removeClass('ks_d_block')
            event.preventDefault();
            var self = this;
            var partner_id = $(event.currentTarget).data('partner-id');
            var offset = 0;
            var td = $(event.currentTarget).next('tr').find('td');
            if (td.length == 1) {
                self.ksGetAgedReportDetailedInfo(offset, partner_id).then(function (datas) {
                    var count = datas[0];
                    var offset = datas[1];
                    var account_data = datas[2];
                    var period_list = datas[3];
                    _.each(account_data, function (k, v) {
                        var ksFormatConfigurations = {
                            currency_id: k.company_currency_id,
                            noSymbol: true,
                        };
                        k.range_0 = self.ksFormatCurrencySign(k.range_0, ksFormatConfigurations, k.range_0 < 0 ? '-' : '');
                        k.range_1 = self.ksFormatCurrencySign(k.range_1, ksFormatConfigurations, k.range_1 < 0 ? '-' : '');
                        k.range_2 = self.ksFormatCurrencySign(k.range_2, ksFormatConfigurations, k.range_2 < 0 ? '-' : '');
                        k.range_3 = self.ksFormatCurrencySign(k.range_3, ksFormatConfigurations, k.range_3 < 0 ? '-' : '');
                        k.range_4 = self.ksFormatCurrencySign(k.range_4, ksFormatConfigurations, k.range_4 < 0 ? '-' : '');
                        k.range_5 = self.ksFormatCurrencySign(k.range_5, ksFormatConfigurations, k.range_5 < 0 ? '-' : '');
                        k.range_6 = self.ksFormatCurrencySign(k.range_6, ksFormatConfigurations, k.range_6 < 0 ? '-' : '');
                        k.date_maturity = field_utils.format.date(field_utils.parse.date(k.date_maturity, {}, {
                            isUTC: true
                        }));
                    });
                    $(event.currentTarget).next('tr').find('td .ks_py-mline-table-div').remove();
                    $(event.currentTarget).next('tr').find('td ul').after(
                        QWeb.render('ks_df_sub_receivable0', {
                            count: count,
                            offset: offset,
                            account_data: account_data,
                            period_list: period_list
                        }))
                    $(event.currentTarget).next('tr').find('td ul li:first a').css({
                        'background-color': '#00ede8',
                        'font-weight': 'bold',
                    });
                })
            }
        },
        ks_input_text_blur:function(event){
            $(event.target).addClass("d-none");
            if ($(event.target).hasClass('ks_input_text')){
                $(event.target).parent().find(".ks_new_text").removeClass("d-none");
            }
            else{
                $(event.target).parent().find(".ks_new_text_upper").removeClass("d-none");
            }
        },

        _onEdit:function(event){
            event.preventDefault();
            var ks_current_value = event.target.innerText;
            $(event.target).addClass('d-none');
            if ($(event.target).parent().find('.ks_input_text').length!=0){
                $(event.target).parent().find('.ks_input_text').removeClass('d-none');
                $(event.target).parent().find('.ks_input_text')[0].value = ks_current_value;
            }
            else if ($(event.target).parent().find('.ks_input_text-pl').length!=0){
                $(event.target).parent().find('.ks_input_text-pl').removeClass('d-none');
                $(event.target).parent().find('.ks_input_text-pl')[0].value = ks_current_value;
            }else if ($(event.target).parent().find('.ks_input_text-py').length!=0){
                $(event.target).parent().find('.ks_input_text-py').removeClass('d-none');
                $(event.target).parent().find('.ks_input_text-py')[0].value = ks_current_value;
            }
            else{
             $(event.target).parent().find('.ks_input_text_upper').removeClass('d-none');
             $(event.target).parent().find('.ks_input_text_upper')[0].value = ks_current_value;
            }
        },
        /**
         * @method to open the Form
        */
        agedLinesOpenForm: function (event) {
            event.preventDefault();
            var self = this
            var moveId =  parseInt($(event.currentTarget).data('move-id'))
            return self._rpc({
                model: 'ks.dynamic.financial.base',
                method: 'ks_df_show_move_line',
                args:[self.ks_report_id, false, {'moveId': moveId}]
            }).then(function(result) {
                self.do_action(result);
            });
        },
        
        /**
         * @method to get Consolidate lines by page
        */
        ksGetConsolidateLinesByPage: function (offset, ks_journal_id) {
            var self = this;
            return self._rpc({
                model: self.ks_dyn_fin_model,
                method: 'ks_consolidate_journals_details',
                args: [self.ks_report_id, offset, ks_journal_id, self.ks_df_report_opt],
            })
        },

        /**
         * @method to get Consolidate move lines
        */
        ksGetConsolidateInfo: function (event) {
             $('.o_filter_menu').removeClass('ks_d_block')
            event.preventDefault();
            var self = this;
            var ks_journal_id = $(event.currentTarget).data('journal-id');
            var offset = 0;
            var td = $(event.currentTarget).next('tr').find('td');
            if (td.length == 1) {
                self.ksGetConsolidateLinesByPage(offset, ks_journal_id).then(function (datas) {
                    var offset = datas[0];
                    var account_data = datas[1];
                    _.each(account_data, function (k, v) {
                        var ksFormatConfigurations = {
                            currency_id: k.company_currency_id,
                            noSymbol: true,
                        };
                        k.debit = self.ksFormatCurrencySign(k.debit, ksFormatConfigurations, k.debit < 0 ? '-' : '');
                        k.credit = self.ksFormatCurrencySign(k.credit, ksFormatConfigurations, k.credit < 0 ? '-' : '');
                        k.balance = self.ksFormatCurrencySign(k.balance, ksFormatConfigurations, k.balance < 0 ? '-' : '');
                        k.ldate = field_utils.format.date(field_utils.parse.date(k.ldate, {}, {
                            isUTC: true
                        }));
                    });
                    $(event.currentTarget).next('tr').find('td .ks_py-mline-table-div').remove();
                    $(event.currentTarget).next('tr').find('td ul').after(
                        QWeb.render('ks_df_cj_subsection', {
                            offset: offset,
                            account_data: account_data,
                        }))
                    $(event.currentTarget).next('tr').find('td ul li:first a').css({
                        'background-color': '#00ede8',
                        'font-weight': 'bold',
                    });
                })
            }
        },

        /**
         * @method to render searchview buttons
        */
        ksRenderSearchViewButtons: function () {
            console.log("\n\nksRenderSearchViewButtons()>>>>>>>>>>>>")
            var self = this;
            // bind searchview buttons/filter to the correct actions

            var $datetimepickers = this.$ks_searchview_buttons.find('.js_account_reports_datetimepicker');
            var options = { // Set the options for the datetimepickers
                locale: moment.locale(),
                format: 'L',
                icons: {
                    date: "fa fa-calendar",
                },
            };
            // attach datepicker
            $datetimepickers.each(function () {
                var name = $(this).find('input').attr('name');
                var defaultValue = $(this).data('default-value');
                $(this).datetimepicker(options);
                var dt = new datepicker.DateWidget(options);
                dt.replace($(this)).then(function () {
                    dt.$el.find('input').attr('name', name);
                    if (defaultValue) { // Set its default value if there is one
                        dt.setValue(moment(defaultValue));
                    }
                });
            });
            // format date that needs to be show in user lang
            _.each(this.$ks_searchview_buttons.find('.js_format_date'), function (dt) {
                var date_value = $(dt).html();
                $(dt).html((new moment(date_value)).format('ll'));
            });
            //        // fold all menu
            this.$ks_searchview_buttons.find('.js_foldable_trigger').click(function (event) {
                $(this).toggleClass('o_closed_menu o_open_menu');
                self.$ks_searchview_buttons.find('.o_foldable_menu[data-filter="' + $(this).data('filter') + '"]').toggleClass('o_closed_menu');
            });
            //        // render filter (add selected class to the options that are selected)
            _.each(self.ks_df_report_opt, function (k) {
                if (k !== null && k.ks_filter !== undefined) {
                    self.$ks_searchview_buttons.find('[data-filter="' + k.ks_filter + '"]').addClass('selected');
                }
                else if(k !== null && k.ks_differentiate_filter !== undefined){
                self.$ks_searchview_buttons.find('[data-filter="' + k.ks_differentiate_filter + '"]').addClass('selected');
                }
            });
            _.each(this.$ks_searchview_buttons.find('.js_account_report_bool_filter'), function (k) {
                $(k).toggleClass('selected', self.ks_df_report_opt[$(k).data('filter')]);
            });
            _.each(this.$ks_searchview_buttons.find('.js_account_report_choice_filter'), function (k) {
                $(k).toggleClass('selected', (_.filter(self.ks_df_report_opt[$(k).data('filter')], function (el) {
                    return '' + el.id == '' + $(k).data('id') && el.selected === true;
                })).length > 0);
            });
            $('.js_account_report_group_choice_filter', this.$ks_searchview_buttons).each(function (i, el) {
                var $el = $(el);
                var ids = $el.data('member-ids');
                $el.toggleClass('selected', _.every(self.ks_df_report_opt[$el.data('filter')], function (member) {
                    // only look for actual ids, discard separators and section titles
                    if (typeof member.id == 'number') {
                        // true if selected and member or non member and non selected
                        return member.selected === (ids.indexOf(member.id) > -1);
                    } else {
                        return true;
                    }
                }));
            });
            _.each(this.$ks_searchview_buttons.find('.js_account_reports_one_choice_filter'), function (k) {
                $(k).toggleClass('selected', '' + self.ks_df_report_opt[$(k).data('filter')] === '' + $(k).data('id'));
            });
            // click events
            this.$ks_searchview_buttons.find('.js_account_report_date_filter').click(function (event) {
                self.ks_df_context.ks_option_enable = false;
                self.ks_df_context.ks_journal_enable = false
                self.ks_df_context.ks_account_enable = false
                self.ks_df_context.ks_account_both_enable = false
                self.ks_df_report_opt.date.ks_filter = $(this).data('filter');
                var error = false;
                if ($(this).data('filter') === 'custom') {
                    var ks_start_date = self.$ks_searchview_buttons.find('.o_datepicker_input[name="ks_start_date"]');
                    var ks_end_date = self.$ks_searchview_buttons.find('.o_datepicker_input[name="ks_end_date"]');
                    if (ks_start_date.length > 0) {
                        error = ks_start_date.val() === "" || ks_end_date.val() === "";
                        self.ks_df_report_opt.date.ks_start_date = field_utils.parse.date(ks_start_date.val());
                        self.ks_df_report_opt.date.ks_end_date = field_utils.parse.date(ks_end_date.val());
                    } else {
                        error = ks_end_date.val() === "";
                        self.ks_df_report_opt.date.ks_end_date = field_utils.parse.date(ks_end_date.val());
                    }
                }
                if (error) {
                    new WarningDialog(self, {
                        title: _t("Odoo Warning"),
                    }, {
                        message: _t("Date cannot be empty")
                    }).open();
                } else {
                    self.ksReloadReport();
                }
            });
            console.log("this.$ks_searchview_buttons =",this.$ks_searchview_buttons)
            this.$ks_searchview_buttons.find('.js_account_report_bool_filter').click(function (event) {
                console.log("\nthis.$ks_searchview_buttons.find('.js_account_report_bool_filter').click()......")
                var option_value = $(this).data('filter');
                console.log("option_value =",option_value)

                self.ks_df_context.ks_option_enable = false;
                self.ks_df_context.ks_journal_enable = false
                self.ks_df_context.ks_account_enable = false
                self.ks_df_context.ks_account_both_enable = false
                var ks_options_enable = false
                if (!$(event.currentTarget).hasClass('selected')){
                    var ks_options_enable = true
                }
                var ks_temp_arr = []
                var ks_options = $(event.currentTarget).parent().find('a')
                for (var i=0; i < ks_options.length; i++){
                    if (ks_options[i].dataset.filter !== option_value){
                        ks_temp_arr.push($(ks_options[i]).hasClass('selected'))
                    }
                }
                if (ks_temp_arr.indexOf(true) !== -1 || ks_options_enable){
                    self.ks_df_context.ks_option_enable = true;
                }else{
                    self.ks_df_context.ks_option_enable = false;
                }

                if(option_value=='ks_comparison_range'){
                    console.log(".....OB1....")
                    var ks_date_range_change = {}
                    ks_date_range_change['ks_comparison_range'] =!self.ks_df_report_opt[option_value]
                    return self._rpc({
                    model: self.ks_dyn_fin_model,
                    method: 'write',
                    args: [self.ks_report_id, ks_date_range_change],
                    }).then(function (res) {
                        self._rpc({
                        model: self.ks_dyn_fin_model,
                        method: 'ks_reload_page',
                        }).then(function (action){
                            self.do_action(action)
                        });
                    });
                }
                else if(option_value!='ks_comparison_range'){
                    console.log("......OB2......")
                    console.log("!self.ks_df_report_opt[option_value] ==",!self.ks_df_report_opt[option_value])
                    self.ks_df_report_opt[option_value]= !self.ks_df_report_opt[option_value]
                }
                if (option_value === 'unfold_all') {
                    self.unfold_all(self.ks_df_report_opt[option_value]);
                }
                self.ksReloadReport();
            });
            $('.js_account_report_group_choice_filter', this.$ks_searchview_buttons).click(function () {
                var option_value = $(this).data('filter');
                var option_member_ids = $(this).data('member-ids') || [];
                var is_selected = $(this).hasClass('selected');
                _.each(self.ks_df_report_opt[option_value], function (el) {
                    // if group was selected, we want to uncheck all
                    el.selected = !is_selected && (option_member_ids.indexOf(Number(el.id)) > -1);
                });
                self.ksReloadReport();
            });
            this.$ks_searchview_buttons.find('.js_account_report_choice_filter').click(function (event) {
                self.ks_df_context.ks_journal_enable = false
                self.ks_df_context.ks_account_enable = false
                self.ks_df_context.ks_account_both_enable = false

                self.ks_df_context.ks_option_enable = false;

                var option_value = $(this).data('filter');
                var option_id = $(this).data('id');

                if (!$(event.currentTarget).hasClass('selected')){
                    var ks_options_enable = true
                }
                var ks_temp_arr = []
                var ks_options = $(event.currentTarget).parent().find('a')
                for (var i=0; i < ks_options.length; i++){
                    if (parseInt(ks_options[i].dataset.id) !== option_id){
                        ks_temp_arr.push($(ks_options[i]).hasClass('selected'))
                    }
                }
                if (option_value === 'account'){
                    if (ks_temp_arr.indexOf(true) !== -1 || ks_options_enable){
                        self.ks_df_context.ks_account_enable = true;
                    }
                }
                if (option_value === 'journals'){
                    if (ks_temp_arr.indexOf(true) !== -1 || ks_options_enable){
                        self.ks_df_context.ks_journal_enable = true;
                    }
                }
                if (option_value === 'account_type'){
                    if (ks_temp_arr.indexOf(true) !== -1 || ks_options_enable){
                        self.ks_df_context.ks_account_both_enable = true;
                    }
                }

//
                _.filter(self.ks_df_report_opt[option_value], function (el) {
                    if ('' + el.id == '' + option_id) {
                        if (el.selected === undefined || el.selected === null) {
                            el.selected = false;
                        }
                        el.selected = !el.selected;
                    } else if (option_value === 'ir_filters') {
                        el.selected = false;
                    }
                    return el;
                });
                self.ksReloadReport();
            });
            var rate_handler = function (event) {
                var option_value = $(this).data('filter');
                if (option_value == 'current_currency') {
                    delete self.report_options.currency_rates;
                } else if (option_value == 'custom_currency') {
                    _.each($('input.js_account_report_custom_currency_input'), function (input) {
                        self.report_options.currency_rates[input.name].rate = input.value;
                    });
                }
                self.ksReloadReport();
            }
            $(document).on('click', '.js_account_report_custom_currency', rate_handler);
            this.$ks_searchview_buttons.find('.js_account_report_custom_currency').click(rate_handler);
            this.$ks_searchview_buttons.find('.js_account_reports_one_choice_filter').click(function (event) {
                self.ks_df_report_opt[$(this).data('filter')] = $(this).data('id');
                self.ksReloadReport();
            });
            this.$ks_searchview_buttons.find('.js_account_report_date_cmp_filter').click(function (event) {
                self.ks_df_context.ks_option_enable = false;
                self.ks_df_context.ks_journal_enable = false
                self.ks_df_context.ks_account_enable = false
                self.ks_df_context.ks_account_both_enable = false
                self.ks_df_report_opt.ks_differ.ks_differentiate_filter = $(this).data('filter');
                if (self.ks_df_report_opt.ks_differ.ks_differentiate_filter == "no_differentiation") {
                    self.ks_df_report_opt.ks_diff_filter.ks_diff_filter_enablity = false
                    self.ks_df_report_opt.ks_diff_filter.ks_debit_credit_visibility = true
                }
                if (self.ks_df_report_opt.ks_differ.ks_differentiate_filter != "no_differentiation") {
                    self.ks_df_report_opt.ks_diff_filter.ks_diff_filter_enablity = true
                    self.ks_df_report_opt.ks_diff_filter.ks_debit_credit_visibility = false
                }
                var error = false;
                var number_period = $(this).parent().find('input[name="periods_number"]');
                self.ks_df_report_opt.ks_differ.ks_no_of_interval = (number_period.length > 0) ? parseInt(number_period.val()) : 1;
                if ($(this).data('filter') === 'custom') {
                    var ks_start_date = self.$ks_searchview_buttons.find('.o_datepicker_input[name="date_from_cmp"]');
                    var ks_end_date = self.$ks_searchview_buttons.find('.o_datepicker_input[name="date_to_cmp"]');
                    if (ks_start_date.length > 0) {
                        error = ks_start_date.val() === "" || ks_end_date.val() === "";
                        self.ks_df_report_opt.ks_differ.ks_start_date = field_utils.parse.date(ks_start_date.val());
                        self.ks_df_report_opt.ks_differ.ks_end_date = field_utils.parse.date(ks_end_date.val());
                    } else {
                        error = ks_end_date.val() === "";
                        self.ks_df_report_opt.ks_differ.ks_end_date = field_utils.parse.date(ks_end_date.val());
                    }
                }
                if (error) {
                    new WarningDialog(self, {
                        title: _t("Odoo Warning"),
                    }, {
                        message: _t("Date cannot be empty")
                    }).open();
                } else {
                    self.ksReloadReport();
                    console.log("\n\njs_account_report_date_cmp_filter() >>>>>>")
                }
            });

            // partner filter
            if (this.ks_df_report_opt.ks_partner) {
                if (!this.ksMany2Many) {
                    var fields = {};
                    if ('ks_partner_ids' in this.ks_df_report_opt) {
                        fields['ks_partner_ids'] = {
                            label: _t('Partners'),
                            modelName: 'res.partner',
                            value: this.ks_df_report_opt.ks_partner_ids.map(Number),
                        };
                    }
                    if (!_.isEmpty(fields)) {
                        this.ksMany2Many = new ksMany2ManyWidget(this, fields);
                        this.ksMany2Many.appendTo(this.$ks_searchview_buttons.find('.js_account_partner_m2m'));
                    }
                } else {
                    this.$ks_searchview_buttons.find('.js_account_partner_m2m').append(this.ksMany2Many.$el);
                }
            }
            if (this.ks_df_report_opt.analytic) {
                if (!this.ksMany2Many) {
                    var fields = {};
                    if (this.ks_df_report_opt.analytic_accounts) {
                        fields['ks_analytic_ids'] = {
                            label: _t('Accounts'),
                            modelName: 'account.analytic.account',
                            value: this.ks_df_report_opt.analytic_accounts.map(Number),
                        };
                    }
                    if (this.ks_df_report_opt.analytic_tags) {
                        fields['ks_analytic_tag_ids'] = {
                            label: _t('Tags'),
                            modelName: 'account.analytic.tag',
                            value: this.ks_df_report_opt.analytic_tags.map(Number),
                        };
                    }
                    if (!_.isEmpty(fields)) {
                        this.ksMany2Many = new ksMany2ManyWidget(this, fields);
                        this.ksMany2Many.appendTo(this.$ks_searchview_buttons.find('.js_account_analytic_m2m'));
                    }
                } else {
                    this.$ks_searchview_buttons.find('.js_account_analytic_m2m').append(this.ksMany2Many.$el);
                }
            }

        },

        /**
         * @method to render main template
        */
        ksRenderMainTemplate: function () {
            this.ksRenderBody();
        },

        /**
         * @method to render report body and currency conversion
        */
        ksRenderBody: function () {
            var self = this;

            var ksFormatConfigurations = {
                currency_id: self.ks_currency,
                noSymbol: true,
            };
            self.initial_balance = self.ksFormatCurrencySign(self.ks_initial_balance, ksFormatConfigurations, self.ks_initial_balance < 0 ? '-' : '');
            self.current_balance = self.ksFormatCurrencySign(self.ks_current_balance, ksFormatConfigurations, self.ks_current_balance < 0 ? '-' : '');
            self.ending_balance = self.ksFormatCurrencySign(self.ks_ending_balance, ksFormatConfigurations, self.ks_ending_balance < 0 ? '-' : '');

            if (self._title != _t("Tax Report") && self._title != _t("Executive Summary")) {
                self.ksSetReportCurrencyConfig();
            } else if (self._title == _t("Tax Report")) {
                self.ksSetTaxReportCurrencyConfig();
            } else if (self._title == _t("Executive Summary")) {
                self.ksSetExecutiveReportCurrencyConfig();
            }

            if (self._title == _t("General Ledger")) {
                self.ksRenderGeneralLedger();
            } else if (self._title == _t("Trial Balance")) {
                self.ksRenderTrialBalance();
            } else if (self._title == _t("Partner Ledger")) {
                self.ksRenderPartnerLedger();
            } else if (self._title == _t("Consolidate Journal")) {
                self.ksRenderConsolidateJournal();
            } else if (self._title == _t("Age Receivable")) {
                self.ksRenderAgeReceivable();
            } else if (self._title == _t("Age Payable")) {
                self.ksRenderAgePayable();
            } else if (self._title == _t("Tax Report")) {
                self.ksRenderTaxReport();
            } else if (self._title == _t("Executive Summary")) {
                self.ksRenderExecutiveSummary();
            } else {
                self.ksRenderGenericReport();
            }
        },

        /**
         * @method to render general ledger report
        */
        ksRenderGeneralLedger: function(){
            var self = this;

            self.$('.o_content').html(QWeb.render('ks_df_gl', {
                    ks_report_lines: self.ks_report_lines,
                    ks_enable_ledger_in_bal: self.ks_enable_ledger_in_bal
                }));
        },

        /**
         * @method to render trial balance report
        */
        // Metro
        ksRenderTrialBalance: function(){
            console.log("\n\nksRenderTrialBalance() >>>>>>>>>>>")
            var self = this;
            console.log("\nself ===",self)
            console.log("\nself.ks_report_lines ===",self.ks_report_lines)
            // Get the keys of the object
            var keys = Object.keys(self.ks_report_lines);

            // Sort the keys
            keys.sort();

            // Create a new object with sorted keys
            var sortedObject = {};
            keys.forEach(function(key) {
                sortedObject[key] = self.ks_report_lines[key];
            });
            console.log("sortedObject ===",sortedObject)
            self.ks_report_lines = sortedObject

            var c = {}
            _.each(sortedObject, function (k, v) {
                    var ksFormatConfigurations = {
                        currency_id: k.company_currency_id,
                        noSymbol: true,
                    };
                    _.each(k.comparision, function(a){
                        console.log(a)
                        if (!c.hasOwnProperty(a.ks_string)) {
                            c[a.ks_string] = {
                                total_initial_debit: 0,
                                total_initial_credit: 0,
                                total_ending_debit: 0,
                                total_ending_credit: 0
                            };
                        }
                        if (a.initial_balance < 0) {
                            a.initial_credit = Math.abs(a.initial_balance)
                            c[a.ks_string].total_initial_credit += a.initial_credit
                        } else if (a.initial_balance > 0) {
                            a.initial_debit = a.initial_balance
                            c[a.ks_string].total_initial_debit += a.initial_debit
                        } else {
                            a.initial_credit = 0
                            a.initial_debit = 0
                        }
                        a.initial_debit = self.ksFormatCurrencySign(a.initial_debit, ksFormatConfigurations, '');
                        a.initial_credit = self.ksFormatCurrencySign(a.initial_credit, ksFormatConfigurations, '');
                        a.initial_balance = self.ksFormatCurrencySign(a.initial_balance, ksFormatConfigurations, a.initial_balance < 0 ? '-': '');
                        a.debit = self.ksFormatCurrencySign(a.debit, ksFormatConfigurations, a.debit < 0 ? '-': '');
                        a.credit = self.ksFormatCurrencySign(a.credit, ksFormatConfigurations, a.credit < 0 ? '-': '');
                        if (a.balance < 0) {
                            a.ending_credit = Math.abs(a.balance)
                            c[a.ks_string].total_ending_credit += a.ending_credit
                        } else if (a.balance > 0) {
                            a.ending_debit = a.balance
                            c[a.ks_string].total_ending_debit += a.ending_debit
                        } else {
                            a.ending_credit = 0
                            a.ending_debit = 0
                        }
                        a.ending_debit = self.ksFormatCurrencySign(a.ending_debit, ksFormatConfigurations, '');
                        a.ending_credit = self.ksFormatCurrencySign(a.ending_credit, ksFormatConfigurations, '');
                        a.balance = self.ksFormatCurrencySign(a.balance, ksFormatConfigurations, a.balance < 0 ? '-': '');

                    });
                });
            console.log("UPDATED self.ks_report_lines ==",self.ks_report_lines)

            console.log("c ==",c)

            _.each(self.ks_subtotal, function (k, v) {
                    var ksFormatConfigurations = {
                        currency_id: k.company_currency_id,
                        noSymbol: true,
                    };
                    _.each(k.subtotal_comparision, function(a){

                        a.ks_total_initial_debit = self.ksFormatCurrencySign(c[a.ks_string].total_initial_debit, ksFormatConfigurations, '')
                        a.ks_total_initial_credit = self.ksFormatCurrencySign(c[a.ks_string].total_initial_credit, ksFormatConfigurations, '')
                        a.ks_total_initial_bln = self.ksFormatCurrencySign(a.ks_total_initial_bln, ksFormatConfigurations, a.ks_total_initial_bln < 0 ? '-': '');
                        a.ks_total_deb = self.ksFormatCurrencySign(a.ks_total_deb, ksFormatConfigurations, a.ks_total_deb < 0 ? '-': '');
                        a.ks_total_cre = self.ksFormatCurrencySign(a.ks_total_cre, ksFormatConfigurations, a.ks_total_cre < 0 ? '-': '');
                        a.ks_total_ending_debit = self.ksFormatCurrencySign(c[a.ks_string].total_ending_debit, ksFormatConfigurations, '')
                        a.ks_total_ending_credit = self.ksFormatCurrencySign(c[a.ks_string].total_ending_credit, ksFormatConfigurations, '')
                        a.ks_total_bln = self.ksFormatCurrencySign(a.ks_total_bln, ksFormatConfigurations, a.ks_total_bln < 0 ? '-': '');
                    });
                });
            console.log("self.ks_subtotal ==",self.ks_subtotal)

            var middle_column = [self.ks_df_report_opt.date.ks_string]
            if (self.ks_df_report_opt.ks_differ.ks_differentiate_filter !== "no_differentiation") {
                _.each(self.ks_df_report_opt.ks_differ.ks_intervals, function (k) {
                    middle_column.push(k.ks_string)
                });
            }
            console.log("middle_column ===",middle_column)
            var trial_dic = {
                    account_data: sortedObject,
                    ks_df_report_opt: self.ks_df_report_opt,
                    subtotal: self.ks_subtotal,
                    middle_column: middle_column.reverse()
                }
            console.log("trial_dic ===",trial_dic)

            self.$('.o_content').html(QWeb.render('ks_df_trial_balance', trial_dic));
            var $table = this.$('.o_content').find('.ks_table_4 tbody');
            
            // Get all rows
            var $rows = $table.find('tr');

            // Sort rows based on data-account-code attribute
            $rows.sort(function(a, b) {
                var codeA = parseInt($(a).attr('data-account-code'));
                var codeB = parseInt($(b).attr('data-account-code'));
                return codeA - codeB;
            });

            // Re-append sorted rows to the table
            $rows.each(function(){
                $table.append(this);
            });

        },

        ksLoadMoreRecords: function(e) {
            console.log("\n   3  ksLoadMoreRecords() >>>>>")
            var self = this;
            var ks_intial_count = e.target.parentElement.dataset.prevOffset;
            var ks_offset = e.target.parentElement.dataset.next_offset;
            console.log("ks_offset ===",ks_offset)

            return this._rpc({
                model: this.ks_dyn_fin_model,
                method: 'ks_get_dynamic_fin_info',
                args: [self.ks_report_id, self.ks_df_report_opt,{
                    ks_intial_count: ks_intial_count,
                    offset: ks_offset}],
                context: self.ks_df_context,
            }).then(function (result) {
              self.$('.ks_pager').find('.ks_value').text(result.ks_offset_dict.offset + "-" + result.ks_offset_dict.next_offset);
              e.target.parentElement.dataset.next_offset = result.ks_offset_dict.next_offset;
              e.target.parentElement.dataset.prevOffset = result.ks_offset_dict.offset;
              self.$('.ks_pager').find('.ks_load_previous').removeClass('ks_event_offer_list');
                 if (result.ks_offset_dict.next_offset >= result.ks_offset_dict.limit){
                $(e.target).addClass('ks_event_offer_list')

                }
                self.ksSetReportInfo(result);
                self.ksRenderMainTemplate();
            });
        },
        ksLoadPreviousRecords: function(e) {
            console.log("\n  5  ksLoadPreviousRecords() >>>>>")
            var paginationlimit=20
            var self = this;
            var ks_offset =  parseInt(e.target.parentElement.dataset.prevOffset) - (paginationlimit+1) ;
            if (ks_offset <0){
                ks_offset=0
            }
            var ks_intial_count = e.target.parentElement.dataset.next_offset;

            return this._rpc({
                model: this.ks_dyn_fin_model,
                method: 'ks_get_dynamic_fin_info',
                args: [self.ks_report_id, self.ks_df_report_opt,{
                    ks_intial_count: ks_intial_count,
                    offset: ks_offset,}],
                context: self.ks_df_context,
            }).then(function (result) {
                self.$('.ks_pager').find('.ks_value').text(result.ks_offset_dict.offset + "-" + result.ks_offset_dict.next_offset);
                e.target.parentElement.dataset.next_offset = result.ks_offset_dict.next_offset;
                e.target.parentElement.dataset.prevOffset = result.ks_offset_dict.offset;
                self.$('.ks_pager').find('.ks_load_next').removeClass('ks_event_offer_list');

                if (result.ks_offset_dict.offset === 1) {
                   $(e.target).addClass('ks_event_offer_list');
                }
                    self.ksSetReportInfo(result);
                    self.ksRenderMainTemplate();
                });
        },
        
        ks_load_pager_rec:function(e){
            console.log("\n    7   ks_load_pager_rec() >>>>>>")
            if (Number(e.target.value)){
            var paginationlimit=20
            var self = this;
            var ks_offset =  e.target.value ;
            var ks_intial_count = Number(e.target.value)+paginationlimit;

            return this._rpc({
                model: this.ks_dyn_fin_model,
                method: 'ks_get_dynamic_fin_info',
                args: [self.ks_report_id, self.ks_df_report_opt,{
                    ks_intial_count: ks_intial_count,
                    offset: ks_offset,}],
                context: self.ks_df_context,
            }).then(function (result) {
                if(result.ks_offset_dict.next_offset < result.ks_offset_dict.offset ){
                self.call('notification', 'notify', {
                    message: "Limit Exceeded",
                    type: 'warning',
                });
                }
                else{
                self.$('.ks_pager').find('.ks_value').text(result.ks_offset_dict.offset + "-" + result.ks_offset_dict.next_offset);
                $(e.target).parent().find('.offset_value')[0].dataset.next_offset = result.ks_offset_dict.next_offset;
                $(e.target).parent().find('.offset_value')[0].dataset.prevOffset = result.ks_offset_dict.offset;
                self.$('.ks_pager').find('.ks_load_next').removeClass('ks_event_offer_list');
                self.$('.ks_pager').find('.ks_load_previous').removeClass('ks_event_offer_list');

                if (result.ks_offset_dict.offset === 1) {
                   $(e.target).parent().find('.ks_load_previous').addClass('ks_event_offer_list');
                }

                    self.ksSetReportInfo(result);
                    self.ksRenderMainTemplate();
                }

                });
    }
            else{
                 this.call('notification', 'notify', {
                    message: "Invalid offset.Please enter single digit",
                    type: 'warning',
                });
            }

        },
        /**
         * @method to render partner ledger report
        */
        ksRenderPartnerLedger: function(){
            var self = this;
            // Step 1: Convert dictionary to array of key-value pairs
            let entries = Object.entries(self.ks_report_lines);

            // Step 2: Sort the entries by 'partner_name'
            entries.sort((a, b) => {
                let nameA = a[1].name.trim().toLowerCase();
                let nameB = b[1].name.trim().toLowerCase();
                return nameA.localeCompare(nameB);
            });

            // Step 3: Extract the sorted keys
            let sortedKeys = entries.map(entry => entry[0]);
            console.log("Sorted Keys",sortedKeys);
            self.$('.o_content').html(QWeb.render('ks_df_pl0', {
                    ks_report_lines: self.ks_report_lines,
                    ks_enable_ledger_in_bal: self.ks_enable_ledger_in_bal,
                    sortedKeys: sortedKeys
                }));
        },

        /**
         * @method to render consolidate journal report
        */
        ksRenderConsolidateJournal: function(){
            var self = this;

            _.each(self.ks_month_lines, function (k, v) {
                    var ksFormatConfigurations = {
                        currency_id: k.company_currency_id,
                        noSymbol: true,
                    };
                    k.debit = self.ksFormatCurrencySign(k.debit, ksFormatConfigurations, k.debit < 0 ? '-' : '');
                    k.credit = self.ksFormatCurrencySign(k.credit, ksFormatConfigurations, k.credit < 0 ? '-' : '');
                    k.balance = self.ksFormatCurrencySign(k.balance, ksFormatConfigurations, k.balance < 0 ? '-' : '')

                });
            self.$('.o_content').html(QWeb.render('ks_df_cj0', {
                    ks_report_lines: self.ks_report_lines,
                    ks_month_lines: self.ks_month_lines
                }));
        },

        /**
         * @method to render Age Receivable report
        */
        ksRenderAgeReceivable: function(){
            var self = this;

            // Step 1: Convert dictionary to array of key-value pairs
            let entries = Object.entries(self.ks_partner_dict);

            // Step 2: Sort the entries by 'partner_name'
            entries.sort((a, b) => {
                let nameA = a[1].partner_name.trim().toLowerCase();
                let nameB = b[1].partner_name.trim().toLowerCase();
                return nameA.localeCompare(nameB);
            });

            // Step 3: Extract the sorted keys
            let sortedKeys = entries.map(entry => entry[0]);

            _.each(self.ks_partner_dict, function (k, v) {
                    var ksFormatConfigurations = {
                        currency_id: k.company_currency_id,
                        noSymbol: true,
                    };
                    for (var z = 0; z < self.ks_period_list.length; z++) {
                        k[self.ks_period_list[z]] = self.ksFormatCurrencySign(k[self.ks_period_list[z]], ksFormatConfigurations, k[self.ks_period_list[z]] < 0 ? '-' : '');
                    }
                    k.total = self.ksFormatCurrencySign(k.total, ksFormatConfigurations, k.total < 0 ? '-' : '');
                    k.is_selected = false;
                });
            self.$('.o_content').html(QWeb.render('ks_df_rec0', {
                    ks_period_list: self.ks_period_list,
                    ks_period_dict: self.ks_period_dict,
                    ks_partner_dict: self.ks_partner_dict,
                    sortedKeys: sortedKeys
                }));

//            custom for partner activity and outstanding statement for AgeReceivable
//            ** start
            self.$(".ks_partner_checkbox").click(function(event) {
                event.stopPropagation();  // Stops row expansion from triggering
            });

            function toggleActionButton() {
                    let selectedCount = self.$(".ks_partner_checkbox:checked").length;
                    if (selectedCount > 0) {
                        self.$("#age_action_button").show();
                    } else {
                        self.$("#age_action_button").hide();
                    }
                }

             self.$('.ks_partner_checkbox').change(function() {
                toggleActionButton();
            });

            self.$("#ks_select_all").change(function() {
                var isChecked = $(this).is(":checked");
                self.$(".ks_partner_checkbox").prop("checked", isChecked);
                toggleActionButton();
            });

            $(document).off("click", "#partner_activity_statement").on("click", "#partner_activity_statement", function () {
                console.log("Partner Activity Statement button clicked!");

                let selectedPartners = [];

                // Loop through checked checkboxes to get partner IDs
                self.$(".ks_partner_checkbox:checked").each(function () {
                    let partnerId = $(this).closest("tr").data("partner-id");  // Get from <tr> instead of <input>
                    if (partnerId) {
                        selectedPartners.push(parseInt(partnerId));
                    }
                });
                console.log('\nselectedPartners', selectedPartners)
                 self._rpc({
                        model: "res.partner",
                        method: "print_partner_activity_statement",
                        args:[selectedPartners],
                        context: {selected_partners: selectedPartners}
                    }).then(function (result) {
                    if (result) {
                        // Handle the action returned from Odoo (like opening a wizard or generating a report)
                        self.do_action(result);
                    }
                })
            });
//            ON Button partner outstanding statement
            $(document).off("click", "#partner_outstanding_statement").on("click", "#partner_outstanding_statement", function () {
                console.log("partner outstanding statement button clicked!");

                let selectedPartners = [];

                // Loop through checked checkboxes to get partner IDs
                self.$(".ks_partner_checkbox:checked").each(function () {
                    let partnerId = $(this).closest("tr").data("partner-id");  // Get from <tr> instead of <input>
                    if (partnerId) {
                        selectedPartners.push(parseInt(partnerId));
                    }
                });
                console.log('\nselectedPartners', selectedPartners)
                 self._rpc({
                        model: "res.partner",
                        method: "print_partner_outstanding_statement",
                        args:[selectedPartners],
                        context: {selected_partners: selectedPartners}
                    }).then(function (result) {
                    if (result) {
                        // Handle the action returned from Odoo (like opening a wizard or generating a report)
                        self.do_action(result);
                    }
                })
            });

            self.$(".ks_pr-py-mline").click(function(event) {
                if (!$(event.target).hasClass("no-expand")) {
                    self.ksGetAgedLinesInfo(event);
                }
            });
//            ** END
        },

        /**
         * @method to render Age Payable report
        */
        ksRenderAgePayable: function(){
            var self = this;
            // Step 1: Convert dictionary to array of key-value pairs
            let entries = Object.entries(self.ks_partner_dict);

            // Step 2: Sort the entries by 'partner_name'
            entries.sort((a, b) => {
                let nameA = a[1].partner_name.trim().toLowerCase();
                let nameB = b[1].partner_name.trim().toLowerCase();
                return nameA.localeCompare(nameB);
            });

            // Step 3: Extract the sorted keys
            let sortedKeys = entries.map(entry => entry[0]);

            _.each(self.ks_partner_dict, function (k, v) {
                var ksFormatConfigurations = {
                    currency_id: k.company_currency_id,
                    noSymbol: true,
                };
                for (var z = 0; z < self.ks_period_list.length; z++) {
                    k[self.ks_period_list[z]] = self.ksFormatCurrencySign(k[self.ks_period_list[z]], ksFormatConfigurations, k[self.ks_period_list[z]] < 0 ? '-' : '');
                }
                k.total = self.ksFormatCurrencySign(k.total, ksFormatConfigurations, k.total < 0 ? '-' : '');
            });
            self.$('.o_content').html(QWeb.render('ks_df_rec0', {
                    ks_period_list: self.ks_period_list,
                    ks_period_dict: self.ks_period_dict,
                    ks_partner_dict: self.ks_partner_dict,
                    sortedKeys: sortedKeys
                }));

            //            custom for partner activity and outstanding statement for AgePayable
//            ** start
            self.$(".ks_partner_checkbox").click(function(event) {
                event.stopPropagation();  // Stops row expansion from triggering
            });

            function toggleActionButton() {
                    let selectedCount = self.$(".ks_partner_checkbox:checked").length;
                    if (selectedCount > 0) {
                        self.$("#age_action_button").show();
                    } else {
                        self.$("#age_action_button").hide();
                    }
                }

             self.$('.ks_partner_checkbox').change(function() {
                toggleActionButton();
            });

            self.$("#ks_select_all").change(function() {
                var isChecked = $(this).is(":checked");
                self.$(".ks_partner_checkbox").prop("checked", isChecked);
                toggleActionButton();
            });

            $(document).off("click", "#partner_activity_statement").on("click", "#partner_activity_statement", function () {
                console.log("Partner Activity Statement button clicked!");

                let selectedPartners = [];

                // Loop through checked checkboxes to get partner IDs
                self.$(".ks_partner_checkbox:checked").each(function () {
                    let partnerId = $(this).closest("tr").data("partner-id");  // Get from <tr> instead of <input>
                    if (partnerId) {
                        selectedPartners.push(parseInt(partnerId));
                    }
                });
                console.log('\nselectedPartners', selectedPartners)
                 self._rpc({
                        model: "res.partner",
                        method: "print_partner_activity_supplier_statement",
                        args:[selectedPartners],
                        context: {selected_partners: selectedPartners}
                    }).then(function (result) {
                    if (result) {
                        // Handle the action returned from Odoo (like opening a wizard or generating a report)
                        self.do_action(result);
                    }
                })
            });
//            ON Button partner outstanding statement
            $(document).off("click", "#partner_outstanding_statement").on("click", "#partner_outstanding_statement", function () {
                console.log("partner outstanding statement button clicked!");

                let selectedPartners = [];

                // Loop through checked checkboxes to get partner IDs
                self.$(".ks_partner_checkbox:checked").each(function () {
                    let partnerId = $(this).closest("tr").data("partner-id");  // Get from <tr> instead of <input>
                    if (partnerId) {
                        selectedPartners.push(parseInt(partnerId));
                    }
                });
                console.log('\nselectedPartners', selectedPartners)
                 self._rpc({
                        model: "res.partner",
                        method: "print_partner_outstanding_supplier_statement",
                        args:[selectedPartners],
                        context: {selected_partners: selectedPartners}
                    }).then(function (result) {
                    if (result) {
                        // Handle the action returned from Odoo (like opening a wizard or generating a report)
                        self.do_action(result);
                    }
                })
            });

            self.$(".ks_pr-py-mline").click(function(event) {
                if (!$(event.target).hasClass("no-expand")) {
                    self.ksGetAgedLinesInfo(event);
                }
            });
//            ** END
        },

        /**
         * @method to render Tax report
        */
        ksRenderTaxReport: function(){
            console.log("ksRenderTaxReport() >>>>>>")
            var self = this;

            self.$('.o_content').html(QWeb.render('ks_tax_report_lines', {
                    ks_report_lines: self.ks_report_lines,
                    ks_df_report_opt: self.ks_df_report_opt
                }));
        },

        /**
         * @method to render Executive summary report
        */
        ksRenderExecutiveSummary: function(){
            var self = this;

            self.$('.o_content').html(QWeb.render('ks_executive_summary_lines', {
                    ks_report_lines: self.ks_report_lines,
                    ks_df_report_opt: self.ks_df_report_opt

                }));

            if (parseFloat(self.ks_initial_balance) > 0 || parseFloat(self.ks_current_balance) > 0 || parseFloat(self.ks_ending_balance) > 0) {
                    self.$(".o_content").append(QWeb.render('ks_account_report_summary_section', {
                        ks_initial_balance: self.ks_initial_balance,
                        ks_current_balance: self.ks_current_balance,
                        ks_ending_balance: self.ks_ending_balance
                    }));
                }
        },

        /**
         * @method to render Generic summary report
        */
        ksRenderGenericReport: function(){
            console.log("\nksRenderGenericReport ===self",this)
            var self = this;

            self.$('.o_content').html(QWeb.render('ks_account_report_lines', {
                    ks_report_lines: self.ks_report_lines,
                    ks_df_report_opt: self.ks_df_report_opt

                }));

            if (parseFloat(self.ks_initial_balance) > 0 || parseFloat(self.ks_current_balance) > 0 || parseFloat(self.ks_ending_balance) > 0) {
                    self.$(".o_content").append(QWeb.render('ks_account_report_summary_section', {
                        ks_initial_balance: self.ks_initial_balance,
                        ks_current_balance: self.ks_current_balance,
                        ks_ending_balance: self.ks_ending_balance
                    }));
                }
        },

        /**
         * @method to set report currency configuration
        */
        ksSetReportCurrencyConfig: function() {
            var self = this;

            _.each(self.ks_report_lines, function (k, v) {
                    var ksFormatConfigurations = {
                        currency_id: k.company_currency_id,
                        noSymbol: true,
                    };
                    k.debit = self.ksFormatCurrencySign(k.debit, ksFormatConfigurations, k.debit < 0 ? '-' : '');
                    k.credit = self.ksFormatCurrencySign(k.credit, ksFormatConfigurations, k.credit < 0 ? '-' : '');
                    if (self._title == _t("Trial Balance")){
                    
                    }else{
                        k.initial_balance = self.ksFormatCurrencySign(k.initial_balance, ksFormatConfigurations, k.initial_balance < 0 ? '-' : '');
                    }
                    //  changed the values of balance
                    if (!k['percentage']) {
                        k.balance = self.ksFormatCurrencySign(k.balance, ksFormatConfigurations, k.balance < 0 ? '-' : '');
                    } else {
                        k.balance = String(Math.round(k.balance)) + "%";
                    }

                    for (const prop in k.balance_cmp) {
                        // ksFormatConfigurations['balance_cmp'] = true // Metro Code
                        console.log("Calling...ksFormatCurrencySign()")
                        ksFormatConfigurations["balance_cmp"] = true;
                        k.balance_cmp[prop] = self.ksFormatCurrencySign(k.balance_cmp[prop], ksFormatConfigurations, k.balance[prop] < 0 ? '-' : '');
                    }
                });
        },

        /**
         * @method to set tax report currency configuration
        */
        ksSetTaxReportCurrencyConfig: function() {
            var self = this;

            _.each(self.ks_report_lines, function (k, v) {
                    var ksFormatConfigurations = {
                        currency_id: k.company_currency_id,
                        noSymbol: true,
                    };
                    k.ks_net_amount = self.ksFormatCurrencySign(k.ks_net_amount, ksFormatConfigurations, k.ks_net_amount < 0 ? '-' : '');
                    k.tax = self.ksFormatCurrencySign(k.tax, ksFormatConfigurations, k.tax < 0 ? '-' : '');

                    for (const prop in k.balance_cmp) {
                        k.balance_cmp[prop][0]['ks_com_net'] = self.ksFormatCurrencySign(k.balance_cmp[prop][0]['ks_com_net'], ksFormatConfigurations, k.balance_cmp[prop][0]['ks_com_net'] < 0 ? '-' : '');
                        k.balance_cmp[prop][1]['ks_com_tax'] = self.ksFormatCurrencySign(k.balance_cmp[prop][1]['ks_com_tax'], ksFormatConfigurations, k.balance_cmp[prop][1]['ks_com_tax'] < 0 ? '-' : '');
                    }
                });
        },

        /**
         * @method to set tax report currency configuration
        */
        ksSetExecutiveReportCurrencyConfig: function() {
            var self = this;

             _.each(self.ks_report_lines, function (k, v) {
                    var ksFormatConfigurations = {
                        currency_id: k.company_currency_id,
                        noSymbol: true,
                    };

                    for (const prop in k.debit) {
                        k.debit[prop] = self.ksFormatCurrencySign(k.debit[prop], ksFormatConfigurations, k.debit[prop] < 0 ? '-' : '');
                    }
                    for (const prop in k.credit) {
                        k.credit[prop] = self.ksFormatCurrencySign(k.credit[prop], ksFormatConfigurations, k.credit[prop] < 0 ? '-' : '');
                    }

                    //  changed the values of balance
                    if (!k['percentage']) {
                        for (const prop in k.balance) {
                            k.balance[prop] = self.ksFormatCurrencySign(k.balance[prop], ksFormatConfigurations, k.balance[prop] < 0 ? '-' : '');
                        }
                    } else {
                        for (const prop in k.balance) {
                            k.balance[prop] = String(field_utils.format.float(k.balance[prop])) + "%";
//                            k.balance[prop] = String(Math.round(k.balance[prop])) + "%";
                        }
                    }

                    for (const prop in k.balance_cmp) {
                        k.balance_cmp[prop] = self.ksFormatCurrencySign(k.balance_cmp[prop], ksFormatConfigurations, k.balance[prop] < 0 ? '-' : '');
                    }
                });
        },

        /**
         * @method to render report body and currency conversion
        */
        ksGetAction: function (e) {
            e.stopPropagation();
            var self = this;
            var action = $(e.target).attr('action');
            var id = $(e.target).parents('td').data('accountId') || $(e.target).parents('td').data('moveId');
            var params = $(e.target).data();
            var context = new Context(this.ks_df_context, params.actionContext || {}, {
                active_id: id
            });

            params = _.omit(params, 'actionContext');
            if (action) {
                return this._rpc({
                        model: this.ks_dyn_fin_model,
                        method: action,
                        args: [this.ks_report_id, this.ks_df_report_opt, params],
                        context: context.eval(),
                    })
                    .then(function (result) {
                        return self.do_action(result);
                    });
            }
        },

        /**
         * @method to format currnecy with amount
         */
        ksFormatCurrencySign: function (amount, ksFormatConfigurations, sign) {
            // console.log("\n 7 ksFormatCurrencySign() >>>> sign =",sign)
            var currency_id = ksFormatConfigurations.currency_id;
            currency_id = session.get_currency(currency_id);
            // Metro Code Testing commented OLDER CODE
            // if (ksFormatConfigurations.hasOwnProperty('balance_cmp')) {
            //     var without_sign = field_utils.format.monetary(amount, {}, ksFormatConfigurations);
            // } else {
            //     var without_sign = field_utils.format.monetary(Math.abs(amount), {}, ksFormatConfigurations);
            // }
            // ends
            // Metro Code Commented 8APR25
            // var without_sign = field_utils.format.monetary(Math.abs(amount), {}, ksFormatConfigurations);  
            // ends 
            
            if (ksFormatConfigurations.hasOwnProperty('balance_cmp')) {
                var without_sign = field_utils.format.monetary(amount, {}, ksFormatConfigurations);  
            } else {
                var without_sign = field_utils.format.monetary(Math.abs(amount), {}, ksFormatConfigurations);   
            }    

            if (!amount) {
                return '-'
            };
            if (currency_id){
                if (currency_id.position === "after") {
                    return sign + '&nbsp;' + without_sign + '&nbsp;' + currency_id.symbol;
                } else {
                    return currency_id.symbol + '&nbsp;' + sign + '&nbsp;' + without_sign;
                }
            }
            return without_sign;
        },
        
        /**
         * @method to get the storage session keys
         */
        ksGetStorageKey: function (ks_df_report_key) {
            self.ks_df_report_opt = JSON.parse(sessionStorage.getItem(ks_df_report_key)) || this.ks_df_report_opt;
        },

        /**
         * @method to set the storage session keys
         */
        ksSetStorageKey: function (ks_df_report_key) {
            // set session key
            sessionStorage.setItem(ks_df_report_key, JSON.stringify(this.ks_df_report_opt));
        },

        /**
         * @method to set the information required by Dynamic financial reports
         */
        ksSetDfRepInfo: function (values) {
            console.log("\n\nksSetDfRepInfo() >>>>",values)

            this.ks_df_reports_ids= values.ks_df_reports_ids;
            this.ks_df_report_opt = values.ks_df_informations;
            this.ks_df_context = values.context;
            this.ks_report_manager_id = values.ks_report_manager_id;
            this.ks_remarks = values.ks_remarks;
            this.$ks_buttons = $(values.ks_buttons);
            this.$ks_searchview_buttons = $(values.ks_searchview_html);
            this.ks_currency = values.ks_currency;
            this.ks_report_lines = values.ks_report_lines;
            this.ks_enable_ledger_in_bal = values.ks_enable_ledger_in_bal;
            this.ks_initial_balance = values.ks_initial_balance;
            this.ks_initial_balance = values.ks_initial_balance;
            this.ks_current_balance = values.ks_current_balance;
            this.ks_ending_balance = values.ks_ending_balance;
            this.ks_diff_filter = values.ks_diff_filter;
            this.ks_retained = values.ks_retained;
            this.ks_subtotal = values.ks_subtotal;
            this.ks_partner_dict = values.ks_partner_dict;
            this.ks_period_list = values.ks_period_list;
            this.ks_period_dict = values.ks_period_dict;
            this.ks_month_lines = values.ks_month_lines;
            this.ks_sub_lines = values.ks_sub_lines
            this.ksStorageKeyOpt();
        },
    });

    core.action_registry.add('ks_dynamic_report', ksDynamicReportsWidget);

    return ksDynamicReportsWidget;

});


 $(document).ready(function() {
        $(document).on('click', 'header .o_main_navbar', function(evt){
                $('.o_filter_menu').removeClass('ks_d_block')
            });
    });












