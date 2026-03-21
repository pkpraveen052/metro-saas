import io
import xlsxwriter
import base64
from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import ValidationError

class PurchasePriceHistoryWizard(models.TransientModel):
    _name = 'purchase.price.history.wizard'
    _description = 'Purchase Price History Wizard'

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    template_id = fields.Many2one('product.template', string='Product')
    product_id = fields.Many2one('product.product', string='Product')
    active_id = fields.Many2one('product.template', string='Product')



    def action_export_purchase_price_history(self):
        self.ensure_one()
        
        if self.start_date > self.end_date:
            raise ValidationError("Start Date cannot be greater than End Date.")

        ICPSudo = self.env['ir.config_parameter'].sudo()
        if self.product_id:
            active_id = self.product_id.product_tmpl_id
        else:
            active_id = self.template_id
        domain = [
            ('product_id.product_tmpl_id', '=', active_id.id),
            ('order_id.date_order', '>=', self.start_date),
            ('order_id.date_order', '<=', self.end_date)
        ]
        
        purchase_order_status = ICPSudo.get_param('purchase_order_status', 'purchase')

        if purchase_order_status == 'purchase':
            domain.append(('state', '=', 'purchase'))
        else:
            domain.append(('state', 'in', ('purchase', 'done')))

        purchase_order_line_ids = self.env['purchase.order.line'].sudo().search(
            domain, order='create_date desc'
        )

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Purchase Price History')

        # Add the company name, start date, and end date
        company_name = self.env.company.name
        worksheet.write(0, 0, 'Company Name:')
        worksheet.write(0, 1, company_name)

        worksheet.write(1, 0, 'Start Date:')
        worksheet.write(1, 1, self.start_date.strftime('%d/%m/%Y'))

        worksheet.write(2, 0, 'End Date:')
        worksheet.write(2, 1, self.end_date.strftime('%d/%m/%Y'))

        # Leave a blank row before the headers
        headers = ['Product', 'Purchase Order', 'Purchase Order Date', 'Vendor', 'Purchase Person', 'Quantity', 'Price', 'Total Price']
        for col, header in enumerate(headers):
            worksheet.write(4, col, header)

        # Define a format for two decimal digits
        currency_format = workbook.add_format({'num_format': '#,##0.00'})

        # Write the data to the Excel sheet
        row = 5
        for line in purchase_order_line_ids:
            worksheet.write(row, 0, line.product_id.product_tmpl_id.name)
            worksheet.write(row, 1, line.order_id.name)
            worksheet.write(row, 2, line.order_id.date_order.strftime('%d/%m/%Y'))
            worksheet.write(row, 3, line.partner_id.name)
            worksheet.write(row, 4, line.order_id.user_id.name)
            worksheet.write(row, 5, line.product_qty)
            worksheet.write(row, 6, line.price_unit, currency_format)
            worksheet.write(row, 7, line.price_total, currency_format)
            row += 1

        workbook.close()
        output.seek(0)

        # Create an attachment and return it as a download
        attachment = self.env['ir.attachment'].create({
            'name': f'{active_id.name}_Purchase_Price_History_{self.start_date}_{self.end_date}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'store_fname': f'{active_id.name}_Purchase_Price_History_{self.start_date}_{self.end_date}.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        download_url = '/web/content/%s?download=true' % (attachment.id)
        return {
            'type': 'ir.actions.act_url',
            'url': download_url,
            'target': 'self',
        }
