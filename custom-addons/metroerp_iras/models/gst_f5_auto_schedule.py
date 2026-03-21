from odoo import models,fields,api,_
from datetime import datetime,date
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class GSTF5AutoSchedule(models.Model):
    _name = "gst.f5.auto.schedule"
    _description = "GSTF5 AutoSchedule"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', default='Reminder Schedule')
    line_ids = fields.One2many("gst.f5.auto.schedule.lines","gst_f5_auto_schedule_id",string="Lines", required=True)
    group_ids = fields.Many2many("res.groups",string="Notification")
    active = fields.Boolean(default=True)
    filing_reminder_id = fields.Many2one("mail.template",string="Filling Date Mail Template")
    due_date_reminder_id = fields.Many2one("mail.template",string="Due Date Mail Template")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, readonly=True, tracking=True)

    @api.model
    def _cron_gst_f5_reminder(self):
        today = fields.Date.today()
        auto_schedule_o = self.env['gst.f5.auto.schedule'].search([], limit=1)
        start_template = auto_schedule_o.filing_reminder_id
        due_template = auto_schedule_o.due_date_reminder_id
        web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for line in auto_schedule_o.line_ids:
            if line.filing_date == today:
                objs = self.env['gst.returns.f5f8'].search([('formType','=','F5'),('dtPeriodStart','=',str(line.quarter_start_date)),('dtPeriodEnd','=',str(line.quarter_end_date))])
                if not objs:
                    obj = self.env['gst.returns.f5f8'].create({
                        'formType': 'F5',
                        'dtPeriodStart': line.quarter_start_date,
                        'dtPeriodEnd': line.quarter_end_date,
                        })
                    url = web_base_url + "/web#id="+str(obj.id)+"&action=" + str(self.env.ref('metroerp_iras.gst_returns_f5f8_action').id) + "&model=gst.returns.f5f8&view_type=form"
                    for group in auto_schedule_o.group_ids:
                        for user in group.users:
                            start_template.with_context({'partner_id': user.partner_id.id, 'obj': obj, 'url':url}).send_mail(auto_schedule_o.id, force_send=True)
                
            due_date = line.due_date - relativedelta(days=line.due_date_notification_days)
            if today >= due_date <= today:
                obj = self.env['gst.returns.f5f8'].search([('formType','=','F5'),('dtPeriodStart','=',str(line.quarter_start_date)),('dtPeriodEnd','=',str(line.quarter_end_date)),('company_id', '=', auto_schedule_o.company_id.id)])
                if obj:
                    url = web_base_url + "/web#id=" + str(obj.id) + "&action=" + str(self.env.ref('metroerp_iras.gst_returns_f5f8_action').id) + "&model=gst.returns.f5f8&view_type=form"
                else:
                    url = False
                for group in auto_schedule_o.group_ids:
                    for user in group.users:
                        due_template.with_context({'partner_id': user.partner_id.id, 'start_date': str(line.quarter_start_date), 'end_date': str(line.quarter_end_date), 'obj': obj, 'url': url}).send_mail(auto_schedule_o.id, force_send=True)
        
class GSTF5AutoScheduleLines(models.Model):
    _name = "gst.f5.auto.schedule.lines"
    _description = "GSTF5 AutoSchedule Lines"

    gst_f5_auto_schedule_id = fields.Many2one("gst.f5.auto.schedule")
    quarter_name = fields.Char(string="Name", required=True)
    quarter_start_date = fields.Date(string="Quarter Start")
    quarter_end_date = fields.Date(string="Quarter End")
    filing_date = fields.Date(string="Filing Date")
    due_date = fields.Date(string="Due Date")
    due_date_notification_days = fields.Integer('Days Prior from Due Date', default=7)

    @api.onchange('quarter_start_date')
    def onchange_quarter_start_date(self):
        if self.quarter_start_date:
            self.filing_date = self.quarter_start_date

    @api.onchange('quarter_end_date')
    def onchange_quarter_end_date(self):
        if self.quarter_end_date:
            self.due_date = self.quarter_end_date