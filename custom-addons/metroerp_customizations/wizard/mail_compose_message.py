# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from pickle import FALSE

from odoo import models, api, fields, tools, _
import base64


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company)
    

    def save_as_template(self):
        """ Save as new template and set active company_id """
        for record in self:
            model = self.env['ir.model']._get(record.model or 'mail.message')
            model_name = model.name or ''
            template_name = "%s: %s" % (model_name, tools.ustr(record.subject))

            values = {
                'name': template_name,
                'subject': record.subject or False,
                'body_html': record.body or False,
                'model_id': model.id or False,
                'use_default_to': True,
                'company_id': self.env.company.id,  # Set current active company
            }

            template = self.env['mail.template'].create(values)

            if record.attachment_ids:
                attachments = self.env['ir.attachment'].sudo().browse(record.attachment_ids.ids).filtered(
                    lambda a: a.res_model == 'mail.compose.message' and a.create_uid.id == self._uid)
                if attachments:
                    attachments.write({'res_model': template._name, 'res_id': template.id})
                template.attachment_ids |= record.attachment_ids

            record.write({'template_id': template.id})
            record.onchange_template_id_wrapper()
            return self._reopen(record.id, record.model, context=self._context)

    def _reopen(self, res_id, model, context=None):
        """Helper method to reopen the wizard with context"""
        context = dict(context or {}, default_model=model)
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': res_id,
            'res_model': self._name,
            'target': 'new',
            'context': context,
        }

    @api.model
    def default_get(self, fields):
        """
        default mass mail payment template on compose model
        """
        result = super(MailComposeMessage, self).default_get(fields)
        if result.get('composition_mode') == 'mass_mail' and self._context.get('active_model') == 'account.payment':
            template = self.env.ref('metroerp_customizations.mass_mail_template_data_payment_receipt', raise_if_not_found=False)
            result.update({'template_id': template.id})
        return result

    def get_mail_values(self, res_ids):
        """ override this method to set partner bulk email header and footer added """
        self.ensure_one()
        results = dict.fromkeys(res_ids, False)
        rendered_values = {}
        mass_mail_mode = self.composition_mode == 'mass_mail'

        # render all template-based value at once
        if mass_mail_mode and self.model:
            rendered_values = self.render_message(res_ids)
        # compute alias-based reply-to in batch
        reply_to_value = dict.fromkeys(res_ids, None)
        if mass_mail_mode and not self.no_auto_thread:
            records = self.env[self.model].browse(res_ids)
            reply_to_value = records._notify_get_reply_to(default=False)
            # when having no specific reply-to, fetch rendered email_from value
            for res_id, reply_to in reply_to_value.items():
                if not reply_to:
                    reply_to_value[res_id] = rendered_values.get(res_id, {}).get('email_from', False)

        blacklisted_rec_ids = set()
        if mass_mail_mode and isinstance(self.env[self.model], self.pool['mail.thread.blacklist']):
            self.env['mail.blacklist'].flush(['email'])
            self._cr.execute("SELECT email FROM mail_blacklist WHERE active=true")
            blacklist = {x[0] for x in self._cr.fetchall()}
            if blacklist:
                targets = self.env[self.model].browse(res_ids).read(['email_normalized'])
                # First extract email from recipient before comparing with blacklist
                blacklisted_rec_ids.update(target['id'] for target in targets
                                           if target['email_normalized'] in blacklist)

        for res_id in res_ids:
            # static wizard (mail.message) values
            mail_values = {
                'subject': self.subject,
                'body': self.body or '',
                'parent_id': self.parent_id and self.parent_id.id,
                'partner_ids': [partner.id for partner in self.partner_ids],
                'attachment_ids': [attach.id for attach in self.attachment_ids],
                'author_id': self.author_id.id,
                'email_from': self.email_from,
                'record_name': self.record_name,
                'no_auto_thread': self.no_auto_thread,
                'mail_server_id': self.mail_server_id.id,
                'mail_activity_type_id': self.mail_activity_type_id.id,
            }

            # mass mailing: rendering override wizard static values
            if mass_mail_mode and self.model:
                record = self.env[self.model].browse(res_id)
                mail_values['headers'] = record._notify_email_headers()
                # keep a copy unless specifically requested, reset record name (avoid browsing records)
                mail_values.update(notification=not self.auto_delete_message, model=self.model, res_id=res_id, record_name=False)
                # auto deletion of mail_mail
                if self.auto_delete or self.template_id.auto_delete:
                    mail_values['auto_delete'] = True
                # rendered values using template
                email_dict = rendered_values[res_id]
                mail_values['partner_ids'] += email_dict.pop('partner_ids', [])
                mail_values.update(email_dict)
                if not self.no_auto_thread:
                    mail_values.pop('reply_to')
                    if reply_to_value.get(res_id):
                        mail_values['reply_to'] = reply_to_value[res_id]
                if self.no_auto_thread and not mail_values.get('reply_to'):
                    mail_values['reply_to'] = mail_values['email_from']
                # mail_mail values: body -> body_html, partner_ids -> recipient_ids
                partner_id = self.env['res.partner'].browse(res_id)
                if self._context.get('active_model') == 'res.partner':
                    mail_values['body_html'] = self.generate_mail_body_html(partner_id.company_id, mail_values.get('body', ''))
                else:
                    mail_values['body_html'] = mail_values.get('body', '')
                mail_values['recipient_ids'] = [(4, id) for id in mail_values.pop('partner_ids', [])]

                # process attachments: should not be encoded before being processed by message_post / mail_mail create
                mail_values['attachments'] = [(name, base64.b64decode(enc_cont)) for name, enc_cont in email_dict.pop('attachments', list())]
                attachment_ids = []
                for attach_id in mail_values.pop('attachment_ids'):
                    new_attach_id = self.env['ir.attachment'].browse(attach_id).copy({'res_model': self._name, 'res_id': self.id})
                    attachment_ids.append(new_attach_id.id)
                attachment_ids.reverse()
                mail_values['attachment_ids'] = self.env['mail.thread'].with_context(attached_to=record)._message_post_process_attachments(
                    mail_values.pop('attachments', []),
                    attachment_ids,
                    {'model': 'mail.message', 'res_id': 0}
                )['attachment_ids']
                # Filter out the blacklisted records by setting the mail state to cancel -> Used for Mass Mailing stats
                if res_id in blacklisted_rec_ids:
                    mail_values['state'] = 'cancel'
                    # Do not post the mail into the recipient's chatter
                    mail_values['notification'] = False

            results[res_id] = mail_values
        return results

    def generate_mail_body_html(self, company, mail_body):
        """
        This method return body part of contact bulk mail
        """
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        logo_url = f"{base_url}/logo.png?company={company.id}"
        company_phone = f"{company.phone}" if company.phone else ""
        company_email = (
            f' | <a href="mailto:{company.email}" style="text-decoration:none; color: #454748;">{company.email}</a>'
            if company.email else ""
        )
        company_website = (
            f' | <a href="{company.website}" style="text-decoration:none; color: #454748;">{company.website}</a>'
            if company.website else ""
        )
        return f"""
        <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
                <tr>
                    <td align="center">
                        <table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
                            <tbody>
                                <tr>
                                    <td align="center" style="min-width: 590px;">
                                        <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                                            <tr>
                                                <td valign="middle">
                                                    <span style="font-size: 20px;">{company.name}</span><br/>
                                                </td>
                                                <td valign="middle" align="right">
                                                    <img src="{logo_url}" style="padding: 0px; margin: 0px; height: 48px; width: 48px;" alt="{company.name}"/>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td colspan="2" style="text-align:center;">
                                                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 5px 0px 16px 0px;"/>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="min-width:590px;">
                                        <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width:590px;background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                                            <tbody><tr><td valign="top" style="font-size:13px;">
                                                <div>
                                                    {mail_body}
                                                </div>
                                            </td></tr>
                                        </tbody></table>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="min-width: 590px; padding: 0 8px 0 8px; font-size:11px;">
                                        <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 4px 0px;"/>
                                        <b style="background-color: white;">{company.name}</b><br/>
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
                            <p>Powered by
                            <a target="_blank"
                            href="https://www.metrogroup.solutions/solutions/accounting-system"
                            style="color: #875A7B;">Metro Accounting System</a>
                            </p>
                          </td></tr>
                        </table>
                    </td>
                </tr>
            </table>
        """