from odoo import models,fields,api

class IrasDefaultAccountsMapping(models.Model):
    _name = "iras.default.accounts.mapping"
    _description = "Iras Default Accounts Mapping"
    
    name = fields.Char(string="Name",required=True)
    active = fields.Boolean(string="Active",default=True)
    line_ids = fields.One2many(
        "iras.default.accounts.mapping.lines",
        "iras_default_mapping_id",
        string="Mapping Lines",
    )

    @api.model
    def default_get(self, fields):
        res = super(IrasDefaultAccountsMapping, self).default_get(fields)
        account_templates = self.env["account.account.template"].search([])
        
        default_lines = [
            (0, 0, {"account_template_id": account.id}) for account in account_templates
        ]
        if "line_ids" in fields:
            res["line_ids"] = default_lines

        return res
    

class IrasDefaultAccountsMappingLines(models.Model):
    _name = "iras.default.accounts.mapping.lines"

    account_template_id = fields.Many2one("account.account.template",string="Account")
    iras_field_id = fields.Many2one("iras.coa.mapping",string="IRAS")
    iras_default_mapping_id = fields.Many2one("iras.default.accounts.mapping")

    