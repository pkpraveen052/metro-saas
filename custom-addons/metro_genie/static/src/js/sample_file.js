

//odoo.define('metro_genie.sample_files_dropdown', function (require) {
//    "use strict";
//
//    const rpc = require('web.rpc');
//
//    $(document).on('click', '.sample-files-btn', function (e) {
//        e.preventDefault();
//        e.stopPropagation();
//
//        // Remove existing dropdown
//        $('.sample-files-dropdown').remove();
//
//        const $btn = $(this);
//        const offset = $btn.offset();
//
//        const $dropdown = $('<ul>', {
//            class: 'sample-files-dropdown',
//            css: {
//                position: 'absolute',
//                top: offset.top + $btn.outerHeight(),
//                left: offset.left,
//                background: '#fff',
//                border: '1px solid #ccc',
//                zIndex: 10000,
//                listStyle: 'none',
//                padding: '5px 0',
//                margin: 0,
//                minWidth: $btn.outerWidth(),
//                maxHeight: '260px',
//                overflowY: 'auto',
//                boxShadow: '0 2px 6px rgba(0,0,0,0.15)'
//            }
//        });
//
//        $('body').append($dropdown);
//
//        rpc.query({
//            model: 'metro.genie.suggestion',
//            method: 'get_sample_files',
//            args: []
//        }).then(function (files) {
//
//            if (!files || !files.length) {
//                $dropdown.append(
//                    '<li style="padding:8px 16px;color:#999;">No sample files</li>'
//                );
//                return;
//            }
//
//            files.forEach(function (file) {
//                const $li = $('<li>', {
//                    text: file.name,
//                    css: {
//                        padding: '8px 16px',
//                        cursor: 'pointer'
//                    }
//                });
//
//                $li.on('click', function (e) {
//                    e.stopPropagation();
//                    window.open(`/web/content/${file.id}?download=true`, '_blank');
//                    $dropdown.remove();
//                });
//
//                $dropdown.append($li);
//            });
//        });
//    });
//
//    // Close on outside click
//    $(document).on('click', function () {
//        $('.sample-files-dropdown').remove();
//    });
//});

//odoo.define('metro_genie.sample_files_dropdown', function (require) {
//    "use strict";
//
//    const rpc = require('web.rpc');
//
//    $(document).on('click', '.sample-files-btn', function (e) {
//        e.preventDefault();
//        e.stopPropagation();
//
//        $('.custom-sample-dropdown').remove();
//
//        const $btn = $(this);
//        const $wrapper = $btn.closest('.sample-files-wrapper');
//
//        const $dropdown = $('<ul>', {
//            class: 'custom-sample-dropdown',
//            css: {
//                position: 'absolute',
//                top: '100%',          // 👈 directly below button
//                left: 0,
//                marginTop: '6px',
//                background: '#fff',
//                border: '1px solid #ccc',
//                zIndex: 10000,
//                listStyle: 'none',
//                padding: '5px 0',
//                minWidth: $btn.outerWidth(),
//                maxHeight: '260px',
//                overflowY: 'auto',
//                boxShadow: '0 2px 6px rgba(0,0,0,0.15)',
//                borderRadius: '4px'
//            }
//        });
//
//        // 👇 append INSIDE wrapper (key fix)
//        $wrapper.append($dropdown);
//
//        rpc.query({
//            model: 'metro.genie.suggestion',
//            method: 'get_sample_files',
//            args: []
//        }).then(function (files) {
//
//            if (!files.length) {
//                $dropdown.append(
//                    '<li style="padding:8px 16px;color:#999;">No sample files</li>'
//                );
//                return;
//            }
//
//            files.forEach(file => {
//                const $li = $('<li>', {
//                    text: file.name,
//                    css: {
//                        padding: '8px 16px',
//                        cursor: 'pointer'
//                    }
//                });
//
//                $li.on('click', function (e) {
//                    e.stopPropagation();
//                    window.open(`/web/content/${file.id}?download=true`, '_blank');
//                    $dropdown.remove();
//                });
//
//                $dropdown.append($li);
//            });
//        });
//    });
//
//    // Close dropdown on outside click
//    $(document).on('click', function () {
//        $('.custom-sample-dropdown').remove();
//    });
//});







odoo.define('metro_genie.sample_files_dropdown', function (require) {
    "use strict";

    const rpc = require('web.rpc');

    $(document).on('click', '.sample-files-btn', function (e) {
        e.preventDefault();
        e.stopPropagation();

        $('.custom-sample-dropdown').remove();

        const btn = this;
        const rect = btn.getBoundingClientRect();

        const $dropdown = $('<ul>', {
            class: 'custom-sample-dropdown',
            css: {
                position: 'fixed',              // 🔥 IMPORTANT
                top: rect.bottom + 'px',        // below button
                left: rect.left + 'px',
                background: '#fff',
                border: '1px solid #ccc',
                zIndex: 10000,
                listStyle: 'none',
                padding: '5px 0',
                minWidth: rect.width + 'px',
                maxHeight: '260px',
                overflowY: 'auto',
                boxShadow: '0 2px 6px rgba(0,0,0,0.15)',
                borderRadius: '4px'
            }
        });

        $('body').append($dropdown);

        rpc.query({
            model: 'metro.genie.suggestion',
            method: 'get_sample_files',
            args: []
        }).then(function (files) {

            if (!files.length) {
                $dropdown.append(
                    '<li style="padding:8px 16px;color:#999;">No sample files</li>'
                );
                return;
            }

            files.forEach(file => {
                const $li = $('<li>', {
                    text: file.name,
                    css: {
                        padding: '8px 16px',
                        cursor: 'pointer'
                    }
                });

                $li.on('click', function (e) {
                    e.stopPropagation();
                    window.open(`/web/content/${file.id}?download=true`, '_blank');
                    $dropdown.remove();
                });

                $dropdown.append($li);
            });
        });
    });

    // close on outside click
    $(document).on('click', function () {
        $('.custom-sample-dropdown').remove();
    });
});


