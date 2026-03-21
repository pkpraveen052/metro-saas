from odoo import models,fields,api,_

class CalendarEvent(models.Model):
    _inherit="calendar.event"

    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id,ondelete="cascade")

    

class CalendarEventType(models.Model):
    _inherit="calendar.event.type"

    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id)
    
    