# -*- encoding: utf-8 -*-

from odoo.addons.web.controllers.main import ReportController
from werkzeug.exceptions import Forbidden
import logging
import json

import werkzeug
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi
from werkzeug.urls import url_encode, url_decode, iri_to_uri
from odoo.tools import image_process, topological_sort, html_escape, pycompat, ustr, apply_inheritance_specs, lazy_property
from odoo.tools.safe_eval import safe_eval, time
from odoo import http, tools
from odoo.http import content_disposition, dispatch_rpc, request, serialize_exception as _serialize_exception, Response

_logger = logging.getLogger(__name__)


class ReportControllerInherit(ReportController):

    @http.route(['/report/download'], type='http', auth="user")
    def report_download(self, data, token, context=None):
        """This function is used by 'action_manager_report.js' in order to trigger the download of
        a pdf/controller report.
        # Overridden method from base to set the partner name in the outstanding and activity report.
        :param data: a javascript array JSON.stringified containg report internal url ([0]) and
        type [1]
        :returns: Response with a filetoken cookie and an attachment header
        """
        requestcontent = json.loads(data)
        url, type = requestcontent[0], requestcontent[1]
        try:
            if type in ['qweb-pdf', 'qweb-text']:
                converter = 'pdf' if type == 'qweb-pdf' else 'text'
                extension = 'pdf' if type == 'qweb-pdf' else 'txt'

                pattern = '/report/pdf/' if type == 'qweb-pdf' else '/report/text/'
                reportname = url.split(pattern)[1].split('?')[0]

                docids = None
                if '/' in reportname:
                    reportname, docids = reportname.split('/')

                if docids:
                    # Generic report:
                    response = self.report_routes(reportname, docids=docids, converter=converter, context=context)
                else:
                    # Particular report:
                    data = dict(url_decode(url.split('?')[1]).items())  # decoding the args represented in JSON
                    if 'context' in data:
                        context, data_context = json.loads(context or '{}'), json.loads(data.pop('context'))
                        context = json.dumps({**context, **data_context})
                    response = self.report_routes(reportname, converter=converter, context=context, **data)

                report = request.env['ir.actions.report']._get_report_from_name(reportname)
                # Custom code start
                if report.name in ['Activity Statement', 'Outstanding Statement'] and data_context:
                    if data_context.get('active_model', False) == 'res.partner':
                        partner_id = request.env['res.partner'].sudo().browse(data_context.get('active_id', False))
                        if partner_id and report.name == 'Activity Statement':
                            filename = '%s_Activity_Statement.%s' % (partner_id.name, extension)
                        elif partner_id and report.name == 'Outstanding Statement':
                            filename = '%s_Outstanding_Statement.%s' % (partner_id.name, extension)
                        else:
                            filename = "%s.%s" % (report.name, extension)
                    else:
                        filename = "%s.%s" % (report.name, extension)
                else:
                    filename = "%s.%s" % (report.name, extension)
                # Custom code end
                if docids:
                    ids = [int(x) for x in docids.split(",")]
                    obj = request.env[report.model].browse(ids)
                    if report.print_report_name and not len(obj) > 1:
                        report_name = safe_eval(report.print_report_name, {'object': obj, 'time': time})
                        filename = "%s.%s" % (report_name, extension)
                response.headers.add('Content-Disposition', content_disposition(filename))
                response.set_cookie('fileToken', token)
                return response
            elif type == 'qweb-xml':
                converter = 'xml' if type == 'qweb-xml' else 'text'
                extension = 'xbrl' if type == 'qweb-xml' else 'xml'

                pattern = '/report/xml/' if type == 'qweb-xml' else '/report/xml/'
                reportname = url.split(pattern)[1].split('?')[0]

                docids = None
                if '/' in reportname:
                    reportname, docids = reportname.split('/')

                if docids:
                    # Generic report:
                    response = self.report_routes(reportname, docids=docids, converter=converter, context=context)
                else:
                    # Particular report:
                    data = dict(url_decode(url.split('?')[1]).items())  # decoding the args represented in JSON
                    if 'context' in data:
                        context, data_context = json.loads(context or '{}'), json.loads(data.pop('context'))
                        context = json.dumps({**context, **data_context})
                    response = self.report_routes(reportname, converter=converter, context=context, **data)

                report = request.env['ir.actions.report']._get_report_from_name(reportname)
                filename = "%s.%s" % (report.name, extension)

                response.headers.add('Content-Disposition', content_disposition(filename))
                response.set_cookie('fileToken', token)
                return response
            else:
                return super().report_download(data, token, context)
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "Metro Server Error",
                'data': se
            }
            res = request.make_response(html_escape(json.dumps(error)))
            raise werkzeug.exceptions.InternalServerError(response=res) from e
