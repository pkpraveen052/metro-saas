from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountMapping(models.Model):

    _name = 'account.mapping'
    _rec_name = "company_id"
    _description = "Carbonate Account Mapping"

    credit_account = fields.Many2one('account.account', 'Default Credit Account(Salary)', required=True)
    debit_account = fields.Many2one('account.account', 'Default Debit Account(Salary)', required=True)
    active = fields.Boolean('Active', default=True)
    # c_account_name = fields.Char("Name")
    # c_account_code = fields.Char("Code", required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    need_separate_cpf = fields.Boolean('Need Separate CPF')
    cpf_lines = fields.One2many('account.mapping.cpf.lines', 'parent_id', string='CPF Lines')

    @api.constrains('cpf_lines', 'need_separate_cpf')
    def check_cpf_lines(self):
        for obj in self:
            if obj.need_separate_cpf and not obj.cpf_lines:
                raise ValidationError(_("Please provide the CPF details."))

    _sql_constraints = [
        ('code_uniq', 'unique (c_account_code,company_id)', 'Carbonate Code already exists!'),
    ]

class AccountMappingCPFLines(models.Model):
    _name = 'account.mapping.cpf.lines'
    _description = 'Account Mapping CPF Lines'

    code = fields.Char('Code', required=True)
    name = fields.Char('Name')
    credit_account = fields.Many2one('account.account', 'Credit Account', required=True)
    debit_account = fields.Many2one('account.account', 'Debit Account', required=True)
    parent_id = fields.Many2one('account.mapping')

