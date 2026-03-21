from odoo import http
from odoo.http import request
import subprocess,os

class ServiceManagementPortal(http.Controller):
    @http.route(['/my/service_management/<int:service_id>'], type='http', auth="public", website=True)
    def service_management_preview(self, service_id):
        service = request.env['service.management'].sudo().browse(service_id)
        return request.render('metroerp_service_management.service_portal_template', {
            'service': service
        })

    @http.route(['/my/service_management/download/<int:service_id>'], type='http', auth="public", website=True)
    def service_management_download(self, service_id):
        service = request.env['service.management'].sudo().browse(service_id)
        report = service.template_id.report_id
        docx = report._render_docx_docx([service.id])

        # Save the DOCX file temporarily
        docx_file_path = "/tmp/temp_report.docx"
        pdf_file_path = "/tmp/temp_report.pdf"

        with open(docx_file_path, "wb") as docx_file:
            docx_file.write(docx[0])

        # Convert DOCX to PDF using LibreOffice
        try:
            subprocess.run([
                "libreoffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                "/tmp",
                docx_file_path
            ], check=True)
        except subprocess.CalledProcessError as e:
            # Handle conversion error
            return request.make_response("Error during DOCX to PDF conversion: %s" % e, status=500)

        # Read the converted PDF
        with open(pdf_file_path, "rb") as pdf_file:
            pdf_content = pdf_file.read()

        # Clean up temporary files
        import os
        os.remove(docx_file_path)
        os.remove(pdf_file_path)
        # Return PDF response
        pdf_http_headers = [
            ("Content-Type", "application/pdf"),
            ('Content-Disposition', f'attachment; filename="service_report_{service_id}.pdf"')
        ]
        # Return PDF response
        return request.make_response(pdf_content, headers=pdf_http_headers)

