# -*- encoding: utf-8 -*-
from odoo import _, http
from odoo.http import request, JsonRequest, AuthenticationError, SessionExpiredException, ustr
import werkzeug
from odoo.addons.web.controllers.main import Home
from odoo.addons.base_setup.controllers.main import BaseSetup
from odoo.addons.web.controllers.main import Binary
from odoo.exceptions import AccessError
import logging
import functools
import odoo
import odoo.exceptions
import base64
import io
from odoo import http, tools
from odoo.http import content_disposition, dispatch_rpc, request, serialize_exception as _serialize_exception, Response
from odoo.tools.mimetypes import guess_mimetype
from odoo.modules import get_module_path, get_resource_path
import werkzeug.exceptions
from odoo.tools.misc import xlsxwriter
import ast
import traceback
_logger = logging.getLogger(__name__)
#----------------------------------------------------------
# Odoo Web helpers
#----------------------------------------------------------

db_monodb = http.db_monodb
# ----------------------------------------------------------
# web/controllers/main.py - Inherited
# ----------------------------------------------------------
class DebugModeEnable(Home):

    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        debug = kw.get('debug', False) if 'debug' in kw.keys() else False
        user_id = request.context.get('uid', False)
        if (debug == '1' or debug == 'assets' or debug == 'assets,tests') and user_id:
            user = request.env['res.users'].sudo().browse(user_id)
            if not user.has_group('metroerp_customizations.group_debug_mode_enable'):
                return werkzeug.utils.redirect('/web?debug=0')
        return super(DebugModeEnable, self).web_client(s_action=s_action, **kw)


# ----------------------------------------------------------
# base_setup/controllers/main.py - Inherited
# ----------------------------------------------------------
class BaseSetupInherited(BaseSetup):

    @http.route('/base_setup/data', type='json', auth='user')
    def base_setup_data(self, **kw):
        if not request.env.user.has_group('base.group_erp_manager') and not request.env.user.has_group('metroerp_customizations.sub_admin_group'):
            raise AccessError(_("Access Denied"))

        cr = request.cr
        cr.execute("""
            SELECT count(*)
              FROM res_users
             WHERE active=true AND
                   share=false
        """)
        active_count = cr.dictfetchall()[0].get('count')

        cr.execute("""
            SELECT count(u.*)
            FROM res_users u
            WHERE active=true AND
                  share=false AND
                  NOT exists(SELECT 1 FROM res_users_log WHERE create_uid=u.id)
        """)
        pending_count = cr.dictfetchall()[0].get('count')

        cr.execute("""
           SELECT id, login
             FROM res_users u
            WHERE active=true AND
                  share=false AND
                  NOT exists(SELECT 1 FROM res_users_log WHERE create_uid=u.id)
         ORDER BY id desc
            LIMIT 10
        """)
        pending_users = cr.fetchall()

        return {
            'active_users': active_count,
            'pending_count': pending_count,
            'pending_users': pending_users,
        }

# ----------------------------------------------------------
# web/controllers/main.py - Inherited
# ----------------------------------------------------------
class BinaryInherited(Binary):

    @http.route([
        '/web/binary/company_logo',
        '/logo',
        '/logo.png',
    ], type='http', auth="none", cors="*")
    def company_logo(self, dbname=None, **kw):
        imgname = 'logo'
        imgext = '.png'
        placeholder = functools.partial(get_resource_path, 'metroerp_customizations', 'static', 'src', 'img') # Overidden to replace the 'web' with 'metroerp_customizations'
        uid = None
        if request.session.db:
            dbname = request.session.db
            uid = request.session.uid
        elif dbname is None:
            dbname = db_monodb()

        if not uid:
            uid = odoo.SUPERUSER_ID

        if not dbname:
            response = http.send_file(placeholder(imgname + imgext))
        else:
            try:
                # create an empty registry
                registry = odoo.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    company = int(kw['company']) if kw and kw.get('company') else False
                    if company:
                        cr.execute("""SELECT logo_web, write_date
                                        FROM res_company
                                       WHERE id = %s
                                   """, (company,))
                    else:
                        cr.execute("""SELECT c.logo_web, c.write_date
                                        FROM res_users u
                                   LEFT JOIN res_company c
                                          ON c.id = u.company_id
                                       WHERE u.id = %s
                                   """, (uid,))
                    row = cr.fetchone()
                    if row and row[0]:
                        image_base64 = base64.b64decode(row[0])
                        image_data = io.BytesIO(image_base64)
                        mimetype = guess_mimetype(image_base64, default='image/png')
                        imgext = '.' + mimetype.split('/')[1]
                        if imgext == '.svg+xml':
                            imgext = '.svg'
                        response = http.send_file(image_data, filename=imgname + imgext, mimetype=mimetype, mtime=row[1])
                    else:
                        response = http.send_file(placeholder('nologo.png'))
            except Exception:
                response = http.send_file(placeholder(imgname + imgext))

        return response


class InvoiceExcelReportController(http.Controller):
    @http.route([
       '/invoicing/excel_report/<string:move_ids>',
    ], type='http', auth="user", csrf=False)
    def get_sale_excel_report(self, move_ids=None, **args):
        move_ids = request.env['account.move'].sudo().browse(ast.literal_eval(move_ids))
        company_name = request.env.user.company_id.name
        response = request.make_response(
            None,
            headers=[
               ('Content-Type', 'application/vnd.ms-excel'),
               ('Content-Disposition', content_disposition(company_name + ' Usage Report.xlsx'))
           ]
        )
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("invoices")

        font_size = 12
        format_1 = workbook.add_format({
            'bold': True, 
            'align': 'center',
            'bg_color': 'AED581',
            'font_size': font_size,
            'valign': 'vcenter',
            'border': 1,
        })
        format_2 = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'num_format':'0.00',
        })

        sheet.set_row(0, 35)
        sheet.set_column('A:A', 30)
        sheet.set_column('B:B', 30)
        sheet.set_column('C:C', 30)
        sheet.set_column('D:D', 25)
        sheet.set_column('E:E', 25)

        row = 0
        col = 0
        sheet.write(row, col, 'Invoice Number', format_1)
        sheet.write(row, col + 1, 'Customer Name', format_1)
        sheet.write(row, col + 2, 'Invoice/Bill Date', format_1)
        sheet.write(row, col + 3, 'Total Signed', format_1)
        sheet.write(row, col + 4, 'Status', format_1)

        formatted_state = {'draft': 'Invoiced', 'posted': 'Posted', 'cancel': 'Cancelled'}
        for rec in move_ids:
            formatted_date = ''
            if rec.invoice_date:
                formatted_date = rec.invoice_date.strftime("%Y-%m-%d")
            sheet.write(row + 1, col, rec.name, format_2)
            sheet.write(row + 1, col + 1, rec.invoice_partner_display_name, format_2)
            sheet.write(row + 1, col + 2, formatted_date, format_2)
            sheet.write(row + 1, col + 3, rec.amount_total_signed, format_2)
            sheet.write(row + 1, col + 4, formatted_state.get(rec.state, ''), format_2)
            row += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
        return response


def _handle_exception(self, exception):
    """Override this method from http.py chnages into odoo regarding string"""
    try:
        return super(JsonRequest, self)._handle_exception(exception)
    except Exception:
        if not isinstance(exception, SessionExpiredException):
            if exception.args and exception.args[0] == "bus.Bus not available in test mode":
                _logger.info(exception)
            elif isinstance(exception, (odoo.exceptions.UserError,
                                        werkzeug.exceptions.NotFound)):
                _logger.warning(exception)
            else:
                _logger.exception("Exception during JSON request handling.")
        error = {
            'code': 200,
            'message': "Metro Server Error",
            'data': serialize_exception(exception),
        }
        if isinstance(exception, werkzeug.exceptions.NotFound):
            error['http_status'] = 404
            error['code'] = 404
            error['message'] = "404: Not Found"
        if isinstance(exception, AuthenticationError):
            error['code'] = 100
            error['message'] = "ERP Session Invalid"
        if isinstance(exception, SessionExpiredException):
            error['code'] = 100
            error['message'] = "ERP Session Expired"
        return self._json_response(error=error)

setattr(JsonRequest, '_handle_exception', _handle_exception)

def serialize_exception(e):
    return {
        "name": type(e).__module__ + "." + type(e).__name__ if type(e).__module__ else type(e).__name__,
        "debug": traceback.format_exc(),
        "message": ustr(e),
        "arguments": e.args,
        "context": getattr(e, 'context', {}),
    }