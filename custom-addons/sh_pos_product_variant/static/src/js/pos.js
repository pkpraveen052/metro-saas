odoo.define('sh_pos_product_variant.pos', function (require) {
    'use strict';

    var DB = require('point_of_sale.DB');
    var models = require('point_of_sale.models')
    const ProductsWidget = require("point_of_sale.ProductsWidget");
    const Registries = require("point_of_sale.Registries");
    const ProductScreen = require("point_of_sale.ProductScreen");
    const ProductItem = require("point_of_sale.ProductItem");
    var utils = require('web.utils');
    const { Gui } = require("point_of_sale.Gui");


    models.load_fields('product.product', ['sh_alternative_products', 'name', 'product_template_attribute_value_ids'])

    models.load_models({
        model: "product.template.attribute.line",
        label: "product_template_attribute",

        loaded: function (self, all_attributes) {
            self.db.product_temlate_attribute_lineids = all_attributes
            if (all_attributes && all_attributes.length > 0) {
                _.each(all_attributes, function (each_qr_element) {
                    self.db.product_temlate_attribute_line_by_id[each_qr_element.id] = each_qr_element
                });
            }
        },
    })
    models.load_models({
        model: "product.template.attribute.value",
        label: "product_template_attribute",
        loaded: function (self, all_attributes) {
            self.db.product_temlate_attribute_ids = all_attributes
            if (all_attributes && all_attributes.length > 0) {
                _.each(all_attributes, function (each_qr_element) {
                    self.db.product_temlate_attribute_by_id[each_qr_element.id] = each_qr_element
                });
            }
        },
    })

    DB.include({
        init: function (options) {
            this._super.apply(this, arguments);
            this.product_temlate_attribute_line_by_id = {};
            this.product_temlate_attribute_by_id = {};
            this.product_tmpl_by_id = {}
        },
        has_variant: function (id) {
            var tmpls = []
            _.each(this.product_by_id, function (each_product) {
                if (each_product.product_tmpl_id == id) {
                    tmpls.push(each_product)
                }
            })
            if (tmpls.length > 1) {
                return tmpls
            } else {
                return false
            }
        },
        search_variants: function (variants, query) {
            var self = this;
            this.variant_search_string = ""
            for (var i = 0; i < variants.length; i++) {
                var variant = variants[i]
                var search_variant = utils.unaccent(self.variant_product_search_string(variant))
                self.variant_search_string += search_variant
            }
            try {
                query = query.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g, '.');
                query = query.replace(/ /g, '.+');
                var re = RegExp("([0-9]+):.*?" + utils.unaccent(query), "gi");
            } catch (e) {
                return [];
            }

            var results = [];
            for (var i = 0; i < this.limit; i++) {
                var pariant_pro = re.exec(this.variant_search_string)
                if (pariant_pro) {
                    var id = Number(pariant_pro[1]);
                    var product_var = this.get_product_by_id(id)

                    results.push(product_var)

                } else {
                    break;
                }
            }
            return results;
        },
        variant_product_search_string: function (product) {

            var str = product.display_name;
            if (product.id) {
                str += '|' + product.id;
            }
            if (product.default_code) {
                str += '|' + product.default_code;
            }
            if (product.description) {
                str += '|' + product.description;
            }
            if (product.description_sale) {
                str += '|' + product.description_sale;
            }
            str = product.id + ':' + str.replace(/:/g, '') + '\n';
            return str;
        }
    })

    const PosProductItem = (ProductItem) =>
        class extends ProductItem {
            mounted() {
                super.mounted()
                var self = this;
                if (self.env.pos.config.sh_pos_enable_product_variants) {
                    var product = this.props.product
                    var variants = self.env.pos.db.has_variant(product.product_tmpl_id)
                    _.each($('.product'), function (each) {
                        if (product.id == each.dataset.productId && variants) {
                            if (variants.length > 1) {
                                $(each).find('.price-tag').addClass('sh_has_variant');
                                $(each).find('.price-tag').text(variants.length + ' variants');
                            }
                        }
                    })
                }
            }
        }

    Registries.Component.extend(ProductItem, PosProductItem);


    const PosProductsWidget = (ProductsWidget) =>
        class extends ProductsWidget {
            constructor() {
                super(...arguments);
                var self = this;
                _.each(self.env.pos.db.product_by_category_id[self.selectedCategoryId], function (product_id, i) {
                    var each_product = self.env.pos.db.product_by_id[product_id]
                    if (self.env.pos.db.product_tmpl_by_id[each_product.product_tmpl_id] && each_product.attribute_line_ids.length > 0) {
                        if (self.env.pos.db.product_tmpl_by_id[each_product.product_tmpl_id] && !self.env.pos.db.product_tmpl_by_id[each_product.product_tmpl_id].includes(each_product.id)) {
                            self.env.pos.db.product_tmpl_by_id[each_product.product_tmpl_id].push(product_id)
                        }
                    } else {
                        if (each_product.attribute_line_ids.length > 0) {
                            self.env.pos.db.product_tmpl_by_id[each_product.product_tmpl_id] = [product_id]
                        }
                    }
                })
            }
            get productsToDisplay() {
                var self = this;
                var res = super.productsToDisplay
                var products = []
                var tmpl_ids = []
                if (this.searchWord !== '') {
                    if (self.env.pos.config.sh_pos_enable_product_variants) {
                        _.each(res, function (each_product, i) {
                            // var each_product = self.env.pos.db.product_by_id[product_id]
                            if (each_product.attribute_line_ids.length > 0) {
                                if (!tmpl_ids.includes(each_product.product_tmpl_id)) {
                                    products.push(each_product)
                                }
                                tmpl_ids.push(each_product.product_tmpl_id)
                            } else {
                                products.push(each_product)
                            }

                        })
                        return products
                    }
                } else {
                    // list = this.env.pos.db.get_product_by_category(this.selectedCategoryId);
                    if (self.env.pos.config.sh_pos_enable_product_variants) {
                        _.each(self.env.pos.db.product_by_category_id[self.selectedCategoryId], function (product_id, i) {
                            var each_product = self.env.pos.db.product_by_id[product_id]
                            if (each_product.attribute_line_ids.length > 0) {
                                if (!tmpl_ids.includes(each_product.product_tmpl_id)) {
                                    products.push(each_product)
                                }
                                tmpl_ids.push(each_product.product_tmpl_id)
                            } else {
                                products.push(each_product)
                            }

                        })
                        return products
                    }
                }
            }
        }

    Registries.Component.extend(ProductsWidget, PosProductsWidget);

    const PosProductScreen = (ProductScreen) =>
        class extends ProductScreen {
            async _clickProduct(event) {
                var self = this;
                this.product_variants = []
                this.alternative_products = []
                var alternative_ids = []
                _.each(self.env.pos.db.product_by_id, function (each_product) {
                    if (each_product.product_tmpl_id == event.detail.product_tmpl_id) {
                        self.product_variants.push(each_product)
                        if (each_product.sh_alternative_products.length > 0) {
                            _.each(each_product.sh_alternative_products, function (each) {
                                var product = self.env.pos.db.get_product_by_id(each)
                                if (!alternative_ids.includes(each)) {
                                    if (self.env.pos.config.sh_pos_display_alternative_products) {
                                        self.alternative_products.push(product)
                                    }
                                }
                                alternative_ids.push(each)
                            })
                        }
                    }
                })
                if (this.product_variants.length > 1) {

                    if (!self.env.pos.config.sh_pos_variants_group_by_attribute && self.env.pos.config.sh_pos_enable_product_variants) {
                        if (this.product_variants.length > 6 && this.product_variants.length < 15) {
                            self.showPopup("variantPopup", { 'title': 'Product Variants', 'morevariant_class': 'sh_lessthan_8_variants', product_variants: this.product_variants, alternative_products: this.alternative_products })
                        }
                        else if (this.product_variants.length > 15) {
                            self.showPopup("variantPopup", { 'title': 'Product Variants', 'morevariant_class': ' sh_morethan_15_variants', product_variants: this.product_variants, alternative_products: this.alternative_products })
                        }
                        else {
                            self.showPopup("variantPopup", { 'title': 'Product Variants', product_variants: this.product_variants, alternative_products: this.alternative_products })
                        }

                    }
                    else if (self.env.pos.config.sh_pos_variants_group_by_attribute && self.env.pos.config.sh_pos_enable_product_variants) {

                        self.Attribute_names = []
                        _.each(event.detail.attribute_line_ids, function (each_attribute) {
                            self.Attribute_names.push(self.env.pos.db.product_temlate_attribute_line_by_id[each_attribute])
                        })
                        if (this.Attribute_names.length > 0) {

                            self.showPopup("variantPopup", { 'title': 'Product Variants', attributes_name: this.Attribute_names, alternative_products: this.alternative_products })
                        } else {
                            super._clickProduct(event)
                        }
                    }
                    else {
                        super._clickProduct(event)
                    }
                }
                // else if (this.alternative_products.length > 1 && self.env.pos.config.sh_pos_display_alternative_products) {
                //    
                //     if (self.env.pos.config.sh_pos_enable_product_variants && self.env.pos.config.sh_pos_display_alternative_products) {
                //        
                //         if (this.alternative_products.length > 0) {
                //             self.showPopup("variantPopup", { 'title': 'Alternative Product', product_variants: this.product_variants, alternative_products: this.alternative_products })
                //         }
                //     }
                // }
                else {
                    if (this.alternative_products.length > 0 && self.env.pos.config.sh_pos_display_alternative_products && self.env.pos.config.sh_pos_variants_group_by_attribute) {
                        self.showPopup("variantPopup", { 'title': 'Alternative Product', attributes_name: [], alternative_products: this.alternative_products })
                    }
                    if (this.alternative_products.length > 0 && self.env.pos.config.sh_pos_display_alternative_products && !self.env.pos.config.sh_pos_variants_group_by_attribute) {
                        self.showPopup("variantPopup", { 'title': 'Alternative Product', product_variants: [], alternative_products: this.alternative_products })
                    }
                    super._clickProduct(event)
                }
            }
        }

    Registries.Component.extend(ProductScreen, PosProductScreen);
});