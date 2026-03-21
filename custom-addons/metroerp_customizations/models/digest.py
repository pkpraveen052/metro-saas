from odoo import models, fields, api


class DigestInherited(models.Model):
	_inherit = "digest.digest"

	state = fields.Selection([('activated', 'Activated'), ('deactivated', 'Deactivated')], string='Status', readonly=True, default='deactivated')