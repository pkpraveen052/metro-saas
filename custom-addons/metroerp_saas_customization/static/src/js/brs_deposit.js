odoo.define('metroerp_saas_customization.brs_deposit_pos', function (require) {
    "use strict";

    const models = require('point_of_sale.models');
    const rpc = require('web.rpc');

    // Load fields from server side models - these MUST exist in Python side
    models.load_fields('product.product', ['is_brs_deposit', 'brs_deposit_amount']);
    models.load_fields('res.company', ['brs_deposit_product_id']);

    const SuperOrder_add_product = models.Order.prototype.add_product;
    const SuperOrder_remove_orderline = models.Order.prototype.remove_orderline;

    // --- Utility: resolve company-configured BRS product id (int) ---
    function _get_brs_product_id_from_company(pos) {
        try {
            const company = pos.company || (pos.get_company && pos.get_company());
            if (!company) return false;
            const conf = company.brs_deposit_product_id;
            if (!conf) return false;
            return Array.isArray(conf) ? conf[0] : (conf.id || conf);
        } catch (e) {
            console.warn("BRS: failed to read company config", e);
            return false;
        }
    }

    // --- Utility: ensure we have a POS product object for brsProductId ---
    // returns a Promise resolved with the product object or null
    async function _ensure_brs_product_in_pos_db(pos, brsProductId) {
        if (!brsProductId) return null;
        let prod = pos.db.get_product_by_id(brsProductId);
        if (prod) {
            return prod;
        }
        try {
            const res = await rpc.query({
                model: 'product.product',
                method: 'read',
                args: [[brsProductId], [
                    'id', 'display_name', 'name', 'lst_price', 'uom_id',
                    'list_price', 'pos_categ_id', 'taxes_id'
                ]],
            });
            if (res && res.length) {
                // add_products expects array of product dicts in POS shape; this works in most POS setups
                pos.db.add_products(res);
                prod = pos.db.get_product_by_id(brsProductId);
                if (prod) {
                    return prod;
                } else {
                    return null;
                }
            } else {
                return null;
            }
        } catch (err) {
            return null;
        }
    }

    // --- Add or update the auto BRS line on the order (safe) ---
    function addOrUpdateBRSLine(order, brsProduct, totalDeposit) {
        try {
            if (!order || !brsProduct) {
                return;
            }

            const existing = order.get_orderlines().find(
                l => l.product && l.product.id === brsProduct.id
            );

            if (existing) {
                existing.price_manually_set = true;
                // Set quantity = 1 and price to totalDeposit
                existing.set_quantity(1);
                existing.set_unit_price(totalDeposit);
                return;
            }

            // guard reentrancy by marking order before adding
            order._brs_adding = true;
            try {
                order.add_product(brsProduct, {
                    quantity: 1,
                    price: totalDeposit,
                    is_brs_auto: true,
                    merge: false
                });

                // tag the newly created line (best-effort)
                const lastLine = order.get_last_orderline && order.get_last_orderline();
                if (lastLine && lastLine.product && lastLine.product.id === brsProduct.id) {
                    lastLine.is_brs_auto = true;
                    lastLine.price_manually_set = true;
                } else {
                    // fallback: find any line with product id and is_brs_auto not set and mark it
                    const newLine = order.get_orderlines().find(l => l.product && l.product.id === brsProduct.id && !l.is_brs_auto);
                    if (newLine) {
                        newLine.is_brs_auto = true;
                        newLine.price_manually_set = true;
                    } else {
                    }
                }
            } finally {
                order._brs_adding = false;
            }

        } catch (err) {
        }
    }

    // --- Calculate total deposit amount across orderlines (quantity-aware) ---
    // returns total deposit (number)
    function _calculate_total_deposit(order, brsProductId) {
    let total = 0;
    try {
        const processedProducts = new Set();   // 🔥 to avoid double counting same product

        order.get_orderlines().forEach(line => {
            if (!line || !line.product) return;

            // skip auto-created BRS line
            if (line.is_brs_auto) return;

            // skip BRS product itself
            if (brsProductId && line.product.id === brsProductId) return;

            if (line.product.is_brs_deposit) {
                const productId = line.product.id;

                // 🔥 Add deposit ONLY once per unique product
                if (!processedProducts.has(productId)) {
                    const amt = line.product.brs_deposit_amount || 0;
                    total += amt;
                    processedProducts.add(productId);
                }
            }
        });

    } catch (e) {
        console.error("BRS: error calculating deposit total", e);
    }
    return total;
}


    // --- Recalc total deposit and add/update BRS line (async) ---
    async function recalc_brs_total(order) {
        try {
            if (!order || !order.pos) {
                return;
            }
            const pos = order.pos;
            const brsProductId = _get_brs_product_id_from_company(pos);
            if (!brsProductId) {
                return;
            }

            const totalDeposit = _calculate_total_deposit(order, brsProductId);

            // if nothing to do -> remove existing brs line if exists
            const existingBRSLine = order.get_orderlines().find(l => l.product && l.product.id === brsProductId);
            if (!totalDeposit || totalDeposit <= 0) {
                if (existingBRSLine) {
                    // mark as auto to avoid re-trigger
                    existingBRSLine.is_brs_auto = true;
                    order.remove_orderline(existingBRSLine);
                }
                return;
            }

            // ensure brs product is present as a POS product object
            let brsProduct = pos.db.get_product_by_id(brsProductId);
            if (!brsProduct) {
                brsProduct = await _ensure_brs_product_in_pos_db(pos, brsProductId);
            }

            if (!brsProduct) {
                return;
            }

            // finally add or update the BRS line
            addOrUpdateBRSLine(order, brsProduct, totalDeposit);

        } catch (err) {
            console.error("BRS: recalc_brs_total failed", err);
        }
    }

    // ---------------------------
    // Override Order.add_product
    // ---------------------------
    models.Order.prototype.add_product = function (product, options = {}) {
        try {
            // debug log

            // call original to add product to order
            SuperOrder_add_product.apply(this, arguments);

            // guards to avoid recursion:
            // - if options.is_brs_auto -> this was an auto-created BRS line (skip)
            // - if the order is currently adding brs internally -> skip
            if (options.is_brs_auto) {
                return;
            }
            if (this._brs_adding) {
                return;
            }

            // get brs product id from company config
            const pos = this.pos;
            const brsProductId = _get_brs_product_id_from_company(pos);

            // if added product is the configured BRS product itself, do not trigger (avoid loops)
            if (product && brsProductId && product.id === brsProductId) {
                return;
            }

            // trigger only when the added product is a deposit-trigger product
            if (product && product.is_brs_deposit) {
                // don't await here so UI remains snappy; recalc_brs_total will internally fetch if needed
                recalc_brs_total(this);
            } else {
                // no-op
            }

        } catch (err) {
            console.error("BRS: add_product wrapper error", err);
            // fallback to default behavior if anything went wrong
            try { SuperOrder_add_product.apply(this, arguments); } catch (e) { /* swallow */ }
        }
    };

    // ---------------------------
    // Override Order.remove_orderline
    // ---------------------------
    models.Order.prototype.remove_orderline = function (orderline) {
        try {

            // perform native removal first
            const res = SuperOrder_remove_orderline.apply(this, arguments);

            // if removed line was auto-created BRS line, do not recalc
            if (orderline && orderline.is_brs_auto) {
                return res;
            }

            // if removed line was a trigger product -> recalc
            if (orderline && orderline.product && orderline.product.is_brs_deposit) {
                recalc_brs_total(this);
            }

            return res;
        } catch (err) {
            console.error("BRS: remove_orderline wrapper error", err);
            try { return SuperOrder_remove_orderline.apply(this, arguments); } catch (e) { return; }
        }
    };

});


