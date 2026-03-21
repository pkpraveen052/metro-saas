from odoo import models,fields,api,_

class CapitalAllowanceResponse(models.Model):
    _name = "capital.allowance.response"
    _description = "Capital Allowance Response"

    form_cs_id1 = fields.Many2one("form.cs")
    form_cs_id2 = fields.Many2one("form.cs")
    form_cs_id3 = fields.Many2one("form.cs")
    form_cs_id4 = fields.Many2one("form.cs")
    form_cs_id5 = fields.Many2one("form.cs")
    form_cs_id6 = fields.Many2one("form.cs")
    form_cs_id7 = fields.Many2one("form.cs")
    form_cs_id8 = fields.Many2one("form.cs")
    form_cs_id9 = fields.Many2one("form.cs")
    form_cs_id10 = fields.Many2one("form.cs")
    
    descriptionEachAsset = fields.Text(string="Description")
    yaOfPurchaseEachAsset = fields.Char(string="YA of Purchase")
    costEachAsset = fields.Float(string="Cost (S$)")
    noOfYearsOfWorkingLifeBFEachAsset = fields.Char(string="No. of Years of Working Life b/f")
    taxWrittenDownValueBFEachAsset = fields.Float(string="Tax written down value b/f (S$)")
    annualAllowanceEachAsset = fields.Float(string="Annual Allowance-AA (S$)")
    taxWrittenDownValueCFEachAsset = fields.Float(string="Tax Written Down Value c/f (S$)")
    salesProceedEachAsset = fields.Float(string="Sales Proceed (S$)")
    yaOfDisposalEachAsset = fields.Char(string="YA of Disposal")
    balancingChargeEachAssetDisposedOfOrWrittenOff = fields.Float(string="Balancing Charge (BC) (S$)")
    balancingAllowanceEachAssetDisposedOfOrWrittenOff = fields.Float(string="Balancing Allowance (BA) (S$)")
    deposit_OrPrincipal_ExcInterest_IncDownpay_EachAsset = fields.Float(string="Deposit/ Principal paid during the year (excluding interest, including downpayment) (S$)")


    def create(self, vals):
        print("\n\n\n\n ---- create",vals)
        res = super(CapitalAllowanceResponse, self).create(vals)
        return res
