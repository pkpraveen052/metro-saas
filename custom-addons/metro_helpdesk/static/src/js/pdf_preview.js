odoo.define('metro_helpdesk.custom_attachment_preview', function (require) {
    'use strict';

    var fieldRegistry = require('web.field_registry');
    var relationalFields = require('web.relational_fields');
    var DocumentViewer = require('mail.DocumentViewer');
    var core = require('web.core');

    var QWeb = core.qweb;

    var FieldMany2ManyBinaryPreview = relationalFields.FieldMany2ManyBinary.extend({
        template: 'metro_helpdesk.FieldMany2ManyBinaryPreview',
        events: _.extend({}, relationalFields.FieldMany2ManyBinary.prototype.events, {
            'click .o_attachment_view': '_onAttachmentView',
        }),
        _render: function () {
            this._super.apply(this, arguments);
            this.$('.o_attachment_view').each(function () {
                var $el = $(this);
                $el.html(QWeb.render('AttachmentPreview', {
                    url: $el.data('url'),
                    name: $el.data('name'),
                    mimetype: $el.data('mimetype')
                }));
            });
        },
        _onAttachmentView: function (ev) {
            ev.preventDefault();
            var attachmentId = $(ev.currentTarget).data('id');
            this._rpc({
                model: 'ir.attachment',
                method: 'search_read',
                args: [[['id', '=', attachmentId]], ['name', 'mimetype', 'url']],
            }).then(function (attachments) {
                var attachmentViewer = new DocumentViewer(this, attachments, 0);
                attachmentViewer.appendTo($('body'));
            }.bind(this));
        },
    });

    fieldRegistry.add('many2many_binary_preview', FieldMany2ManyBinaryPreview);

    return FieldMany2ManyBinaryPreview;
});
