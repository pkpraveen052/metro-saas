from json import dumps as json_dumps, loads as json_loads
from werkzeug.urls import url_decode

from odoo.http import (
    content_disposition,
    request,
    route,
    serialize_exception as _serialize_exception,
)
from odoo.tools import html_escape
from odoo.tools.safe_eval import safe_eval, time

from odoo.addons.web.controllers.main import ReportController
from odoo import http
import json,subprocess

import base64


class DocxReportController(ReportController):

    @http.route([
        '/report/<converter>/<reportname>',
        '/report/<converter>/<reportname>/<docids>',
    ], type='http', auth='user', website=True)
    def report_routes(self, reportname, docids=None, converter=None, **data):
        """ NEW OVERIDDEN METHOD. """
        print("\nCUSTOM report_routes() >>>>>")
        print("reportname ==",reportname)
        print("docids ==",docids)
        print("converter ==",converter)
        print("data ==",data)
        report = request.env['ir.actions.report']._get_report_from_name(reportname)
        context = dict(request.env.context)

        if docids:
            docids = [int(i) for i in docids.split(',')]
        if data.get('options'):
            data.update(json.loads(data.pop('options')))
        if data.get('context'):
            # Ignore 'lang' here, because the context in data is the one from the webclient *but* if
            # the user explicitely wants to change the lang, this mechanism overwrites it.
            data['context'] = json.loads(data['context'])
            if data['context'].get('lang') and not data.get('force_context_lang'):
                del data['context']['lang']
            context.update(data['context'])
        if converter == 'html':
            html = report.with_context(context)._render_qweb_html(docids, data=data)[0]
            return request.make_response(html)
        elif converter == 'pdf' and "qweb-pdf" in report.report_type:
            print(" elif converter == 'pdf'")
            pdf = report.with_context(context)._render_qweb_pdf(docids, data=data)[0]
            print(" pdf....")
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            print(" return.....")
            return request.make_response(pdf, headers=pdfhttpheaders)
        elif converter == 'text':
            text = report.with_context(context)._render_qweb_text(docids, data=data)[0]
            texthttpheaders = [('Content-Type', 'text/plain'), ('Content-Length', len(text))]
            return request.make_response(text, headers=texthttpheaders)
        elif converter == "docx": #Metro custom code
            print("if converter == 'docx'")
            #docx = report.with_context(context)._render_docx_docx(docids, data=data)
            #docxhttpheaders = [
            #    (
            #        "Content-Type",
            #        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            #    ),
            #]
            #return request.make_response(docx, headers=docxhttpheaders)
            docx = report.with_context(context)._render_docx_docx(docids, data=data)
            encoded_content = base64.b64encode(docx[0]).decode('utf-8')
            docxhttpheaders = [
                (
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            ]
            return request.make_response(base64.b64decode(encoded_content), headers=docxhttpheaders)
        elif converter == "pdf" and "docx" in report.report_type:
            print("if converter == 'pdf' and 'docx'....")
            docx = report.with_context(context)._render_docx_docx(docids, data=data)

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
                ("Content-Type", "application/pdf")
            ]
            # Return PDF response
            return request.make_response(pdf_content, headers=pdf_http_headers)
        else:
            raise werkzeug.exceptions.HTTPException(description='Converter %s not implemented.' % converter)


    @route()
    def report_download(self, data, token, context=None):
        """
        Обрабатывает запрос на скачивание файла отчета
        """
        print("\nreport_download() >>>>>>")
        requestcontent = json_loads(data)
        url, type = requestcontent[0], requestcontent[1]
        try:
            if type in ["docx-docx", "docx-pdf"]:
                converter = "docx" if type == "docx-docx" else "pdf"
                extension = "docx" if type == "docx-docx" else "pdf"

                pattern = "/report/%s/" % ("docx" if type == "docx-docx" else "pdf")
                reportname = url.split(pattern)[1].split("?")[0]

                docids = None
                if "/" in reportname:
                    reportname, docids = reportname.split("/")

                if docids:
                    # Generic report:
                    response = self.report_routes(
                        reportname, docids=docids, converter=converter, context=context
                    )
                else:
                    # Particular report:
                    data = dict(
                        url_decode(url.split("?")[1]).items()
                    )  # decoding the args represented in JSON
                    if "context" in data:
                        context, data_context = json_loads(context or "{}"), json_loads(
                            data.pop("context")
                        )
                        context = json_dumps({**context, **data_context})
                    response = self.report_routes(
                        reportname, converter=converter, context=context, **data
                    )

                report = request.env["ir.actions.report"]._get_report_from_name(
                    reportname
                )
                filename = "%s.%s" % (report.name, extension)

                if docids:
                    ids = [int(x) for x in docids.split(",")]
                    obj = request.env[report.model].browse(ids)
                    if report.print_report_name and not len(obj) > 1:
                        report_name = safe_eval(
                            report.print_report_name, {"object": obj, "time": time}
                        )
                        filename = "%s.%s" % (report_name, extension)
                response.headers.add(
                    "Content-Disposition", content_disposition(filename)
                )
                response.set_cookie("fileToken", token)
                return response
            else:
                print("\nREturnnnnnnnnnnn")
                return super().report_download(data, token, context=context)
        except Exception as e:
            print("\nException..........")
            se = _serialize_exception(e)
            error = {"code": 200, "message": "Metro Server Error", "data": se}
            return request.make_response(html_escape(json_dumps(error)))
