# Copyright (C) Softhealer Technologies.
from odoo import fields, models,api,_
from odoo.exceptions import UserError
from odoo.http import request
import base64
import logging
_logger = logging.getLogger(__name__)

class PosConfig(models.Model):
    _inherit = 'pos.config'

    enable_whatsapp = fields.Boolean(string="Enable Whatsapp")

    whatsapp_method = fields.Selection([
        ('web', 'Web WhatsApp'),
        ('assistro', 'Assistro API')
    ], string="WhatsApp Sending Method", default='web')


class ResUsers(models.Model):
    _inherit = "res.users"

    sign = fields.Text(string='Signature')


class POSCustom(models.Model):
    _name = 'pos.order'
    _inherit = ['pos.order','portal.mixin','mail.thread', 'mail.activity.mixin','utm.mixin']

    use_assistro = fields.Boolean(related="company_id.use_assistro",string="Use Assistro")

    @api.model
    def action_get_pos_invoice_link(self,order_id):
        # Fetch the POS order based on the given order ID
        pos_session = self.env['pos.session'].search([('state', '=', 'opened')], limit=1)
        if not pos_session:
            raise UserError("No active POS session found.")
        
        # Fetch the latest POS order in the current session
        order = self.env['pos.order'].search([('session_id', '=', pos_session.id)], order='id desc', limit=1)
        invoice = self.env['account.move'].search([('pos_order_ids', '=',order.id)], limit=1)
        
        # Generate the URL for the share action
        portal_share = self.env['portal.share'].create({
        'res_model': 'account.move',
        'res_id': invoice.id,
        'partner_ids': [(6, 0, [self.env.user.partner_id.id])], 
        })

        # Compute the share link
        share_link = portal_share.share_link         
        
        return share_link
    
   