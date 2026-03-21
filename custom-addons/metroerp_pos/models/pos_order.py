from odoo import models, api
import pytz
from odoo import api, fields, models, tools, _
import base64
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


import logging
_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'


    @api.model
    def _prepare_invoice_vals(self):
        vals = super(PosOrder, self)._prepare_invoice_vals()
        note = self.note or ''
        terms = ''
        if self.env.company.sales_invoice_tc:
            terms = self.with_context(lang=self.partner_id.lang).env.company.sales_invoice_tc

        narration = note + '\n' + terms if note else terms
        vals['narration'] = narration

        return vals

    def action_receipt_to_customer(self, name, client, ticket):
        """
        Sends a customized email with a receipt to the customer using the provided email template structure.
        """
        if not self or not client.get('email'):
            return False
        # Prepare dynamic values
        company = self.company_id
        company_logo = company.logo or False
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # Ensure the company logo is displayed with the correct URL
        logo_url = f"{base_url}/logo.png?company={company.id}"
        # logo_base64 = company_logo and f"data:image/png;base64,{company_logo.decode('utf-8')}" or False
        user_signature = self.env.user.signature or ""
        company_phone = company.phone or ""
        company_email = (
            f' | <a href="mailto:{company.email}" style="text-decoration:none; color: #454748;">{company.email}</a>'
            if company.email else ""
        )
        company_website = (
            f' | <a href="{company.website}" style="text-decoration:none; color: #454748;">{company.website}</a>'
            if company.website else ""
        )

        # Format the email content
        email_content = """
        <div style="margin: 0px; padding: 0px;">
            <table border="0" cellpadding="0" cellspacing="0" style="padding-top:16px;background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
                <tr>
                    <td align="center">
                        <table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 24px; background-color: white; color: #454748; border-collapse:separate;">
                            <tbody>
                                <!-- HEADER -->
                                <tr>
                                    <td align="center" style="min-width: 590px;">
                                        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: white; padding: 0; border-collapse:separate;">
                                            <tr>
                                                <td valign="middle">
                                                    <span style="font-size: 20px; font-weight: bold;">
                                                        Your Payment Receipt
                                                    </span>
                                                    <br/>
                                                </td>
                                                <td valign="middle" align="right">
                                                    <img src="{logo_url}" style="padding: 0px; margin: 0px; height: 48px;" alt="{company_name}" id="mail_template_images"/>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td colspan="2" style="text-align:center;">
                                                <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin:4px 0px 17px 0px;"/>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <!-- CONTENT -->
                                <tr>
                                    <td style="min-width:590px;">
                                        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: white; padding: 0; border-collapse:separate;">
                                            <tbody>
                                                <tr>
                                                    <td valign="top" style="font-size:13px;">
                                                        <div>
                                                            <p style="font-size: 13px;">
                                                                Dear {client_name},<br/><br/>
                                                                Thank you for your payment.
                                                                Here is your payment receipt <strong>{receipt_name}</strong> amounting
                                                                to <strong>{formatted_amount_total}</strong> from {company_name}.
                                                                <br /><br />
                                                                Do not hesitate to contact us if you have any questions.
                                                                <br/><br/>
                                                                Best regards,
                                                                <br/>
                                                                {user_signature}
                                                            </p>
                                                            <br/>
                                                        </div>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </td>
                                </tr>
                                <!-- FOOTER -->
                                <tr>
                                    <td align="center" style="min-width: 590px; padding: 0 8px 0 8px; font-size:11px;">
                                        <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 4px 0px;"/>
                                        <b style="background-color: white;">{company_name}</b><br/>
                                        <div style="color: #999999;">
                                            {company_phone}
                                            {company_email}
                                            {company_website}
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </td>
                </tr>
                <!-- POWERED BY -->
                <tr>
                    <td align="center" style="min-width: 590px;">
                        <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: #F1F1F1; color: #454748; padding: 8px; border-collapse:separate;">
                            <tr><td style="text-align: center; font-size: 13px;">
                            Powered by <a href="https://www.metrogroup.solutions/solutions/accounting-system" style="color: #875A7B;">Metro Accounting System</a>
                            </td></tr>
                        </table>
                    </td>
                </tr>
            </table>
        </div>
        """.format(
            client_name=client['name'],
            receipt_name=name,
            formatted_amount_total="{:.2f}".format(self.amount_total),
            company_name=company.name,
            company_id=company.id,  # Ensure you pass the company ID here
            user_signature=user_signature,
            company_phone=company_phone,
            company_email=company_email,
            company_website=company_website,
            logo_url=logo_url,
        )

        # Receipt attachment
        filename = f'Receipt-{name}.jpg'
        receipt = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': ticket,
            'res_model': 'pos.order',
            'res_id': self.ids[0],
            'mimetype': 'image/jpeg',
        })

        # Prepare mail values
        mail_values = {
            'subject': f'Your Payment Receipt {name}',
            'email_to': client.get('email'),
            'body_html': email_content,
            'attachment_ids': [(6, 0, [receipt.id])],
        }

        # Create and send the mail
        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()

   

    def action_get_pos_invoice(self, name):
        """Custom method. Called from POS UI. Custom method that will geenrate the Invoice and return the URL to download the PDF document. """
        if not self.account_move:
            raise UserError(_("You haven't generated the Invoice for this Order on the Payment Screen."))
        res_config = self.env['ks.report.configuration'].sudo().search([('company_id','=',self.company_id.id),('name','=','Invoice')], limit=1)
        report = self.env.ref('account.account_invoices')._render_qweb_pdf(self.account_move.id)
        invoice_number = self.account_move.name
        formatted_filename = invoice_number.replace('/', '-')
        filename = f"{formatted_filename}.pdf"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(report[0]),
            'res_model': 'pos.order',
            'res_id': self.ids[0],
            'mimetype': 'application/pdf'
        })
        web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{web_base_url}/web/content/{attachment.id}/{filename}"
    


    def _prepare_invoice_line(self, order_line):
        invoice_line_vals = super(PosOrder, self)._prepare_invoice_line(order_line)

        description_sale = order_line.product_id.description_sale or ''
        default_code = order_line.product_id.default_code or ''
        
        if description_sale and default_code:
            name = f"{default_code}\n{description_sale}"
        elif description_sale:
            name = description_sale
        elif default_code:
            name = default_code
        else:
            name = ' '

        invoice_line_vals['name'] = name        
        return invoice_line_vals



    def change_payment(self, payment_lines):
        """
        This method get changes payment line
        pass line to add_payment method create new payment method line in main pos order
        """
        self.ensure_one()
        orders = self
        # Removing zero lines
        precision = self.pricelist_id.currency_id.decimal_places
        payment_lines = [
            x
            for x in payment_lines
            if not float_is_zero(x["amount"], precision_digits=precision)
        ]
        if payment_lines:
            self.payment_ids.with_context().unlink()
            # Create new payment
            for line in payment_lines:
                self.add_payment(line)
        return orders
    
    
    def open_cancel_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }


    def cancel_pos_order(self):
        for order in self:
            self._reverse_order_stock_picking(order)
            order.payment_ids.unlink()
            order.write({'state': 'cancel'})

    def _reverse_order_stock_picking(self, order):
        for picking in order.picking_ids:
            if picking.state == 'done':
                # Create a new picking for the return
                return_picking = picking.copy({
                    'move_lines': [],
                    'state': 'draft',
                    'origin': 'Return of %s' % order.name,
                    'location_id': picking.location_dest_id.id,
                    'location_dest_id': picking.location_id.id,
                })
                for move in picking.move_lines:
                    move.copy({
                        'picking_id': return_picking.id,
                        'location_id': move.location_dest_id.id,  # Destination becomes source
                        'location_dest_id': move.location_id.id,  # Source becomes destination
                        'quantity_done': move.quantity_done,  # Set the quantity to the done quantity
                    })
                return_picking.action_confirm()
                return_picking.action_assign()
                return_picking.button_validate()

            elif picking.state not in ('cancel', 'done'):
                picking.action_cancel()

   
