from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import urllib.parse as urllib
import re

class PortalShareWhatsapp(models.TransientModel):
    _name = 'portal.share.whatsapp'

    @api.model
    def default_get(self, fields):
        result = super(PortalShareWhatsapp, self).default_get(fields)
        if self._context.get('active_id', False):
            record = self.env['sale.order'].browse(self._context.get('active_id', False))
            result['share_link'] = record.get_base_url() + record._get_share_url(redirect=True)
        return result

    def get_id(self):
        rec = self.env['sale.order'].browse(self.env.context.get('active_id'))
        return rec.partner_id

    partner_id = fields.Many2one('res.partner', string="Recipient", required=True, default=get_id)
    share_link = fields.Char(string="Link")
    note = fields.Text(help="Add extra content to display in the email")

    def action_send_whatsapps(self):

        if not self.partner_id.mobile and not self.partner_id.phone:
            raise ValidationError("Please Add Mobile or Phone Number!")

        phone, mobile = '', ''
        if self.partner_id.mobile:
            mobile = "".join(self.partner_id.mobile.split())
            mobile = re.sub(r'[^a-zA-Z0-9]', '', mobile)
        elif self.partner_id.phone:
            phone = "".join(self.partner_id.phone.split())
            phone = re.sub(r'[^a-zA-Z0-9]', '', phone)

        def validate_string(input_string):
            # Define the regular expression pattern
            pattern = r'^\d{8}$|^\d{10}$'

            # Check if the input string matches the pattern
            if re.match(pattern, input_string):
                # If the string is 8 characters, append '65' at its prefix
                if len(input_string) == 8:
                    input_string = '65' + input_string
                return input_string
            else:
                return None

        if mobile:
            mobile = validate_string(mobile)
            if not mobile:
                raise ValidationError("Please add valid mobile!")

        elif phone:
            phone = validate_string(phone)
            if not phone:
                raise ValidationError("Please add valid mobile!")

        common_message = 'Please access your documents using below link'
        message_string = _('Dear') + ' ' + self.partner_id.name + ',' + '%0a''%0a' + common_message + '%0a' + 'Link : ' + urllib.quote(self.share_link)
        if self.note:
            message_string += '%0a''%0a' + 'Note : ' + self.note
        if mobile:
            link = "https://web.whatsapp.com/send?phone=" + mobile
        else:
            link = "https://web.whatsapp.com/send?phone=" + phone
        return {
            'type': 'ir.actions.act_url',
            'url': link + "&text=" + message_string,
            'target': 'new',
            'res_id': self.id,
        }