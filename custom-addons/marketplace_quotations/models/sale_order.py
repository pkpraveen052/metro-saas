from odoo import fields, models,api, _
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def write(self, vals):
        
        res = super(SaleOrder, self).write(vals)
        for obj in self:
            if self.env.ref('marketplace_quotations.demo_record_1') and obj.tag_ids and self.env.ref('marketplace_quotations.demo_record_1').id in obj.tag_ids.ids and 'state' in vals and vals.get('state') == 'sale':
                try:
                    if obj.company_id.market_place_order_notify_ids:
                        for user in obj.company_id.market_place_order_notify_ids:
                            template_obj = self.env['mail.template'].browse(self.env.ref('marketplace_quotations.email_template_marketplace').id)
                            template_obj.with_context(
                                {'email_to': user.email}).send_mail(obj.id, force_send=False)
                except Exception as e:
                    _logger.exception("Error arised while sending order confirmed marketplace notification to the the Users:\n %s" % repr(e))
                    msg = _('Error arised while sending order confirmed marketplace notification to the Users: %s', repr(e))
                    obj.message_post(body=msg)
        auto_invoice = self.env['ir.config_parameter'].sudo().get_param('base_setup.auto_invoice', default=False)           
        if auto_invoice:
            # try:
            #     if obj.picking_ids:
            #         for picking in obj.picking_ids:
            #             if picking.state == 'assigned':
            #                 for move_line in picking.move_line_ids_without_package:
            #                     move_line.write({'qty_done': move_line.product_uom_qty})
            #                     picking.button_validate()

            # except Exception as picking_error:
            #     _logger.exception("Error occurred while processing picking:\n %s" % repr(picking_error))
            #     picking_msg = _('Error occurred while processing picking: %s', repr(picking_error))
            #     obj.message_post(body=picking_msg)
            try:
                if obj.invoice_status == 'to invoice':
                    obj._create_invoices()
                    obj.invoice_ids.action_post()
                    for invoice in obj.invoice_ids:
                        if not invoice.partner_id.peppol_identifier:
                            values = {'peppol_identifier': "SGUEN" + invoice.partner_id.l10n_sg_unique_entity_number}
                            invoice.partner_id.sudo().write(values)
                        else:
                            _logger.error("UEN is None. Cannot create peppol_identifier.")
                        if not invoice.partner_id.country_id:
                            country_singapore = self.env['res.country'].search([('code', '=', 'SG')], limit=1)
                            if country_singapore:
                                values = {'country_id': country_singapore.id}
                                invoice.partner_id.write(values)
                        else:
                            _logger.error("Singapore not found in res.country. Cannot set country.")
                        tax_objs = invoice.invoice_line_ids.mapped('tax_ids')
                        for tax_obj in tax_objs:
                            if tax_obj.amount > 0 and tax_obj.unece_categ_id.code != 'SR':
                                categ_id = self.env['unece.code.list'].search([('code', '=', 'SR')], limit=1)
                                tax_obj.sudo().write({'unece_categ_id': categ_id.id})
                           
                        if invoice.partner_id.peppol_identifier and invoice.partner_id.country_id:
                            invoice.action_send_via_peppol()
            except Exception as invoice_error:
                _logger.exception("Error occurred while processing invoicing:\n %s" % repr(invoice_error))
                invoice_msg = _('Error occurred while processing invoicing: %s', repr(invoice_error))
                obj.message_post(body=invoice_msg)      
                                              
        return res

    # def write(self, vals):
    #     # auto_invoice = self.env['ir.config_parameter'].sudo().get_param('base_setup.auto_invoice', default=False)
    #     # if not auto_invoice: 
    #     #     return super(SaleOrder, self).write(vals)
    #     res = super(SaleOrder, self).write(vals)
    #     for obj in self:
    #         if self.env.ref('marketplace_quotations.demo_record_1') and obj.tag_ids and self.env.ref('marketplace_quotations.demo_record_1').id in obj.tag_ids.ids and 'state' in vals and vals.get('state') == 'sale':
    #             try:
    #                 if obj.company_id.market_place_order_notify_ids:
    #                     for user in obj.company_id.market_place_order_notify_ids:
    #                         template_obj = self.env['mail.template'].browse(self.env.ref('marketplace_quotations.email_template_marketplace').id)
    #                         template_obj.with_context(
    #                             {'email_to': user.email}).send_mail(obj.id, force_send=False)
    #             except Exception as e:
    #                 _logger.exception("Error arised while sending order confirmed marketplace notification to the the Users:\n %s" % repr(e))
    #                 msg = _('Error arised while sending order confirmed marketplace notification to the Users: %s', repr(e))
    #                 obj.message_post(body=msg)   

    #             try:
    #                 if obj.picking_ids:
    #                     for picking in obj.picking_ids:
    #                         if picking.state == 'assigned':
    #                             for move_line in picking.move_line_ids_without_package:
    #                                 move_line.write({'qty_done': move_line.product_uom_qty})
    #                             picking.button_validate()

    #             except Exception as picking_error:
    #                 _logger.exception("Error occurred while processing picking:\n %s" % repr(picking_error))
    #                 picking_msg = _('Error occurred while processing picking: %s', repr(picking_error))
    #                 obj.message_post(body=picking_msg)

    #             try:
    #                 if obj.invoice_status == 'to invoice':
    #                     payment_inv_model = self.env['sale.advance.payment.inv'].create({
    #                         'advance_payment_method': 'delivered'})
    #                     payment_inv_model.create_invoices()
    #                     obj.invoice_ids.action_post()
    #                     for invoice in obj.invoice_ids:
    #                         invoice.action_send_via_peppol()

    #             except Exception as invoice_error:
    #                 _logger.exception("Error occurred while processing invoicing:\n %s" % repr(invoice_error))
    #                 invoice_msg = _('Error occurred while processing invoicing: %s', repr(invoice_error))
    #                 obj.message_post(body=invoice_msg)                                   
    #     return res