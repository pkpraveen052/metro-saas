from odoo import api, models, fields, _
import datetime
from datetime import datetime


def _get_year(self):
    lst = []
    year = datetime.now().year
    for ya in range(year - 5, year + 1):
        lst.append((str(ya), str(ya)))
    return lst

class HPOtherPPE(models.Model):
    _name = "hp.other.ppe"
    _description = "HP Other PPE"

    form_cs_id = fields.Many2one('form.cs')
    descriptionEachAsset = fields.Char(string="Description")
    yaOfPurchaseEachAsset = fields.Selection(_get_year,string="YA of Purchase")
    costEachAsset = fields.Float(string="Cost (S$)")
    salesProceedEachAsset = fields.Float(string="Sales Proceed (S$)")
    yaOfDisposalEachAsset = fields.Selection(_get_year,string="YA of Disposal")
    taxWrittenDownValueBFEachAsset = fields.Float(string="Tax Written Down Value b/f (S$)", readonly=True)
    depositOrPrincipalExcluding = fields.Float(string="Deposit/ Principal Paid in  Current YA (Excluding Interest, Including Downpayment) (S$)")
    depositOrPrincipalMinus1 = fields.Float(string="Deposit/ Principal Paid in  YA-1 (Excluding Interest, Including Downpayment) (S$)")
    depositOrPrincipalMinus2 = fields.Float(string="Deposit/ Principal Paid in YA-2 (Excluding Interest, Including Downpayment) (S$)")
    annualAllowanceEachAsset = fields.Float(string="Annual Allowance-AA (S$)", readonly=True)
    balancingAllowanceEachAssetDisposedOfOrWrittenOff = fields.Float(string="Balancing Allowance (BA) (Disposed Of/ Written Off)  (S$)", readonly=True)
    balancingChargeEachAssetDisposedOfOrWrittenOff = fields.Float(string="Balancing Charge (BC) (Disposed Of/ Written Off)  (S$)", readonly=True)
    taxWrittenDownValueCFEachAsset = fields.Float(string="Tax Written Down Value c/f (S$)", readonly=True)
    totalPrincipalTillDateEachAsset = fields.Float(string="Total Principal Paid Till Date (S$)")

    @api.constrains('costEachAsset', 'salesProceedEachAsset','taxWrittenDownValueBFEachAsset','depositOrPrincipalExcluding',
                    'depositOrPrincipalMinus1','depositOrPrincipalMinus2','balancingAllowanceEachAssetDisposedOfOrWrittenOff',
                    'balancingChargeEachAssetDisposedOfOrWrittenOff','taxWrittenDownValueCFEachAsset','totalPrincipalTillDateEachAsset')
    def constrain_fields(self):
        for obj in self:
            if obj.costEachAsset < 0 or obj.salesProceedEachAsset < 0 or obj.taxWrittenDownValueBFEachAsset < 0 or obj.depositOrPrincipalExcluding < 0 or\
                    obj.depositOrPrincipalMinus1 < 0 or obj.depositOrPrincipalMinus2 < 0 or obj.balancingAllowanceEachAssetDisposedOfOrWrittenOff < 0 or\
                    obj.balancingChargeEachAssetDisposedOfOrWrittenOff < 0 or obj.taxWrittenDownValueCFEachAsset < 0 or obj.totalPrincipalTillDateEachAsset < 0:
                raise ValidationError(_("Assets cannot accept negative values."))

class NonHPCompCommEquipment(models.Model):
    _name = "non.hp.compcommequipment"
    _description = "Non HP Comp Comm Equipment"

    form_cs_id = fields.Many2one('form.cs')
    descriptionEachAsset = fields.Char(string="Description")
    yaOfPurchaseEachAsset = fields.Selection(_get_year, string="YA of Purchase")
    noOfYearsOfWorkingLifeBFEachAsset = fields.Float(string="No. of Years of Working Life b/f", readonly=True)
    costEachAsset = fields.Float(string="Cost (S$)")
    salesProceedEachAsset = fields.Float(string="Sales Proceed (S$)")
    yaOfDisposalEachAsset = fields.Selection(_get_year, string="YA of Disposal")
    taxWrittenDownValueBFEachAsset = fields.Float(string="Tax Written Down Value brought forward (S$)", readonly=True)
    annualAllowanceEachAsset = fields.Float(string="Annual Allowance-AA (S$)", readonly=True)
    balancingAllowanceEachAssetDisposedOfOrWrittenOff = fields.Float(string="Balancing Allowance (BA) (Disposed Of/ Written Off)  (S$)", readonly=True)
    balancingChargeEachAssetDisposedOfOrWrittenOff = fields.Float(string="Balancing Charge (BC) (Disposed Of/ Written Off)  (S$)", readonly=True)
    taxWrittenDownValueCFEachAsset = fields.Float(string="Tax Written Down Value c/f (S$)", readonly=True)

    @api.constrains('costEachAsset', 'salesProceedEachAsset', 'noOfYearsOfWorkingLifeBFEachAsset',
                    'taxWrittenDownValueBFEachAsset','annualAllowanceEachAsset','balancingAllowanceEachAssetDisposedOfOrWrittenOff',
                    'balancingChargeEachAssetDisposedOfOrWrittenOff', 'taxWrittenDownValueCFEachAsset')
    def constrain_fields(self):
        for obj in self:
            if obj.costEachAsset < 0 or obj.salesProceedEachAsset < 0 or obj.noOfYearsOfWorkingLifeBFEachAsset < 0 or obj.taxWrittenDownValueBFEachAsset < 0 or \
                    obj.annualAllowanceEachAsset < 0 or obj.balancingAllowanceEachAssetDisposedOfOrWrittenOff < 0 or \
                    obj.balancingChargeEachAssetDisposedOfOrWrittenOff < 0 or obj.taxWrittenDownValueCFEachAsset < 0:
                raise ValidationError(_("Assets cannot accept negative values."))

class NonHpOtherPPE(models.Model):
    _name = "non.hp.other.ppe"
    _description = "Non HP Other PPE"

    form_cs_id = fields.Many2one('form.cs')
    descriptionEachAsset = fields.Char(string="Description")
    yaOfPurchaseEachAsset = fields.Selection(_get_year, string="YA of Purchase")
    noOfYearsOfWorkingLifeBFEachAsset = fields.Float(string="No. of Years of Working Life b/f", readonly=True)
    costEachAsset = fields.Float(string="Cost (S$)")
    salesProceedEachAsset = fields.Float(string="Sales Proceed (S$)")
    yaOfDisposalEachAsset = fields.Selection(_get_year, string="YA of Disposal")
    taxWrittenDownValueBFEachAsset = fields.Float(string="Tax Written Down Value b/f  (S$)", readonly=True)
    annualAllowanceEachAsset = fields.Float(string="Annual Allowance-AA (S$)", readonly=True)
    balancingAllowanceEachAssetDisposedOfOrWrittenOff = fields.Float(string="Balancing Allowance (BA) (Disposed Of/ Written Off)  (S$)", readonly=True)
    balancingChargeEachAssetDisposedOfOrWrittenOff = fields.Float(string="Balancing Charge (BC) (Disposed Of/ Written Off)  (S$)", readonly=True)
    taxWrittenDownValueCFEachAsset = fields.Float(string="Tax Written Down Value c/f (S$)", readonly=True)

    @api.constrains('costEachAsset', 'salesProceedEachAsset', 'noOfYearsOfWorkingLifeBFEachAsset',
                    'taxWrittenDownValueBFEachAsset', 'annualAllowanceEachAsset',
                    'balancingAllowanceEachAssetDisposedOfOrWrittenOff',
                    'balancingChargeEachAssetDisposedOfOrWrittenOff', 'taxWrittenDownValueCFEachAsset')
    def constrain_fields(self):
        for obj in self:
            if obj.costEachAsset < 0 or obj.salesProceedEachAsset < 0 or obj.noOfYearsOfWorkingLifeBFEachAsset < 0 or obj.taxWrittenDownValueBFEachAsset < 0 or \
                    obj.annualAllowanceEachAsset < 0 or obj.balancingAllowanceEachAssetDisposedOfOrWrittenOff < 0 or \
                    obj.balancingChargeEachAssetDisposedOfOrWrittenOff < 0 or obj.taxWrittenDownValueCFEachAsset < 0:
                raise ValidationError(_("Assets cannot accept negative values."))

class NonHpOtherPPELowValueAsset(models.Model):
    _name = "non.hp.other.ppe.lowvalueasset"
    _description = "Non HP Other PPE LowValueAsset"

    form_cs_id = fields.Many2one('form.cs')
    descriptionEachAsset = fields.Char(string="Description")
    yaOfPurchaseEachAsset = fields.Selection(_get_year, string="YA of Purchase")
    noOfYearsOfWorkingLifeBFEachAsset = fields.Float(string="No. of Years of Working Life b/f  (S$)", readonly=True)
    costEachAsset = fields.Float(string="Cost (S$)")
    salesProceedEachAsset = fields.Float(string="Sales Proceed (S$)")
    yaOfDisposalEachAsset = fields.Selection(_get_year, string="YA of Disposal")
    taxWrittenDownValueBFEachAsset = fields.Float(string="Tax Written Down Value b/f (S$)", readonly=True)
    annualAllowanceEachAsset = fields.Float(string="Annual Allowance-AA (S$)", readonly=True)
    balancingAllowanceEachAssetDisposedOfOrWrittenOff = fields.Float(string="Balancing Allowance (BA) (Disposed Of/ Written Off) (S$)", readonly=True)
    balancingChargeEachAssetDisposedOfOrWrittenOff = fields.Float(string="Balancing Charge (BC) (Disposed Of/ Written Off) (S$)", readonly=True)
    taxWrittenDownValueCFEachAsset = fields.Float(string="Tax Written Down Value c/f (S$)",readonly=True)