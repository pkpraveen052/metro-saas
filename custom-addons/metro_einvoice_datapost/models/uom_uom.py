from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError


class UomUom(models.Model):
    _inherit = "uom.uom"

    @api.constrains('unece_code')
    def _check_unece_code(self):
        """
        check valid uom code
        """
        for record in self:
            if record.unece_code:
                uom_code = self.env['uom.code'].search([
                    ('name', '=', record.unece_code)
                ])
                if not uom_code:
                    raise ValidationError(
                        "The UNECE Code '%s' is not a valid code. "
                        "Please choose a code from the UOM Codes list."
                        % record.unece_code
                    )
