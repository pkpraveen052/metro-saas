
from odoo import models, api, fields

class WhatsappSendMessage(models.TransientModel):
    _name = 'whatsapp.message.wizard'
    _description = "Whatsapp Wizard"

    name = fields.Char(string="Recipient Name")
    mobile = fields.Char(string="Mobile", required=True)
    message = fields.Text(string="Message", required=True)

    @api.model
    def default_get(self, fields):
        res = super(WhatsappSendMessage, self).default_get(fields)
        visitor_id = self.env.context.get('active_id')  # Here get active visitor ID from visitor.details
        visitor = self.env['visitor.details'].browse(visitor_id)
        res.update({
            'name': visitor.name, 
            'mobile': visitor.phone,
        })
        return res

    def send_message(self):
        if self.message and self.mobile:
            message_string = ''
            message = self.message.split(' ')
            for msg in message:
                message_string += msg + '%20'  # URL-encode spaces
            message_string = message_string.rstrip('%20')  # Removed the last '%20'
            return {
                'type': 'ir.actions.act_url',
                'url': "https://api.whatsapp.com/send?phone=" + self.mobile + "&text=" + message_string,
                'target': 'new',
                'res_id': self.id,
            }
        
    
    

