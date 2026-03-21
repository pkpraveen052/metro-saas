# -*- coding: utf-8 -*-
from odoo import api, models, _


class Channel(models.Model):
    _inherit = 'mail.channel'

    @api.model
    def init_odoobot(self):
        """ Overridden to change the message containing 'Odoo' with the debrand_config settings name. """
        if self.env.user.odoobot_state in [False, 'not_initialized']:
            odoobot_id = self.env['ir.model.data'].xmlid_to_res_id("base.partner_root")
            channel_info = self.channel_get([odoobot_id])
            channel = self.browse(channel_info['id'])
            IrDefault = self.env['ir.default'].sudo()
            odoo_text_replacement = IrDefault.get('res.config.settings', "odoo_text_replacement")
            message = _("Hello,<br/>%s's chat helps employees collaborate efficiently. I'm here to help you discover "
                        "its features.<br/><b>Try to send me an emoji</b> <span "
                        "class=\"o_odoobot_command\">:)</span>") % (odoo_text_replacement,)
            channel.sudo().message_post(body=message, author_id=odoobot_id, message_type="comment", subtype_xmlid="mail.mt_comment")
            self.env.user.odoobot_state = 'onboarding_emoji'
            return channel

    @api.model
    def _replace_odoo_label(self):
        """ Already the OdooBot User replaced with System, then we just need to replace the name with Chnnel Partners. """
        mail_channel_objs = self.env['mail.channel'].sudo().search(['|',('name','ilike','odoo'),('name','ilike','Odoo')])
        for mail_channel in mail_channel_objs:
            partner_names = [channel_partner.partner_id.name for channel_partner in mail_channel.channel_last_seen_partner_ids]
            mail_channel.write({'name': ', '.join(partner_names)})


    def _channel_channel_notifications(self, partner_ids):
        """ Overidden to put sudo() while fetching user_ids
        """
        notifications = []
        for partner in self.env['res.partner'].browse(partner_ids):
            user_id = partner.sudo().user_ids and partner.sudo().user_ids[0] or False #TODO metro
            if user_id:
                user_channels = self.with_user(user_id).with_context(
                    allowed_company_ids=user_id.company_ids.ids
                )
                for channel_info in user_channels.channel_info():
                    notifications.append([(self._cr.dbname, 'res.partner', partner.id), channel_info])
        return notifications