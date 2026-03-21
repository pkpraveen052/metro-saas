from odoo import models, fields, api


class MailMessage(models.Model):
	_inherit = "mail.message"

	@api.model
	def _replace_odoo_label(self):
		""" To replace the Odoo/odoo labels from the 'email_from' and 'body' fields with debranded name. """
		IrDefault = self.env['ir.default'].sudo()
		odoo_text_replacement = IrDefault.get('res.config.settings', "odoo_text_replacement") or 'ERP'
		message_objs = self.env['mail.message'].sudo().search([('email_from','ilike','OdooBot')])
		for message_obj in message_objs:
			message_obj.write({'email_from': str(message_obj.email_from).replace('OdooBot', 'System')})
		message_objs = self.env['mail.message'].sudo().search([('email_from','ilike','odoobot')])
		for message_obj in message_objs:
			message_obj.write({'email_from': str(message_obj.email_from).replace('odoobot', 'system')})
		message_objs = self.env['mail.message'].sudo().search([('email_from','ilike','Odoo')])
		for message_obj in message_objs:
			message_obj.write({'email_from': str(message_obj.email_from).replace('Odoo', odoo_text_replacement)})


		message_objs = self.env['mail.message'].sudo().search([('body','ilike','OdooBot')])
		for message_obj in message_objs:
			message_obj.write({'body': str(message_obj.body).replace('OdooBot', 'System')})
		message_objs = self.env['mail.message'].sudo().search([('body','ilike','Odoo')])
		for message_obj in message_objs:
			message_obj.write({'body': str(message_obj.body).replace('Odoo', odoo_text_replacement)})


		message_objs = self.env['mail.message'].sudo().search([('record_name','ilike','OdooBot')])
		for message_obj in message_objs:
			message_obj.write({'record_name': str(message_obj.record_name).replace('OdooBot', 'System')})
		message_objs = self.env['mail.message'].sudo().search([('record_name','ilike','Odoo')])
		for message_obj in message_objs:
			message_obj.write({'record_name': str(message_obj.record_name).replace('OdooBot', odoo_text_replacement)})


		message_objs = self.env['mail.message'].sudo().search([('reply_to','ilike','OdooBot')])
		for message_obj in message_objs:
			message_obj.write({'reply_to': str(message_obj.email_from).replace('OdooBot', 'System')})
		message_objs = self.env['mail.message'].sudo().search([('reply_to','ilike','odoobot')])
		for message_obj in message_objs:
			message_obj.write({'reply_to': str(message_obj.email_from).replace('odoobot', 'system')})
		message_objs = self.env['mail.message'].sudo().search([('reply_to','ilike','Odoo')])
		for message_obj in message_objs:
			message_obj.write({'reply_to': str(message_obj.email_from).replace('Odoo', odoo_text_replacement)})

		message_objs = self.env['mail.message'].sudo().search([('subject','ilike','Odoo')])
		for message_obj in message_objs:
			message_obj.write({'subject': str(message_obj.subject).replace('Odoo', odoo_text_replacement)})
