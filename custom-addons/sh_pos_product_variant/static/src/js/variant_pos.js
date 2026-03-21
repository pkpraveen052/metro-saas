odoo.define('sh_pos_product_variant.variant_pos', function (require, factory) {
    'use strict';

    const Registries = require("point_of_sale.Registries");
    const AbstractAwaitablePopup = require("point_of_sale.AbstractAwaitablePopup");
    const { useListener } = require("web.custom_hooks");
    const { Gui } = require("point_of_sale.Gui");
    var utils = require('web.utils');
    var models = require('point_of_sale.models')

    class variantPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            useListener('click-product', this._clickProduct1);
            this.attibute_list = []
        }
        updateSearch(event) {
            this.searchWord = event.target.value;
            this.render()
        }
        _clickProduct1(event) {
            var product = event.detail
            var currentOrder = this.env.pos.get_order()
            currentOrder.add_product(product)
            if (this.env.pos.config.sh_close_popup_after_single_selection ) {
                this.trigger("close-popup");
            }
        }
        Confirm() {
            var self = this
            var lst = []
            var currentOrder = this.env.pos.get_order()
            if ($('.sh_highlight')) {
                _.each($('.sh_highlight'), function (each) {
                    lst.push(parseInt($(each).attr('data-id')))
                })
            }
            _.each(self.env.pos.db.product_by_id, function (product) {
                if(product.product_template_attribute_value_ids.length > 0 && JSON.stringify(product.product_template_attribute_value_ids)===JSON.stringify(lst)) {
                    currentOrder.add_product(product)
                }
            })
            if(this.props.attributes_name.length > $('.sh_highlight').length){
                alert('Please Select Variant')
            }else{
                if(self.env.pos.config.sh_close_popup_after_single_selection){
                    this.trigger("close-popup");
                }else{
                    $('.sh_group_by_attribute').find('.sh_highlight').removeClass('sh_highlight')
                }
            }
        }
        
        mounted() {
            if(this.env.pos.config.sh_pos_variants_group_by_attribute && !this.env.pos.config.sh_pos_display_alternative_products){
                
                $('.main').addClass('sh_product_attr_no_alternative')
                $('.sh_product_variants_popup').addClass('sh_attr_no_alternative_popup')
            }
            if(this.Attribute_names && this.Attribute_names.length > 0 && this.AlternativeProducts && this.AlternativeProducts < 1 ){
                $('.main').addClass('sh_only_attributes')
            }
            super.mounted();
        }
        get VariantProductToDisplay() {
            if (this.searchWord) {
                var searched = this.env.pos.db.search_variants(this.props.product_variants, this.searchWord);
                return searched
            } else {
                return this.props.product_variants;
            }
        }
        get AlternativeProducts() {
            return this.props.alternative_products
        }
        get Attribute_names(){
            return this.props.attributes_name
        }
        Select_attribute_value(event) {

            _.each($('.'+$(event.currentTarget).attr('class')), function (each) {
                $(each).removeClass('sh_highlight')
            })

            if($('.sh_attribute_value').hasClass('sh_highlight')){
                $('.sh_attribute_value').removeClass('sh_highlight')
            }
            if ($(event.currentTarget).hasClass('sh_highlight')) {
                $(event.currentTarget).removeClass('sh_highlight')

            } else {
                $(event.currentTarget).addClass('sh_highlight')
            }
        }
    }
    variantPopup.template = "variantPopup";

    Registries.Component.add(variantPopup);


});
