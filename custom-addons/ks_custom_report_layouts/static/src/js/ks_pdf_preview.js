odoo.define('ks_custom_report_layouts.ks_pdf_preview', function(require) {

    var DocumentViewer = require('mail.DocumentViewer');
    var core = require('web.core');
    var ajax = require('web.ajax');
    var ks_file_data = undefined;

    function KsViewPDF(parent, action) {
        var self = this;
        var ks_activeAttachmentID = action.params.attachment_id;
        var ks_attachment = [{id: ks_activeAttachmentID, is_main: false, mimetype: 'application/pdf', name: 'Sample View',
                        url: "/web/content/" + ks_activeAttachmentID + "?download=true"}]
        var ks_attachmentViewer = new DocumentViewer(self,ks_attachment,ks_activeAttachmentID);
        ks_attachmentViewer.appendTo($('body'));
    }

    core.action_registry.add("ks_view_report_pdf", KsViewPDF);
});
