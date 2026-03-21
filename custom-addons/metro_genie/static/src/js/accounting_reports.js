odoo.define('metro_genie.accounting_report_dropdown', function (require) {
    "use strict";

    const rpc = require('web.rpc');

    $(document).ready(function () {
        $(document).on('click', '.accounting-reports-btn', function (e) {
            e.preventDefault();
            e.stopPropagation();

            // Remove any existing dropdown to avoid duplicates
            $('.custom-accounting-dropdown').remove();

            const $button = $(this);
            const offset = $button.offset();
            const buttonHeight = $button.outerHeight();
            const buttonWidth = $button.outerWidth();

            // Create the dropdown container
            const $dropdown = $('<ul>', {
                class: 'custom-accounting-dropdown',
                css: {
                    position: 'absolute',
                    top: offset.top + buttonHeight,
                    left: offset.left,
                    background: '#fff',
                    border: '1px solid #ccc',
                    zIndex: 9999,
                    padding: '5px 0',
                    margin: 0,
                    listStyle: 'none',
                    minWidth: buttonWidth,
                    boxShadow: '0 2px 6px rgba(0,0,0,0.15)',
                    borderRadius: '4px'
                }
            });

            // Append it to the body so it stays global
            $('body').append($dropdown);

            rpc.query({
                model: 'metro.genie.suggestion',
                method: 'get_group_filtered_suggestions',
                args: []
            }).then(function (reports) {
                const filtered = reports.filter(r => r.is_accounting_report && r.is_accounting_report);
                console.log('filteredfiltered', filtered)
                if (filtered.length === 0) {
                    $dropdown.append('<li style="padding: 8px 16px; color: #999;">No reports</li>');
                }

                filtered.forEach(report => {
                    const $li = $('<li>', {
                        text: report.name,
                        css: {
                            padding: '8px 16px',
                            cursor: 'pointer',
                            color: '#333'
                        },
                        click: function () {
                            $dropdown.remove();
                            const urlParts = [];
                            if (!report) {
                                alert("No Action found!");
                            }

                            if (report.window_action_id) urlParts.push(`action=${report.window_action_id}`);
                            if (report.client_actions_id) urlParts.push(`action=${report.client_actions_id}`);
                            if (report.menu_id) urlParts.push(`menu_id=${report.menu_id}`);
                            if (report.model) urlParts.push(`model=${report.model}`);
                            if (report.view_types) urlParts.push(`view_type=${report.view_types}`);
                            const url = '/web#' + urlParts.join('&');
                            window.location.href = url;
                        }
                    });
                    $dropdown.append($li);
                });
            });
        });

        // Hide dropdown if clicking anywhere else
        $(document).on('click', function () {
            $('.custom-accounting-dropdown').remove();
        });
    });
});


