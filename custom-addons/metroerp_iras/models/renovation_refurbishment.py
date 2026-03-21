from odoo import models,fields,api,_
from odoo.exceptions import ValidationError
from datetime import datetime

def _get_year(self):
    lst = []
    year = datetime.now().year
    for ya in range(year - 5, year + 1):
        lst.append((str(ya), str(ya)))
    return lst

class RenovationRefurbishmentSchedule(models.Model):
    _name = "renovation.refurbishment.schedule"
    _description = "Renovation Refurbishment Schedule"

    form_cs_id = fields.Many2one('form.cs')
    ya = fields.Selection(_get_year, string="Year of Assessment (YA)")
    leaseholdImprovementsAndRenoCostIncurred = fields.Float(string="Leasehold Improvements And Renovation Cost Incurred ($)")
    tech_name = fields.Char('Tech Name')

    @api.constrains('qualifyingRAndRCosts', 's14QDeduction')
    def constrain_fields(self):
        if self.qualifyingRAndRCosts < 0 or self.s14QDeduction < 0:
            raise ValidationError(_("Assets cannot accept negative values."))
        

class RenovationRefurbishmentScheduleResponse(models.Model):
    _name = "renovation.refurbishment.schedule.response"
    _description = "Renovation Refurbishment Schedule Response"

    form_cs_response_id = fields.Many2one('form.cs')
    ya = fields.Selection(_get_year, string="Year of Assessment (YA)")
    leaseholdImprovementsAndRenoCostIncurred = fields.Float(string="Leasehold Improvements And Renovation Cost Incurred ($)")
    qualifyingRAndRCosts = fields.Float(string="Qualifying R&R Cost ($)", readonly=True)
    s14QDeduction = fields.Float(string="Section 14N Deduction ($)", readonly=True)
    