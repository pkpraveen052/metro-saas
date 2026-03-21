from odoo import models, fields, api


class IrActionsActWindow(models.Model):
	_inherit = "ir.actions.act_window"

	@api.model
	def _replace_odoo_label(self):
		""" To replace the Odoo labels from the 'help' field with debranded name. """
		IrDefault = self.env['ir.default'].sudo()
		odoo_text_replacement = IrDefault.get('res.config.settings', "odoo_text_replacement") or 'ERP'
		action_objs = self.env['ir.actions.act_window'].sudo().search([('help','ilike','Odoo')])
		for action_obj in action_objs:
			action_obj.write({'help': str(action_obj.help).replace('Odoo', odoo_text_replacement)})