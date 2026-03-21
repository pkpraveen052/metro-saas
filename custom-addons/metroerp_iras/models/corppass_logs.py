from odoo import api, models, fields, _


class CorppassLogs(models.Model):
    _name = "corppass.logs"
    _description = "Corppass Logs"
    _order = "create_date desc"

    content = fields.Text('Content')