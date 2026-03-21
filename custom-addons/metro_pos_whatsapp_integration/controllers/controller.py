from odoo import http
from odoo.http import request
from werkzeug.wsgi import ClosingIterator
from werkzeug.utils import secure_filename
from io import BytesIO
import base64
import logging
_logger = logging.getLogger(__name__)

class MyController(http.Controller):

    @http.route('/pos/generate_receipt_pdf', type='json', auth='user')
    def generate_receipt_pdf(self, order_id):
        # Fetch the order
        order = request.env['pos.order'].browse(order_id)
        if not order.exists():
            return {"error": "Order not found"}

        # Render the report to get the PDF content
        report_name = 'point_of_sale.OrderReceipt'
        pdf_content, _ = request.env['ir.actions.report'].sudo()._get_report_from_name(report_name).render_qweb_pdf([order.id])

        # Encode PDF content for response
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        pdf_url = f'/pos/download_receipt_pdf?order_id={order_id}'
        
        return {'pdf_url': pdf_url}

    @http.route('/pos/download_receipt_pdf', type='http', auth='user')
    def download_receipt_pdf(self, order_id, **kwargs):
        order = request.env['pos.order'].browse(order_id)
        if not order.exists():
            return request.not_found()

        report_name = 'point_of_sale.OrderReceipt'
        pdf_content, _ = request.env['ir.actions.report'].sudo()._get_report_from_name(report_name).render_qweb_pdf([order.id])

        pdf_filename = f"order_{order_id}.pdf"
        pdf_file = BytesIO(pdf_content)
        
        response = request.make_response(
            pdf_file.getvalue(),
            headers=[('Content-Type', 'application/pdf'), ('Content-Disposition', f'attachment; filename={secure_filename(pdf_filename)}')]
        )
        return response
