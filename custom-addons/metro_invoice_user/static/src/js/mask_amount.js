odoo.define('metro_invoice_user.mask_account_amount', function (require) {
"use strict";

const session = require('web.session');
const ListRenderer = require('web.ListRenderer');

let maskEnabled = false;
let isAccountMoveLineView = false;
let isAccountMoveView = false;

session.user_has_group('metro_invoice_user.group_account_invoice_user').then(function(res){
    maskEnabled = res;
});

const fields_to_mask = ['debit','credit','balance','amount_currency'];

const maskMessage =
"This feature is not available in the free InvoiceNow solution.\n\n" +
"To avail this function:\n" +
"WhatsApp: +65323242342\n" +
"Email: sales@metrogroup.solutions";

function maskValue(value){
    if (!value) return value;

    let clean = value.toString().replace(/[^0-9.-]/g,'');

    if (clean.length <= 2){
        return '**';
    }

    return '**' + clean.slice(2);
}

////////////////////////////////////////////////////////
// 1️⃣ NORMAL LIST VIEW RENDER
////////////////////////////////////////////////////////

ListRenderer.include({

    _renderBodyCell: function (record, node, colIndex, options) {

        let $cell = this._super.apply(this, arguments);

        if (!maskEnabled){
            return $cell;
        }

        //////////////////////////////////////////////////////
        // Detect model
        //////////////////////////////////////////////////////

        if (this.state && this.state.model === 'account.move.line'){
            isAccountMoveLineView = true;
            isAccountMoveView = false;
        }
        else if (this.state && this.state.model === 'account.move'){
            isAccountMoveView = true;
            isAccountMoveLineView = false;
            return $cell; // normal rows NOT masked
        }
        else{
            isAccountMoveView = false;
            isAccountMoveLineView = false;
            return $cell;
        }

        //////////////////////////////////////////////////////
        // Skip invoice line table
        //////////////////////////////////////////////////////

        if ($cell.closest('.o_field_x2many_list').length){
            return $cell;
        }

        //////////////////////////////////////////////////////
        // Mask account.move.line columns
        //////////////////////////////////////////////////////

        if (isAccountMoveLineView && fields_to_mask.includes(node.attrs.name)){

            let value = $cell.text().trim();

            if (value){

                let masked = maskValue(value);

                $cell.text(masked);
                $cell.attr('title', maskMessage);

            }

        }

        return $cell;

    },

});

////////////////////////////////////////////////////////
// 2️⃣ GROUP BY + TOTAL MASK
////////////////////////////////////////////////////////

function applyMask($root){

    if (!maskEnabled) return;

    //////////////////////////////////////////////////////
    // account.move.line masking (Journal Items)
    //////////////////////////////////////////////////////

    if (isAccountMoveLineView){

        $root.find('td, th').each(function(){

            if ($(this).closest('.o_field_x2many_list').length){
                return;
            }

            let text = $(this).text().trim();

            if (/^-?\d[\d,]*\.?\d*$/.test(text)){

                let masked = maskValue(text);

                if ($(this).text() !== masked){
                    $(this).text(masked);
                    $(this).attr('title', maskMessage);
                }

            }

        });

    }

    //////////////////////////////////////////////////////
    // account.move masking (Invoices / Bills)
    // ONLY when grouped
    //////////////////////////////////////////////////////

    if (isAccountMoveView){

        // Apply only when group by is active
        if ($root.find('.o_group_header').length){

            $root.find('td.o_list_number, th.o_list_number').each(function(){

                let text = $(this).text().trim();

                if (/^-?\d[\d,]*\.?\d*$/.test(text)){

                    let masked = maskValue(text);

                    if ($(this).text() !== masked){
                        $(this).text(masked);
                        $(this).attr('title', maskMessage);
                    }

                }

            });

        }

    }

}

////////////////////////////////////////////////////////
// 3️⃣ WATCH ODOO DOM CHANGES
////////////////////////////////////////////////////////

$(document).ready(function(){

    const observer = new MutationObserver(function(mutations){

        if (!maskEnabled) return;

        observer.disconnect();

        mutations.forEach(function(mutation){

            if (mutation.addedNodes.length){
                applyMask($('.o_list_view'));
            }

        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

});

});