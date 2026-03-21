from odoo import models, fields, api


class DigestTip(models.Model):
	_inherit = "digest.tip"

	@api.model
	def _replace_odoo_label(self):
		""" To replace the Odoo/odoo labels from the name or tip_description fields with debranded name. """
		IrDefault = self.env['ir.default'].sudo()
		odoo_text_replacement = IrDefault.get('res.config.settings', "odoo_text_replacement") or 'ERP'
		digest_objs = self.env['digest.tip'].sudo().search(['|',('name','ilike','odoo'),('name','ilike','Odoo')])
		for digest_obj in digest_objs:
			digest_obj.write({'name': str(digest_obj.name).replace('odoo', odoo_text_replacement)})
			digest_obj.write({'name': str(digest_obj.name).replace('Odoo', odoo_text_replacement)})
		digest_objs = self.env['digest.tip'].sudo().search(['|',('tip_description','ilike','odoo'),('tip_description','ilike','Odoo')])
		for digest_obj in digest_objs:
			digest_obj.write({'tip_description': str(digest_obj.tip_description).replace('odoo', odoo_text_replacement)})
			digest_obj.write({'tip_description': str(digest_obj.tip_description).replace('Odoo', odoo_text_replacement)})