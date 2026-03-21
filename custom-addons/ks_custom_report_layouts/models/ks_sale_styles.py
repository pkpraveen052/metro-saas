from odoo import fields, models, api, _


class KsSaleStyles(models.Model):
    _name = 'ks.sale.styles'
    _description = 'Sale Report Styles'

    name = fields.Char('Styles')
    ks_images = fields.Binary(string="Images")

    


