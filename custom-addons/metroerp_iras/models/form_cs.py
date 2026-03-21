from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from dateutil import relativedelta
import json
import requests
import datetime
from datetime import datetime
import pytz
import random
import string
import math
import logging

logger = logging.getLogger(__name__)

class GFormCS(models.Model):
    _name = "form.cs"
    _description = "Form C-S"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'base.gst.accounts']
    _order = "create_date desc"
    _rec_name = "ya"

    @api.onchange('ya')
    def get_dates(self):
        if self.ya:
            ya = str(int(self.ya) - 1)
            fiscal_o = self.env['account.fiscal.year'].sudo().search([('company_id','=',self.company_id.id),('name','=',ya)])
            if fiscal_o:
                self.basisPeriodFrom = fiscal_o.date_from
                self.basisPeriodTo = fiscal_o.date_to
            # else:
            #     raise ValidationError("Please define the Fiscal Year for the selected Assessment Year.")
            # yr = str(int(self.ya) - 1)
            # self.basisPeriodFrom = datetime.now().date().replace(year=int(yr), month=1, day=1)
            # self.basisPeriodTo = datetime.now().date().replace(year=int(yr), month=12, day=31)

    @api.onchange('fsPrep')
    def get_first_fye(self):
        if self.fsPrep == '1':
            self.firstFYE = self.basisPeriodTo
        else:
            self.firstFYE = False
            
    @api.depends('basisPeriodTo','basisPeriodFrom')
    def _get_month_difference(self):
        for obj in self:
            r = relativedelta.relativedelta(obj.basisPeriodTo, obj.basisPeriodFrom)
            obj.months_difference = (r.years * 12) + (r.months + 1)

    def _get_year(self):
        lst = []
        year = datetime.now().year
        for ya in range(year - 4, year + 1):
            lst.append((str(ya), str(ya)))
        return lst

    @api.model
    def default_get(self, fields):
        res = super(GFormCS, self).default_get(fields)
        res.update({
            'uenType': self.env.company.uenType
        })
        contact = self.env.user.partner_id
        res.update({
            'designationOfFiler': contact.function,
            'designationOfContactPerson': contact.function,
            'contactNumber': contact.phone or contact.mobile
            })
        if self.env.user.partner_id.is_foreigner and self.env.user.partner_id.tax_ref_iras:
            res.update({
                'declarantRefNo': self.env.user.partner_id.tax_ref_iras
            })
        return res

    #TODO: For the new fields (YA 2024)
    @api.constrains('totalRevenue','c1_FurtherDed','unutilCABFNorm','unutilLossBFNorm','unutilDonationBFNorm','cyDonation',\
        'unutilCALDClaimS23S37','expRD','expRDSG','enhanceDeductRD','iaAaPriorSeamlessFiling','baPriorSeamlessFiling','bcPriorSeamlessFiling')
    def constrain_taxconversion_fields(self):
        if self.totalRevenue < 0 or self.DataFormCS_totalRevenue < 0:
            raise ValidationError(_("Negative value is not allowed to Total Revenue."))
        if self.c1_FurtherDed < 0 or self.DataFormCS_c1_FurtherDed < 0:
            raise ValidationError(_("Negative value is not allowed to Further Deductions/ Other Deductions."))
        if self.unutilCABFNorm < 0 or self.DataFormCS_unutilCABFNorm < 0:
            raise ValidationError(_("Negative value is not allowed to Unutilised Capital Allowances brought forward."))
        if self.unutilLossBFNorm < 0 or self.DataFormCS_unutilLossBFNorm < 0:
            raise ValidationError(_("Negative value is not allowed to Unutilised Losses brought forward."))
        if self.unutilDonationBFNorm < 0 or self.DataFormCS_unutilDonationBFNorm < 0:
            raise ValidationError(_("Negative value is not allowed to Unutilised Donations brought forward."))
        if self.cyDonation < 0 or self.DataFormCS_cyDonation < 0:
            raise ValidationError(_("Negative value is not allowed to Current Year Donations."))
        if self.unutilCALDClaimS23S37 < 0 or self.DataFormCS_unutilCALDClaimS23S37 < 0:
            raise ValidationError(_("Negative value is not allowed to Unutilised Capital Allowances/ Losses/ Donations Claimed where Waiver of the Shareholding Test Has Been Granted by IRAS."))
        if self.expRD < 0 or self.DataFormCS_expRD < 0:
            raise ValidationError(_("Negative value is not allowed to Deduction for Expenditure Incurred on R&D - Total Deduction under Section 14C."))
        if self.expRDSG < 0 or self.DataFormCS_expRDSG < 0:
            raise ValidationError(_("Negative value is not allowed to Section 14C Deduction for Expenditure Incurred on R&D Activities undertaken in Singapore."))
        if self.enhanceDeductRD < 0 or self.DataFormCS_enhanceDeductRD < 0:
            raise ValidationError(_("Negative value is not allowed to Staff Costs and Consumables for R&D Activities Undertaken in Singapore Qualifying for Section 14D(1)."))
        if self.iaAaPriorSeamlessFiling < 0:
            raise ValidationError(_("Negative value is not allowed to Initial or Annual Allowance (Assets acquired prior to Seamless Filing Solution)."))
        if self.baPriorSeamlessFiling < 0:
            raise ValidationError(_("Negative value is not allowed to Balancing Allowance (Assets acquired prior to Seamless Filing Solution)."))
        if self.bcPriorSeamlessFiling < 0:
            raise ValidationError(_("Negative value is not allowed to Balancing Charge (Assets acquired prior to Seamless Filing Solution)."))

    @api.constrains('basisPeriodTo')
    def constrain_basisPeriodTo(self):
        if self.basisPeriodTo <= self.basisPeriodFrom:
            raise UserError(_("The 'Period End Date' must be greater than the 'Period State Date'."))

    @api.constrains('basisPeriodFrom', 'basisPeriodTo', 'ya')
    def constrain_yearofAssessment(self):
        for record in self:
            if record.ya and record.basisPeriodFrom and record.basisPeriodTo:
                from_year = record.basisPeriodFrom.year
                to_year = record.basisPeriodTo.year
                if to_year != int(record.ya) - 1:
                    raise UserError(
            "For the UEN " + str(record.uen) + ", the Period End Date must be earlier than the corresponding Year of Assessment. Please verify and adjust the dates accordingly to ensure compliance with accounting standards.")

    @api.depends('ya', 'basisPeriodFrom', 'basisPeriodTo')
    def _get_display_ya(self):
        for obj in self:
            obj.display_ya = obj.ya
            obj.display_basisPeriodFrom = obj.basisPeriodFrom
            obj.display_basisPeriodTo = obj.basisPeriodTo

    @api.depends('sgIntDisc', 'oneTierTaxDividendIncome', 'c1_GrossRent', 'sgOtherI', 'otherNonTaxableIncome')
    def _compute_total_otherincome(self):
        for obj in self:
            obj.totalOtherIncome = obj.sgIntDisc + obj.oneTierTaxDividendIncome + obj.c1_GrossRent + obj.sgOtherI + obj.otherNonTaxableIncome

    @api.depends('bankCharges', 'commissionOther', 'depreciationExpense', 'directorsFees', 'directorsRemunerationExcludingDirectorsFees', 'donations', 'cpfContribution',
                'c1_EntertainExp', 'commissionExpRentalIncome', 'insuranceExpRentalIncome', 'interestExpRentalIncome', 'propertyTaxExpRentalIncome', 'repairMaintenanceExpRentalIncome',
                'otherExpRentalIncome', 'fixedAssetsExpdOff', 'amortisationExpense', 'insuranceExpOther', 'interestExpOther', 'impairmentLossReversalOfImpairmentLossForBadDebts', 'medicalExpIncludingMedicalInsurance',
                'netGainsOrLossesOnDisposalOfPPE', 'netGainsOrLossesOnForex', 'netGainsOrLossesOnOtherItems', 'miscExp', 'otherPrivateOrCapitalExp', 'otherFinanceCost',
                'penaltiesOrFine', 'professionalFees', 'propertyTaxOther', 'rentExp', 'repairMaintenanceExcludingUpkeepOfPrivateVehiclesAndExp', 'repairsMaintenanceForPrivateVehicles', 
                'salesAndMarketingExpense', 'skillsDevelopmentForeignWorkerLevy', 'staffRemunerationOtherThanDirectorsRemuneration', 'staffWelfare', 'telecommunicationOrUtilities', 'training',
                'c1_TransportExp', 'upkeepNonPrivateVehicles', 'upkeepPrivateVehicles')
    def _compute_totalExpenses(self):
        for obj in self:
            obj.totalExpenses = obj.bankCharges + obj.commissionOther + obj.depreciationExpense + obj.directorsFees + obj.directorsRemunerationExcludingDirectorsFees + \
                obj.donations + obj.cpfContribution + obj.c1_EntertainExp + obj.commissionExpRentalIncome + obj.insuranceExpRentalIncome + \
                obj.interestExpRentalIncome + obj.propertyTaxExpRentalIncome + obj.repairMaintenanceExpRentalIncome + obj.otherExpRentalIncome + obj.fixedAssetsExpdOff + \
                obj.amortisationExpense + obj.insuranceExpOther + obj.interestExpOther + obj.impairmentLossReversalOfImpairmentLossForBadDebts + obj.medicalExpIncludingMedicalInsurance + \
                obj.netGainsOrLossesOnDisposalOfPPE + obj.netGainsOrLossesOnForex + obj.netGainsOrLossesOnOtherItems + obj.miscExp + obj.otherPrivateOrCapitalExp + \
                obj.otherFinanceCost + obj.penaltiesOrFine + obj.professionalFees + obj.propertyTaxOther + obj.rentExp + \
                obj.repairMaintenanceExcludingUpkeepOfPrivateVehiclesAndExp + obj.repairsMaintenanceForPrivateVehicles + obj.salesAndMarketingExpense + obj.skillsDevelopmentForeignWorkerLevy + obj.staffRemunerationOtherThanDirectorsRemuneration + \
                obj.staffWelfare + obj.telecommunicationOrUtilities + obj.training + obj.c1_TransportExp + obj.upkeepNonPrivateVehicles + obj.upkeepPrivateVehicles

    @api.depends('totalRevenue', 'totalOtherIncome', 'totalExpenses')
    def _compute_profitLossBeforeTaxation(self):
        for obj in self:
            obj.profitLossBeforeTaxation = obj.totalRevenue - obj.costOfGoodsSold + obj.totalOtherIncome - obj.totalExpenses

    @api.depends('totalRevenue', 'costOfGoodsSold')
    def _compute_gross_pl(self):
        for obj in self:
            obj.grossPL = obj.totalRevenue - obj.costOfGoodsSold

    @api.depends('ya')
    def _get_year_int(self):
        for obj in self:
            obj.ya_int = int(obj.ya)

    @api.depends('cyDonation', 'DataFormCS_cyDonation') #Jun2025
    def _compute_ptisDonInd_mandatory(self):
        for rec in self:
            rec.ptisDonInd_mandatory = rec.DataFormCS_cyDonation > rec.cyDonation

    ya = fields.Selection(_get_year, string="Year of Assessment", required=True, tracking=True)
    ya_int = fields.Integer(string="Year of Assessment (Technical)", compute="_get_year_int", store=True)
    singpass_url = fields.Char("Singpass Login URL", tracking=True)
    state_identifier = fields.Char("State Identifier", tracking=True)
    access_token = fields.Text("Access Token", tracking=True) 
    auth_code = fields.Char("Auth Code", tracking=True)
    active = fields.Boolean('Active', default=True)
    access_token_datetime = fields.Datetime(string="Access Token Datetime", store=True, readonly=False, tracking=True)
    access_token_expired = fields.Boolean(string="Access Token Expired", tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, readonly=True, tracking=True)
    state = fields.Selection(
        [
         ('new', "New"),
         ('pre_fill', "CIT Pre-fill"),
         ('conversion', "CIT Conversion"),
         ('cs_submission', "Form C-S"),
         ('submitted', 'Submitted')],
        default='new', string='Status', tracking=True)
    uen = fields.Char(string="UEN No.", size=10, required=True, tracking=True, default=lambda self: self.env.company.l10n_sg_unique_entity_number)
    uenType = fields.Selection([('6','ROC'),('35','UENO'),('8','ASGD'),('10','ITR')], string="UEN Type", tracking=True, required=True)
    basisPeriodFrom = fields.Date(string="Period Start Date", required=True, tracking=True)
    basisPeriodTo = fields.Date(string="Period End Date", required=True, tracking=True)
    declarantRefNo = fields.Char(string="Tax Reference Number assigned by IRAS for foreigners not eligible for Singpass", size=9, tracking=True, help="Note: 1) Mandatory for foreigners not eligible for Singpass. 2) Enter IRAS assigned tax reference number for Foreigners not eligible for Singpass (e.g. AxxxxxxxZ)")
    taxReturnChk = fields.Boolean(string="Is it the first tax return?", tracking=True)
    fsPrep = fields.Selection([('1','1'),('2','2')], string="How many sets of financial statements did the company prepare for the period declared?", tracking=True)
    firstFYE = fields.Date(string="The financial year end of the first set of financial statements", tracking=True)
    prevFYE = fields.Date(string="There is a change in the company's financial year end. The financial year end of the company before the change.", tracking=True)
    months_difference = fields.Integer(compute="_get_month_difference", store=True)
    unutilCABFNorm = fields.Float(string="Unutilised Capital Allowances brought forward", digits=(12, 0), required=True, tracking=True, default=0.0)
    unutilLossBFNorm = fields.Float(string="Unutilised Losses brought forward", digits=(12, 0), required=True, tracking=True, default=0.0)
    unutilDonationBFNorm = fields.Float(string="Unutilised Donations brought forward", digits=(12, 0), required=True, tracking=True, default=0.0)
    cyDonation = fields.Float(string="Current Year Donations", digits=(12, 0), required=True, tracking=True, default=0.0)

    nameOfFiler = fields.Char(string="Name of Filer", default=lambda self: self.env.user.name)
    designationOfFiler = fields.Char(string="Designation of Filer", tracking=True, size=30)
    contactNumber = fields.Char(string="Contact No. (+65)", tracking=True, size=30, default=lambda self: self.env.user.phone)
    inventories = fields.Integer(string="Inventories", tracking=True, default=0.0)
    tradeReceivables = fields.Integer(string="Trade Receivables", tracking=True, default=0.0)
    totalRevenue = fields.Integer(string="Total Revenue", required=True, tracking=True, store=True) #compute="_get_totalRevenew"
    costOfGoodsSold = fields.Integer(string="Cost of Goods Sold", required=True, tracking=True)
    totalOtherIncome = fields.Integer(string="Total Other Income", compute="_compute_total_otherincome", required=True, tracking=True)
    sgIntDisc = fields.Integer(string="Interest Income", required=True, tracking=True)
    oneTierTaxDividendIncome = fields.Integer(string="Dividend Income - One-Tier", required=True, tracking=True)
    c1_GrossRent = fields.Integer(string="Gross Rental Income", required=True, tracking=True)
    sgOtherI = fields.Integer(string="Other Taxable Income", required=True, tracking=True)
    otherNonTaxableIncome = fields.Integer(string="Other non-Taxable Income", required=True, tracking=True)
    grossPL = fields.Integer(string="Gross Profit/ Loss", compute="_compute_gross_pl", readonly=True, tracking=True)
    amortisationExpense = fields.Integer(string="Amortisation Expense", required=True, tracking=True)
    bankCharges = fields.Integer(string="Bank Charges", required=True, tracking=True)
    commissionOther = fields.Integer(string="Commission (Other Than Expenses Incurred to Derive Rental Income)", required=True, tracking=True)
    depreciationExpense = fields.Integer(string="Depreciation Expense", required=True, tracking=True)
    directorsFees = fields.Integer(string="Director's Fees", required=True, tracking=True)
    directorsRemunerationExcludingDirectorsFees = fields.Integer(string="Director's Remuneration (Excluding Director's Fees)", required=True, tracking=True)
    donations = fields.Integer(string="Donations", required=True, tracking=True)
    cpfContribution = fields.Integer(string="CPF Contribution", required=True, tracking=True)
    c1_EntertainExp = fields.Integer(string="Entertainment Expenses", required=True, tracking=True)
    commissionExpRentalIncome = fields.Integer(string="Expenses Incurred to Derive Rental Income - Commission", required=True, tracking=True)
    insuranceExpRentalIncome = fields.Integer(string="Expenses Incurred to Derive Rental Income - Insurance", required=True, tracking=True)
    interestExpRentalIncome = fields.Integer(string="Expenses Incurred to Derive Rental Income - Interest", required=True, tracking=True)
    propertyTaxExpRentalIncome = fields.Integer(string="Expenses Incurred to Derive Rental Income - Property Tax", required=True, tracking=True)
    repairMaintenanceExpRentalIncome = fields.Integer(string="Expenses Incurred to Derive Rental Income - Repair and Maintenance", required=True, tracking=True)
    otherExpRentalIncome = fields.Integer(string="Expenses Incurred to Derive Rental Income - Others", required=True, tracking=True)
    fixedAssetsExpdOff = fields.Integer(string="Fixed Assets Expensed Off", required=True, tracking=True)
    insuranceExpOther = fields.Integer(string="Insurance (Other Than Medical Expenses and Expenses Incurred to Derive Rental Income)", required=True, tracking=True)
    interestExpOther = fields.Integer(string="Interest Expenses (Other Than Expenses Incurred to Derive Rental Income)", required=True, tracking=True)
    impairmentLossReversalOfImpairmentLossForBadDebts = fields.Integer(string="Impairment Loss/ Reversal of Impairment Loss for Bad Debts", required=True, tracking=True, default=0.0)
    medicalExpIncludingMedicalInsurance = fields.Integer(string="Medical Expenses (Including Medical Insurance)", required=True, tracking=True, default=0.0)
    netGainsOrLossesOnDisposalOfPPE = fields.Integer(string="Net Gains/ Losses on Disposal of Property, Plant and Equipment", required=True, tracking=True, default=0.0)
    netGainsOrLossesOnForex = fields.Integer(string="Net Gains/ Losses on Foreign Exchange Adjustment", required=True, tracking=True, default=0.0)
    netGainsOrLossesOnOtherItems = fields.Integer(string="Net Gains/ Losses on Other Items", required=True, tracking=True, default=0.0)
    miscExp = fields.Integer(string="Miscellaneous Expenses", required=True, tracking=True, default=0.0)
    otherPrivateOrCapitalExp = fields.Integer(string="Other Private/ Capital Expenses", required=True, tracking=True, default=0.0)
    otherFinanceCost = fields.Integer(string="Other Finance Cost", required=True, tracking=True, default=0.0)
    penaltiesOrFine = fields.Integer(string="Penalties/ Fine", required=True, tracking=True, default=0.0)
    professionalFees = fields.Integer(string="Professional Fees", required=True, tracking=True, default=0.0)
    propertyTaxOther = fields.Integer(string="Property Tax (Other Than Expenses Incurred to Derive Rental Income)", required=True, tracking=True, default=0.0)
    rentExp = fields.Integer(string="Rent Expense", required=True, tracking=True, default=0.0)
    repairMaintenanceExcludingUpkeepOfPrivateVehiclesAndExp = fields.Integer(string="Repairs and Maintenance (Excluding Private Motor Vehicles and Expenses Incurred to Derive Rental Income)", required=True, tracking=True, default=0.0)
    repairsMaintenanceForPrivateVehicles = fields.Integer(string="Repairs and Maintenance (Private Motor Vehicles)", required=True, tracking=True, default=0.0)
    salesAndMarketingExpense = fields.Integer(string="Sales and Marketing Expense", required=True, tracking=True, default=0.0)
    skillsDevelopmentForeignWorkerLevy = fields.Integer(string="Skills Development Levy/ Foreign Worker Levy", required=True, tracking=True, default=0.0)
    staffRemunerationOtherThanDirectorsRemuneration = fields.Integer(string="Staff Remuneration (Other Than Director's Remuneration)", required=True, tracking=True, default=0.0)
    staffWelfare = fields.Integer(string="Staff Welfare", required=True, tracking=True, default=0.0)
    telecommunicationOrUtilities = fields.Integer(string="Telecommunication/ Utilities", required=True, tracking=True, default=0.0)
    training = fields.Integer(string="Training", required=True, tracking=True, default=0.0)
    c1_TransportExp = fields.Integer(string="Transport/ Travelling Expenses", required=True, tracking=True, default=0.0)
    upkeepNonPrivateVehicles = fields.Integer(string="Upkeep of Non-private Motor Vehicles", required=True, tracking=True, default=0.0)
    upkeepPrivateVehicles = fields.Integer(string="Upkeep of Private Motor Vehicles", required=True, tracking=True, default=0.0)
    totalExpenses = fields.Integer(string="Total Expenses", compute="_compute_totalExpenses", readonly=True, tracking=True)
    profitLossBeforeTaxation = fields.Integer(string="Profit/ Loss before Taxation", compute="_compute_profitLossBeforeTaxation", required=True, tracking=True, default=0.0)
    sepSrcIncome = fields.Float(string="Separate Source Income", readonly=False, tracking=True)
    medicalExpDisallowed = fields.Float(string="Medical Expenses Disallowed", readonly=True, tracking=True)
    totalRemuneration = fields.Float(string="Total Remunueration", readonly=True, tracking=True)
    onePercentOfTotalRemuneration = fields.Float(string="1% of Total Remuneration", readonly=True, tracking=True)
    c1_NTDeductibleExp = fields.Float(string="Non-Tax Deductible Expenses", readonly=False, tracking=True)
    adjPLBefDed = fields.Float(string="Adjusted Profit/ Loss before Other Deductions", readonly=False, tracking=True)
    renoWorksExpS14Q = fields.Float(string="Total Section 14Q14N Deduction", readonly=False, tracking=True)
    c1_FurtherDed = fields.Float(string="Further Deductions/ Other Deductions", digits=(11,0), tracking=True)
    sgAdjPLAft = fields.Float(string="Adjusted Profit/ Loss before Capital Allowances", readonly=False, tracking=True)
    c1_BC = fields.Float(string="Balancing Charge (Non-HP & HP)", readonly=False, tracking=True)
    currentYearCapitalAllowancesNonHPAndHP = fields.Float(string="Current Year Capital Allowances (Non-HP & HP)", readonly=True, tracking=True)
    balancingAllowancesNonHPandHP = fields.Float(string="Balancing Allowances (Non-HP & HP)", readonly=True, tracking=True)
    unutilCACFNorm = fields.Float(string="Unutilised Capital Allowances carried forward", readonly=False, tracking=True)
    unutilLossCFNorm = fields.Float(string="Unutilised Losses carried forward", readonly=False, tracking=True)
    adjustedProfitOrLossAfterCapitalAllowanceAndUnutilisedLossesBF = fields.Float(string="Adjusted Profit/ Loss after Capital Allowance and Unutilised Losses brought forward", readonly=True, tracking=True)
    sgRent = fields.Float(string="Net Rental Income", readonly=False, tracking=True)
    totSgFI = fields.Float(string="Total Income/ Losses before Donations", readonly=False, tracking=True)
    unutilDonationCFNorm = fields.Float(string="Unutilised Donations carried forward", readonly=False, tracking=True)
    chargeableIncomeBefTaxExemptAmt = fields.Float(string="Chargeable Income (before Tax Exempt Amount)", readonly=True, tracking=True)
    taxExemptAmount = fields.Float(string="Tax Exempt Amount", readonly=True, tracking=True)
    chargeableIncomeAftTaxExemptAmt = fields.Float(string="Chargeable Income (after Tax Exempt Amount)", readonly=True, tracking=True)
    taxPayable = fields.Float(string="Tax Payable", readonly=True, tracking=True)
    taxRebate = fields.Float(string="Tax Rebate", readonly=True, tracking=True)
    netTaxPayable = fields.Float(string="Net Tax Payable", readonly=True, tracking=True)
    sholderChange = fields.Selection([('1', "Yes"), ('2', "No")], string="Is There a Substantial Change in the Company's Ultimate Shareholders and Their Shareholdings as at the Relevant Dates?", tracking=True, default='2')
    uCALDChangePrinAct = fields.Selection([('1', "Yes"), ('2', "No")], string="Is There a Change in the Principal Activities of the Company during the Relevant Dates?", tracking=True, default='2')
    fullTxX = fields.Selection([('1', "Yes"), ('2', "No")], string="Has the Company Satisfied All Conditions to Qualify for the Tax Exemption Scheme for New Start-Up Companies?", tracking=True, default='2')
    unutilCALDClaimS23S37 = fields.Float(string="Unutilised Capital Allowances/ Losses/ Donations Claimed where Waiver of  the Shareholding Test Has Been Granted by IRAS", tracking=True, default=0.0)
    hpOtherPPE_ids = fields.One2many('hp.other.ppe','form_cs_id', string="Other Property, Plant and Equipment (HP)")
    nonHPCompCommEquipment_ids = fields.One2many('non.hp.compcommequipment','form_cs_id', string="Computer And Communication Equipment (Non-HP)")
    nonHpOtherPPE_ids = fields.One2many('non.hp.other.ppe', 'form_cs_id', string="Other Property, Plant and Equipment (Non-HP)")
    nonHpOtherPPElowvalueasset_ids = fields.One2many('non.hp.other.ppe.lowvalueasset', 'form_cs_id', string="Other Property, Plant and Equipment (Non-HP)(Low Value Assets)")
    iaAaPriorSeamlessFiling = fields.Float(string="Initial or Annual Allowance (Assets acquired prior to Seamless Filing Solution)", digits=(11, 0), tracking=True)
    baPriorSeamlessFiling = fields.Float(string="Balancing Allowance (Assets acquired prior to Seamless Filing Solution)", digits=(11, 0), tracking=True)
    bcPriorSeamlessFiling = fields.Float(string="Balancing Charge (Assets acquired prior to Seamless Filing Solution)", digits=(11, 0), tracking=True)
    firstYAInWhichS14QDeductionClaimed = fields.Selection(_get_year, string="First YA in which Leasehold Improvements and Renovation Cost was Incurred and Section 14N Deduction Claimed", tracking=True)
    isRevBelow5M = fields.Selection([('Yes','Yes'),('No','No')], string="Declaration: The Company's Revenue For The Financial Year is $5,000,000 Or Below", tracking=True, default='Yes')
    isOnlyIncTxbl17 = fields.Selection([('Yes','Yes'),('No','No')], string="Declaration: The Company Derives Only Income Taxable At 17% (Excluding Exempt Income)", tracking=True, default='Yes')
    isNotClaimingSpecificItems = fields.Selection([('Yes','Yes'),('No','No')], string="Declaration: The Company Is Not Claiming/ Utilising Any Of The Following Items:Any Of The Following Items: -Carry-back Of Current Year Capital Allowances/Losses -Group Relief -Investment Allowance -Foreign Tax Credit And Tax Deducted At Source", tracking=True, default='Yes')
    expRD = fields.Float(string="Deduction for Expenditure Incurred on R&D - Total Deduction under Section 14C", digits=(11, 0), tracking=True)
    expRDSG = fields.Float(string="Section 14C Deduction for Expenditure Incurred on R&D Activities undertaken in Singapore", required=True, digits=(11, 0), tracking=True, default=0.0)
    enhanceDeductRD = fields.Float(string="Staff Costs and Consumables for R&D Activities Undertaken in Singapore Qualifying for Section 14D(1)", required=True, digits=(11, 0), tracking=True, default=0.0)
    # furtherDeductRD = fields.Float(string="Further Deduction for Expenditure on R&D Project - Section 14E", required=True, digits=(11, 0), tracking=True, default=0.0)
    appStockConvAsset = fields.Selection([('1', "Yes"), ('2', "No")], string="Has the company appropriated any trading stock for non-trade or capital purposes under Section 10J and/ or converted any non-trade or capital asset to trading stock under Section 32A?", default="2")
    acknowledgementNo = fields.Char(string="Acknowledgement No.", tracking=True)
    c1_DedExp = fields.Float(string="Deductible Expenses", readonly=False, tracking=True)
    ci = fields.Float(string="Total Income/ Losses after Donations", readonly=False, tracking=True)
    cyCANorm = fields.Float(string="Current Year Capital Allowances", readonly=False, tracking=True)
    designationOfContactPerson = fields.Char(string="Designation of Contact Person", tracking=True, size=30, default=lambda self: self.env.user.partner_id.function)
    directorFee = fields.Float(string="Directors' Fees and Remuneration", readonly=False, tracking=True)
    estTaxPayable = fields.Float(string="Estimated Tax Payable", tracking=True, default=0.0)
    medicalExp = fields.Float(string="Medical Expenses", readonly=False, tracking=True)
    nameOfContactPerson = fields.Char(string="Name of Contact Person", tracking=True, size=30, default=lambda self: self.env.user.name)
    receiptNotTxAmt = fields.Float(string="Non-Taxable Income", readonly=False, tracking=True)
    timestamp = fields.Datetime(string="Date/ Time", tracking=True)
    timestamp_str = fields.Char(string="Date/ Time", tracking=True)
    totRemuneration = fields.Float(string="Total Remuneration excluding Directors' Fees and Remuneration", readonly=False, tracking=True)
    isFullAndTrueAccOfCompInc = fields.Boolean(string="Declaration: The company declares that this return give a full and true account of the whole of the company's income for the financial period ending in the preceding year.", required=True, tracking=True, default=True)
    isQualifiedToUseConvFormCS = fields.Boolean(string="Declaration: The company maintains Singapore dollar as its functional/ presentation currency. The company is not an investment holding company or a service company that provides only related party services. The company does not own subsidiaries, associates or joint ventures, and has no investment in intangibles.", tracking=True, default=True)
    sctpInd = fields.Selection([('1', "Yes"), ('2', "No")], string="The return has been reviewed by a person who is a Singapore Chartered Tax Professionals Limited (SCTP) Accredited Tax Advisor or Accredited Tax Practitioner for Income Tax.", tracking=True, default='1')
    sctpName = fields.Char(string="Name of person", tracking=True, default=lambda self: self.env.user.name)
    sctpNo = fields.Char(string="SCTP membership number", tracking=True)
    renovation_refurbishment_sch_ids = fields.One2many('renovation.refurbishment.schedule','form_cs_id',string="Renovation & Refurbishment Schedule")
    revenueFromPropertyTransferredAtPointInTime = fields.Float(string="Revenue recognised at a point in time - Properties", tracking=True)
    revenueFromGoodsTransferredAtPointInTime = fields.Float(string="Revenue recognised at a point in time - Goods (excluding properties)", tracking=True)
    revenueFromServicesTransferredAtPointInTime = fields.Float(string="Revenue recognised at a point in time - Services", tracking=True)
    revenueFromPropertyTransferredOverTime = fields.Float(string="Revenue recognised over time - Properties", tracking=True)
    revenueFromConstructionContractsOverTime = fields.Float(string="Revenue recognised over time - Construction contracts (excluding properties)", tracking=True)
    revenueFromServicesTransferredOverTime = fields.Float(string="Revenue recognised over time - Services", tracking=True)
    revenueOthers = fields.Float(string="Revenue - Others", tracking=True)
    theLeaseholdImprovementsAndRenoCost = fields.Selection([('1', 'Yes'),('2', 'No')], string="Does Leasehold Improvements and Renovation Cost Require the Approval of the Commissioner of Building Control under the Building Control Act?", tracking=True)
    is_fetched = fields.Boolean(default=False)
    signed_by = fields.Char('Signed By', tracking=True, copy=False,  default=lambda self: self.env.user.name if self.env.user else self.partner_id.name)
    manager_signature_done = fields.Boolean(copy=False)
    manager_signature = fields.Binary(string="Signature", attachment=True, tracking=True, copy=False)

    c1_EnhancedEISDed = fields.Float(string='Enhanced Deductions under Enterprise Innovation Scheme (EIS) for Training; Innovation Projects carried out with Partner Institutions; Licensing of Intellectual Property Rights; Registration of Intellectual Property; Qualfiying R&D undertaken in Singapore', digits=(11, 0), tracking=True)
    enhancedEISCA = fields.Integer(string='Enhanced Allowance under Enterprise Innovation Scheme (EIS) for Acquisition of Intellectual Property Rights (IPRs)', tracking=True)
    eis_ClaimCashPayout = fields.Selection([('1', 'Yes'),('2', 'No')], default="2", string="Is the company claiming cash payout under the EIS in this current YA?", tracking=True)
    eis_ClaimDedAll = fields.Selection([('1', 'Yes'),('2', 'No')], default="2", string="Is the company claiming enhanced deductions/ allowances under the EIS in this current YA?", tracking=True)
    eis_TrainTotCost = fields.Integer(string="Total Qualifying Cost Incurred", tracking=True)
    eis_TrainDedAll = fields.Integer(string="Enhanced Deductions/ Allowances Claimed/ To Be Claimed", tracking=True)
    eis_InnoProjTotCost = fields.Integer(string="Total Qualifying Cost Incurred (capped at $50,000)", tracking=True)
    eis_InnoProjDedAll = fields.Integer(string="Enhanced Deductions/ Allowances Claimed/ To Be Claimed ", tracking=True)
    eis_AcqIPRTotCost = fields.Integer(string="Total Qualifying Cost Incurred", tracking=True)
    eis_AcqIPRDedAll = fields.Integer(string="Enhanced Deductions/ Allowances Claimed/ To Be Claimed", tracking=True)
    eis_LicensIPRTotCost = fields.Integer(string="Total Qualifying Cost Incurred", tracking=True)
    eis_LicensIPRDedAll = fields.Integer(string="Enhanced Deductions/ Allowances Claimed/ To Be Claimed", tracking=True)
    eis_RegIPTotCost = fields.Integer(string="Total Qualifying Cost Incurred", tracking=True)
    eis_RegIPDedAll = fields.Integer(string="Enhanced Deductions/ Allowances Claimed/ To Be Claimed", tracking=True)
    eis_RDSgTotCost = fields.Integer(string="Total Qualifying Cost Incurred", tracking=True)
    eis_RDSgDedAll = fields.Integer(string="Enhanced Deductions/ Allowances Claimed/ To Be Claimed", tracking=True)
    #Jun2025
    ptisDonInd = fields.Selection([('1', "Yes"), ('2', "No")], string="Is the company an approved qualifying donor making qualifying overseas donations under the Philanthropy Tax Incentive Scheme for Family Offices (PTIS)?", tracking=True, default='2')
    foreignAssetsSaleGainLoss = fields.Float(string="Amount of gains/ losses from the sale or disposal of foreign assets during the basis period for the current YA", tracking=True)
    foreignSourceSaleGainsRemit = fields.Float(string="Amount of the foreign-sourced sale or disposal gains remitted to Singapore during the basis period for the current YA", tracking=True)
    foreignSourceSaleNotTax = fields.Selection([('1', "Yes"), ('2', "No")], string="Do the foreign-sourced sale or disposal gains/ losses fall under any of the scenarios where the sale or disposal of foreign assets (excluding foreign IPRs) is not subject to tax under Section 10L(8) of the ITA?", tracking=True, default='2')
    ptisDonInd_mandatory = fields.Boolean(string='ptisDonInd Is Mandatory?', compute="_compute_ptisDonInd_mandatory")
    
    renovation_refurbishment_sch_resp_ids = fields.One2many('renovation.refurbishment.schedule.response','form_cs_response_id',string="Renovation & Refurbishment Schedule Response")
    nonHpOtherPPE_nonHPAddsDuringTheYear_ids = fields.One2many('capital.allowance.response','form_cs_id1')
    nonHpOtherPPE_LowValAsset_nonHPAddsDuringTheYear_ids = fields.One2many('capital.allowance.response','form_cs_id2',string="Capital Allowances Schedule")
    nonHPCompCommEquipment_nonHPAddsDuringTheYear_ids = fields.One2many('capital.allowance.response','form_cs_id3',string="Capital Allowances Schedule")
    hpOtherPPE_hpAddsDuringTheYear_ids = fields.One2many('capital.allowance.response','form_cs_id4',string="Capital Allowances Schedule")
    nonHpOtherPPE_nonHPPriorYearAdds_ids = fields.One2many('capital.allowance.response','form_cs_id5',string="Capital Allowances Schedule")
    hpOtherPPE_hpPriorYearAdditions_ids = fields.One2many('capital.allowance.response','form_cs_id6',string="Capital Allowances Schedule")
    nonHpOtherPPE_nonHPDispDuringTheYear_ids = fields.One2many('capital.allowance.response','form_cs_id7',string="Capital Allowances Schedule")
    nonHpOtherPPE_LowValAsset_nonHPDispDuringTheYear_ids = fields.One2many('capital.allowance.response','form_cs_id8',string="Capital Allowances Schedule")
    nonHPCompCommEquipment_nonHPDispDuringTheYear_ids = fields.One2many('capital.allowance.response','form_cs_id9',string="Capital Allowances Schedule")
    hpOtherPPE_hpDispDuringTheYear_ids = fields.One2many('capital.allowance.response','form_cs_id10',string="Capital Allowances Schedule")

    DataMedExpSch_cpfContribution = fields.Float(string="CPF Contribution")
    DataMedExpSch_directorsRemExclDirectorsFees = fields.Float(string="Director's Remuneration (Excluding Director's Fees)")
    DataMedExpSch_medicalExpDisallowed = fields.Float(string="Medical Expenses Disallowed")
    DataMedExpSch_medicalExpIncludingMedicalInsurance = fields.Float(string="Medical Expenses (Including Medical Insurance)")
    DataMedExpSch_onePercentOfTotalRemuneration = fields.Float(string="1% of Total Remuneration")
    DataMedExpSch_staffRemOtherThanDirectorsRem = fields.Float(string="Staff Remuneration (Other Than Director's Remuneration)")
    DataMedExpSch_totalRemuneration = fields.Float(string="Total Remunueration")

    DataRentalSch_c1_GrossRent = fields.Float(string="Gross Rental Income")
    DataRentalSch_commissionExpRentalIncome = fields.Float(string="Expenses Incurred to Derive Rental Income - Commission")
    DataRentalSch_insuranceExpRentalIncome = fields.Float(string="Expenses Incurred to Derive Rental Income - Insurance")
    DataRentalSch_interestExpRentalIncome = fields.Float(string="Expenses Incurred to Derive Rental Income - Interest")
    DataRentalSch_otherExpRentalIncome = fields.Float(string="Expenses Incurred to Derive Rental Income - Others")
    DataRentalSch_propertyTaxExpRentalIncome = fields.Float(string="Expenses Incurred to Derive Rental Income - Property Tax")
    DataRentalSch_repairMaintenanceExpRentalIncome = fields.Float(string="Expenses Incurred to Derive Rental Income - Repair and Maintenance")
    DataRentalSch_sgRent = fields.Float(string="Net Rental Income")

    DataRRSch_renoWorksExpS14Q = fields.Float(string="Total Section 14N deduction")

    DataTCSch_adjPLBefDed = fields.Float(string="Adjusted Profit/ Loss before Other Deductions")
    DataTCSch_adjustedProfitOrLossAfterCapAllowAndUnutilisedLosBF = fields.Float(string="Adjusted Profit/ Loss after Capital Allowance and Unutilised Losses brought forward")
    DataTCSch_amortisationExpense = fields.Float(string="Amortisation Expense")
    DataTCSch_balancingAllowancesNonHPandHP = fields.Float(string="Balancing Allowances (Non-HP & HP)")
    DataTCSch_c1_BC = fields.Float(string="Balancing Charge (Non-HP & HP)")
    DataTCSch_c1_FurtherDed = fields.Float(string="Further Deductions/ Other Deductions")
    DataTCSch_c1_NTDeductibleExp = fields.Float(string="Non-Tax Deductible Expenses")
    DataTCSch_c1_GrossRent = fields.Float(string="Gross Rental Income")
    DataTCSch_chargeableIncomeAftTaxExemptAmt = fields.Float(string="Chargeable Income (after Tax Exempt Amount)")
    DataTCSch_chargeableIncomeBefTaxExemptAmt = fields.Float(string="Chargeable Income (before Tax Exempt Amount)")
    DataTCSch_commissionExpRentalIncome = fields.Float(string="Expenses Incurred to Derive Rental Income - Commission")
    DataTCSch_currentYearCapitalAllowancesNonHPAndHP = fields.Float(string="Current Year Capital Allowances (Non-HP & HP)")
    DataTCSch_cyDonation = fields.Float(string="Current Year Donations")
    DataTCSch_depreciationExpense = fields.Float(string="Depreciation Expense")
    DataTCSch_donations = fields.Float(string="Donations")
    DataTCSch_fixedAssetsExpdOff = fields.Float(string="Fixed Assets Expensed Off")
    DataTCSch_insuranceExpRentalIncome = fields.Float(string="Expenses Incurred to Derive Rental Income - Insurance")
    DataTCSch_interestExpRentalIncome = fields.Float(string="Expenses Incurred to Derive Rental Income - Interest")
    DataTCSch_medicalExpDisallowed = fields.Float(string="Medical Expenses Disallowed")
    DataTCSch_netGainsOrLossesOnDisposalOfPPE = fields.Float(string="Net Gains/ Losses on Disposal of Property, Plant and Equipment")
    DataTCSch_netGainsOrLossesOnOtherItems = fields.Float(string="Net Gains/ Losses on Other Items")
    DataTCSch_otherPrivateOrCapitalExp = fields.Float(string="Other Private/ Capital Expenses")
    DataTCSch_netTaxPayable = fields.Float(string="Net Tax Payable")
    DataTCSch_oneTierTaxDividendIncome = fields.Float(string="Dividend Income - One-Tier")
    DataTCSch_otherNonTaxableIncome = fields.Float(string="Other non-Taxable Income")
    DataTCSch_otherExpRentalIncome = fields.Float(string="Expenses Incurred to Derive Rental Income - Others")
    DataTCSch_penaltiesOrFine = fields.Float(string="Penalties/ Fine")
    DataTCSch_profitLossBeforeTaxation = fields.Float(string="Profit/ Loss before Taxation")
    DataTCSch_propertyTaxExpRentalIncome = fields.Float(string="Expenses Incurred to Derive Rental Income - Property Tax")
    DataTCSch_repairMaintenanceExpRentalIncome = fields.Float(string="Expenses Incurred to Derive Rental Income - Repair and Maintenance")
    DataTCSch_sgOtherI = fields.Float(string="Other Taxable Income")
    DataTCSch_sgIntDisc = fields.Float(string="Interest Income")
    DataTCSch_sepSrcIncome = fields.Float(string="Separate Source Income")
    DataTCSch_receiptNotTxAmt = fields.Float(string="Non-Taxable Income")
    DataTCSch_repairsMaintenanceForPrivateVehicles = fields.Float(string="Repairs and Maintenance (Private Motor Vehicles)")
    DataTCSch_upkeepPrivateVehicles = fields.Float(string="Upkeep of Private Motor Vehicles")
    DataTCSch_renoWorksExpS14Q = fields.Float(string="Total Section 14Q14N deduction")
    DataTCSch_sgAdjPLAft = fields.Float(string="Adjusted Profit/ Loss before Capital Allowances")
    DataTCSch_totSgFI = fields.Float(string="Total Income/ Losses before Donations")
    DataTCSch_unutilCABFNorm = fields.Float(string="Unutilised Capital Allowances brought forward")
    DataTCSch_unutilDonationBFNorm = fields.Float(string="Unutilised Donations brought forward")
    DataTCSch_taxPayable = fields.Float(string="Tax Payable")
    DataTCSch_taxRebate = fields.Float(string="Tax Rebate")
    DataTCSch_unutilCACFNorm = fields.Float(string="Unutilised Capital Allowances carried forward")
    DataTCSch_unutilLossCFNorm = fields.Float(string="Unutilised Losses carried forward")
    DataTCSch_unutilDonationCFNorm = fields.Float(string="Unutilised Donations carried forward")
    DataTCSch_taxExemptAmount = fields.Float(string="Tax Exempt Amount")
    DataTCSch_unutilLossBFNorm = fields.Float(string="Unutilised Losses brought forward")
    DataTCSch_sgRent = fields.Float(string="Net Rental Income")
    DataTCSch_c1_EnhancedEISDed = fields.Float(string='Enhanced Deductions under Enterprise Innovation Scheme (EIS) for Training; Innovation Projects carried out with Partner Institutions; Licensing of Intellectual Property Rights; Registration of Intellectual Property; Qualfiying R&D undertaken in Singapore')
    DataTCSch_ptisDonInd = fields.Selection([('1', "Yes"), ('2', "No")], string="Is the company an approved qualifying donor making qualifying overseas donations under the Philanthropy Tax Incentive Scheme for Family Offices (PTIS)?") #Jun2025


    DataFormCS_adjPLBefDed = fields.Float(string="Adjusted Profit/ Loss before Other Deductions")
    DataFormCS_c1_BC = fields.Float(string="Balancing Charge (Non-HP & HP)")
    DataFormCS_c1_DedExp = fields.Float(string="Deductible Expenses")
    DataFormCS_c1_EntertainExp = fields.Float(string="Entertainment Expenses")
    DataFormCS_c1_FurtherDed = fields.Float(string="Further Deductions/ Other Deductions")
    DataFormCS_c1_GrossRent = fields.Float(string="Gross Rental Income")
    DataFormCS_c1_NTDeductibleExp = fields.Float(string="Non-Tax Deductible Expenses")
    DataFormCS_c1_TransportExp = fields.Float(string="Transport/ Travelling Expenses")
    DataFormCS_ci = fields.Float(string="Total Income/ Losses after Donations")
    DataFormCS_cyCANorm = fields.Float(string="Current Year Capital Allowances")
    DataFormCS_cyDonation = fields.Float(string="Current Year Donations")
    DataFormCS_directorFee = fields.Float(string="Directors' Fees and Remuneration")
    DataFormCS_enhanceDeductRD = fields.Float(string="Staff Costs and Consumables for R&D Activities Undertaken in Singapore Qualifying for Section 14D(1)")
    DataFormCS_expRD = fields.Float(string="Deduction for Expenditure Incurred on R&D - Total Deduction under Section 14C")
    DataFormCS_expRDSG = fields.Float(string="Section 14C Deduction for Expenditure Incurred on R&D Activities undertaken in Singapore")
    DataFormCS_fullTxX = fields.Selection([('1', "Yes"), ('2', "No")], string="Has the Company Satisfied All Conditions to Qualify for the Tax Exemption Scheme for New Start-Up Companies?")
    DataFormCS_grossPL = fields.Float(string="Gross Profit/ Loss")
    DataFormCS_inventories = fields.Float(string="Inventories", digits=(11,2))
    DataFormCS_medicalExp = fields.Float(string="Medical Expenses")
    DataFormCS_profitLossBeforeTaxation = fields.Float(string="Profit/ Loss before Taxation")
    DataFormCS_receiptNotTxAmt = fields.Float(string="Non-Taxable Income")
    DataFormCS_renoWorksExpS14Q = fields.Float(string="Total Section 14Q14N deduction")
    DataFormCS_sepSrcIncome = fields.Float(string="Separate Source Income")
    DataFormCS_sgIntDisc = fields.Float(string="Interest Income")
    DataFormCS_sgOtherI = fields.Float(string="Other Taxable Income")
    DataFormCS_sgRent = fields.Float(string="Net Rental Income")
    DataFormCS_sholderChange = fields.Selection([('1', "Yes"), ('2', "No")], string="Is There a Substantial Change in the Company's Ultimate Shareholders and Their Shareholdings as at the Relevant Dates?")
    DataFormCS_totRemuneration = fields.Float(string="Total Remuneration excluding Directors' Fees and Remuneration", readonly=True, tracking=True)
    DataFormCS_totSgFI = fields.Float(string="Total Income/ Losses before Donations")
    DataFormCS_sgAdjPLAft = fields.Float(string="Adjusted Profit/ Loss before Capital Allowances")
    DataFormCS_totalRevenue = fields.Float(string="Total Revenue")
    DataFormCS_tradeReceivables = fields.Float(string="Trade Receivables", digits=(11, 2))
    DataFormCS_uCALDChangePrinAct = fields.Selection([('1', "Yes"), ('2', "No")], string="Is There a Change in the Principal Activities of the Company during the Relevant Dates?")
    DataFormCS_unutilLossBFNorm = fields.Float(string="Unutilised Losses brought forward")
    DataFormCS_unutilCABFNorm = fields.Float(string="Unutilised Capital Allowances brought forward")
    DataFormCS_unutilCACFNorm = fields.Float(string="Unutilised Capital Allowances carried forward")
    DataFormCS_unutilLossCFNorm = fields.Float(string="Unutilised Losses carried forward")
    DataFormCS_unutilDonationCFNorm = fields.Float(string="Unutilised Donations carried forward")
    DataFormCS_unutilDonationBFNorm = fields.Float(string="Unutilised Donations brought forward")
    DataFormCS_unutilCALDClaimS23S37 = fields.Float(string="Unutilised Capital Allowances/ Losses/ Donations Claimed where Waiver of  the Shareholding Test Has Been Granted by IRAS")
    DataFormCS_appStockConvAsset = fields.Selection([('1', "Yes"), ('2', "No")], string="Has the company appropriated any trading stock for non-trade or capital purposes under Section 10J and/ or converted any non-trade or capital asset to trading stock under Section 32A?")
    DataFormCS_c1_EnhancedEISDed = fields.Integer(string="Enhanced Deductions under Enterprise Innovation Scheme (EIS) for Training; Innovation Projects carried out with Partner Institutions; Licensing of Intellectual Property Rights; Registration of Intellectual Property; Qualfiying R&D undertaken in Singapore")
    DataFormCS_eis_AcqIPRDedAll = fields.Integer(string="Enhanced Deductions/ Allowances Claimed/ To Be Claimed")
    DataFormCS_eis_AcqIPRTotCost = fields.Integer(string="Total Qualifying Cost Incurred")
    DataFormCS_eis_ClaimCashPayout = fields.Selection([('1', 'Yes'),('2', 'No')], string="Is the company claiming cash payout under the EIS in this current YA?")
    DataFormCS_eis_ClaimDedAll = fields.Selection([('1', 'Yes'),('2', 'No')], string="Is the company claiming enhanced deductions/ allowances under the EIS in this current YA?")
    DataFormCS_eis_InnoProjDedAll = fields.Integer(string="Enhanced Deductions/ Allowances Claimed/ To Be Claimed")
    DataFormCS_eis_InnoProjTotCost = fields.Integer(string="Total Qualifying Cost Incurred (capped at $50,000)")
    DataFormCS_eis_LicensIPRDedAll = fields.Integer(string="Enhanced Deductions/ Allowances Claimed/ To Be Claimed")
    DataFormCS_eis_LicensIPRTotCost = fields.Integer(string="Total Qualifying Cost Incurred")
    DataFormCS_eis_RDSgDedAll = fields.Integer(string="Enhanced Deductions/ Allowances Claimed/ To Be Claimed")
    DataFormCS_eis_RDSgTotCost = fields.Integer(string="Total Qualifying Cost Incurred")
    DataFormCS_eis_RegIPDedAll = fields.Integer(string="Enhanced Deductions/ Allowances Claimed/ To Be Claimed")
    DataFormCS_eis_RegIPTotCost = fields.Integer(string="Total Qualifying Cost Incurred")
    DataFormCS_eis_TrainDedAll = fields.Integer(string="Enhanced Deductions/ Allowances Claimed/ To Be Claimed")
    DataFormCS_eis_TrainTotCost = fields.Integer(string="Total Qualifying Cost Incurred")
    #Jun2025
    DataFormCS_ptisDonInd = fields.Selection([('1', "Yes"), ('2', "No")], string="Is the company an approved qualifying donor making qualifying overseas donations under the Philanthropy Tax Incentive Scheme for Family Offices (PTIS)?",default='2')
    DataFormCS_foreignAssetsSaleGainLoss = fields.Float(string="Amount of gains/ losses from the sale or disposal of foreign assets during the basis period for the current YA")
    DataFormCS_foreignSourceSaleGainsRemit = fields.Float(string="Amount of the foreign-sourced sale or disposal gains remitted to Singapore during the basis period for the current YA")
    DataFormCS_foreignSourceSaleNotTax = fields.Selection([('1', "Yes"), ('2', "No")], string="Do the foreign-sourced sale or disposal gains/ losses fall under any of the scenarios where the sale or disposal of foreign assets (excluding foreign IPRs) is not subject to tax under Section 10L(8) of the ITA?", default='2')
    
    is_foreigner = fields.Boolean(string="Foreigner",compute="hide_declarantrefno")

    display_ya = fields.Selection(_get_year, string="Year of Assessment", compute="_get_display_ya", store=True, tracking=True)
    display_basisPeriodFrom = fields.Date(string="Period Start Date", tracking=True, compute="_get_display_ya", store=True)
    display_basisPeriodTo = fields.Date(string="Period End Date", tracking=True, compute="_get_display_ya", store=True)
    tax_agent_firm = fields.Char('Tax Agent Firm')
    submitted_by_thirdparty = fields.Boolean('Submitted by Third Party other than Taxpayer')
    basisPeriodFrom_display = fields.Char(string="Period Start Date", tracking=True, compute="_get_aknow_display_date",
                                          store=True)
    basisPeriodTo_display = fields.Char(string="Period End Date", tracking=True, compute="_get_aknow_display_date", store=True)
    current_accounting = fields.Boolean('Fetch Data from Metro Accounting System')
    skip_tax_conversion = fields.Boolean('Skip tax conversion')

    # my custom code
    is_value = fields.Boolean('Is Value')

    @api.depends("basisPeriodFrom","basisPeriodTo")
    def _get_aknow_display_date(self):
        for rec in self:
            rec.basisPeriodFrom_display = rec.basisPeriodFrom.strftime("%d %b %Y")
            rec.basisPeriodTo_display = rec.basisPeriodTo.strftime("%d %b %Y")

    @api.depends("is_foreigner")
    def hide_declarantrefno(self):
        for obj in self:
            if obj.env.user.partner_id.is_foreigner:
                obj.is_foreigner = True
            else:
                obj.is_foreigner = False

    @api.model
    def create(self, vals):
        if vals.get('declarantRefNo'):
            if not self.env.user.partner_id.tax_ref_iras:
                self.env.user.partner_id.tax_ref_iras = vals.get('declarantRefNo')
                self.env.user.partner_id.is_foreigner = True
        obj = super(GFormCS, self).create(vals)
        ctx = self._context or {}
        if ctx.get('bulk_import'):
            resp = obj.validate_tax_compuation()
            if not resp:
                raise ValidationError("UEN: " + str(obj.uen) + "\nKindly review once again and verify the details provided in the Tax Computation (Part B) to ensure accuracy and completeness.")
        return obj

    def validate_tax_compuation_OLD(self, during_submission=False):
        if (self.DataFormCS_ci > 0 or self.DataFormCS_ci == 0) and (self.DataFormCS_unutilCACFNorm > 0 or self.DataFormCS_unutilLossCFNorm > 0 or self.DataFormCS_unutilDonationCFNorm > 0):
            return message
        elif self.DataFormCS_unutilCACFNorm < 0 or self.DataFormCS_unutilLossCFNorm < 0 or self.DataFormCS_unutilDonationCFNorm < 0:
            return False
        elif (self.DataFormCS_ci < 0) and abs(self.DataFormCS_ci) != (
                self.DataFormCS_unutilCACFNorm +
                self.DataFormCS_unutilLossCFNorm +
                self.DataFormCS_unutilDonationCFNorm):            
            return False
        elif during_submission and (self.unutilCABFNorm != self.DataFormCS_unutilCABFNorm or \
            self.unutilLossBFNorm != self.DataFormCS_unutilLossBFNorm or \
            self.unutilDonationBFNorm != self.DataFormCS_unutilDonationBFNorm or \
            self.cyDonation != self.DataFormCS_cyDonation):
            return False
        elif (self.DataFormCS_c1_GrossRent - self.DataFormCS_c1_DedExp) != self.DataFormCS_sgRent:
            return False
        elif (self.DataFormCS_profitLossBeforeTaxation -
              self.DataFormCS_sepSrcIncome -
              self.DataFormCS_receiptNotTxAmt +
              self.DataFormCS_c1_NTDeductibleExp) != (self.DataFormCS_adjPLBefDed) or \
                (self.DataFormCS_adjPLBefDed -
                 self.DataFormCS_renoWorksExpS14Q -
                 self.DataFormCS_c1_EnhancedEISDed -
                 self.DataFormCS_c1_FurtherDed) != (self.DataFormCS_sgAdjPLAft) or \
                (self.DataFormCS_sgAdjPLAft +
                 self.DataFormCS_c1_BC -
                 self.DataFormCS_unutilCABFNorm -
                 self.DataFormCS_cyCANorm -
                 self.DataFormCS_unutilLossBFNorm +
                 self.DataFormCS_sgRent +
                 self.DataFormCS_sgIntDisc +
                 self.DataFormCS_sgOtherI) != (self.DataFormCS_totSgFI) or \
                (self.DataFormCS_totSgFI -
                 self.DataFormCS_unutilDonationBFNorm -
                 self.DataFormCS_cyDonation) != (self.DataFormCS_ci):
            return False
        return True


    def validate_tax_compuation(self, during_submission=False):
        message = ""
        if (self.DataFormCS_ci > 0 or self.DataFormCS_ci == 0) and (self.DataFormCS_unutilCACFNorm > 0 or self.DataFormCS_unutilLossCFNorm > 0 or self.DataFormCS_unutilDonationCFNorm > 0):
            if (self.DataFormCS_ci > 0 or self.DataFormCS_ci == 0) and self.DataFormCS_unutilCACFNorm > 0:
                message = (
                    "Please correct the values of <br/>'<span style='color: black; font-weight: bold'>Total Income/ Losses (after Donations)</span>'"
                    "<br/>'<span style='color: black; font-weight: bold'>Unutilised Capital Allowances carried forward.</span>'"
                )
            elif (self.DataFormCS_ci > 0 or self.DataFormCS_ci == 0) and self.DataFormCS_unutilLossCFNorm > 0:
                message = (
                    "Please correct the values of '<span style='color: black; font-weight: bold'>Total Income/ Losses (after Donations)</span>'"
                    "<br/>'<span style='color: black; font-weight: bold'>Unutilised Losses carried forward.</span>'"
                )
            elif (self.DataFormCS_ci > 0 or self.DataFormCS_ci == 0) and self.DataFormCS_unutilDonationCFNorm > 0:
                message = (
                    "Please correct the values of '<span style='color: black; font-weight: bold'>Total Income/ Losses (after Donations)</span>'"
                    "<br/>'<span style='color: black; font-weight: bold'>Unutilised Donations carried forward.</span>'"
                )
        elif self.DataFormCS_unutilCACFNorm < 0 or self.DataFormCS_unutilLossCFNorm < 0 or self.DataFormCS_unutilDonationCFNorm < 0:
            if self.DataFormCS_unutilCACFNorm < 0:
                message = (
                    "The value under the field '<span style='color: black; font-weight: bold'>Unutilised Capital Allowances carried forward</span>' "
                    "cannot be negative."
                )
            elif self.DataFormCS_unutilLossCFNorm < 0:
                message = (
                    "The value under the field '<span style='color: black; font-weight: bold'>Unutilised Losses carried forward</span>' "
                    "cannot be negative."
                )
            elif self.self.DataFormCS_unutilDonationCFNorm < 0:
                message = (
                    "The value under the field '<span style='color: black; font-weight: bold'>Unutilised Donations carried forward</span>' "
                    "cannot be negative."
                )
        elif (self.DataFormCS_ci < 0) and abs(self.DataFormCS_ci) != (
                self.DataFormCS_unutilCACFNorm +
                self.DataFormCS_unutilLossCFNorm +
                self.DataFormCS_unutilDonationCFNorm):
            message = (
                "The sum of values of the fields '<span style='color: black; font-weight: bold'>Unutilised Capital Allowances carried forward,  Unutilised Losses carried forward   &   Unutilised Donations carried forward</span>' "
                "are not equal to the value of "
                "'<span style='color: black; font-weight: bold'>Total Income/ Losses (after Donations)</span>.'"
            )
        elif during_submission and (self.unutilCABFNorm != self.DataFormCS_unutilCABFNorm or \
            self.unutilLossBFNorm != self.DataFormCS_unutilLossBFNorm or \
            self.unutilDonationBFNorm != self.DataFormCS_unutilDonationBFNorm or \
            self.cyDonation != self.DataFormCS_cyDonation):
            if self.unutilCABFNorm != self.DataFormCS_unutilCABFNorm:
                message = (
                    "The value in the field '<span style='color: black; font-weight: bold'>Unutilised Capital Allowances brought forward</span>' "
                    "does not match the corresponding value under the "
                    "'<span style='color: black; font-weight: bold'>Tax Prefill</span>' "
                    "tab. <br/>Ensure that the values fetched from IRAS and displayed under the Tax Prefill tab are accurately reflected and consistently applied in this section."
                )
                # message = "The field 'Unutilised Capital Allowances brought forward' is not equal to the value under 'Tax Prefill' tab."
            elif self.unutilLossBFNorm != self.DataFormCS_unutilLossBFNorm:
                message = (
                    "The value in the field '<span style='color: black; font-weight: bold'>Unutilised Losses brought forward</span>' "
                    "does not match the corresponding value under the "
                    "'<span style='color: black; font-weight: bold'>Tax Prefill</span>' "
                    "tab. <br/>Ensure that the values fetched from IRAS and displayed under the Tax Prefill tab are accurately reflected and consistently applied in this section."
                )
            elif self.unutilDonationBFNorm != self.DataFormCS_unutilDonationBFNorm:
                message = (
                    "The value in the field '<span style='color: black; font-weight: bold'>Unutilised Donations brought forward</span>' "
                    "does not match the corresponding value under the "
                    "'<span style='color: black; font-weight: bold'>Tax Prefill</span>' "
                    "tab. <br/>Ensure that the values fetched from IRAS and displayed under the Tax Prefill tab are accurately reflected and consistently applied in this section."
                )
            elif self.cyDonation != self.DataFormCS_cyDonation:
                message = (
                    "The value in the field '<span style='color: black; font-weight: bold'>Current Year Donations</span>' "
                    "does not match the corresponding value under the "
                    "'<span style='color: black; font-weight: bold'>Tax Prefill</span>' "
                    "tab. <br/>Ensure that the values fetched from IRAS and displayed under the Tax Prefill tab are accurately reflected and consistently applied in this section."
                )
        elif (self.DataFormCS_c1_GrossRent - self.DataFormCS_c1_DedExp) != self.DataFormCS_sgRent:
            message = (
                "The '<span style='color: black; font-weight: bold'>Net Rental Income</span>' "
                "value is invalid. Please review the entries for "
                "'<span style='color: black; font-weight: bold'>Gross Rental Income</span>' "
                " & "
                "'<span style='color: black; font-weight: bold'>Deductible Expenses</span>' to ensure accuracy."
            )
        elif (self.DataFormCS_profitLossBeforeTaxation -
              self.DataFormCS_sepSrcIncome -
              self.DataFormCS_receiptNotTxAmt +
              self.DataFormCS_c1_NTDeductibleExp) != (self.DataFormCS_adjPLBefDed) or \
                (self.DataFormCS_adjPLBefDed -
                 self.DataFormCS_renoWorksExpS14Q -
                 self.DataFormCS_c1_EnhancedEISDed -
                 self.DataFormCS_c1_FurtherDed) != (self.DataFormCS_sgAdjPLAft) or \
                (self.DataFormCS_sgAdjPLAft +
                 self.DataFormCS_c1_BC -
                 self.DataFormCS_unutilCABFNorm -
                 self.DataFormCS_cyCANorm -
                 self.DataFormCS_unutilLossBFNorm +
                 self.DataFormCS_sgRent +
                 self.DataFormCS_sgIntDisc +
                 self.DataFormCS_sgOtherI) != (self.DataFormCS_totSgFI) or \
                (self.DataFormCS_totSgFI -
                 self.DataFormCS_unutilDonationBFNorm -
                 self.DataFormCS_cyDonation) != (self.DataFormCS_ci):
            if (self.DataFormCS_profitLossBeforeTaxation -
              self.DataFormCS_sepSrcIncome -
              self.DataFormCS_receiptNotTxAmt +
              self.DataFormCS_c1_NTDeductibleExp) != (self.DataFormCS_adjPLBefDed):
                message = (
                    "The value for '<span style='color: black; font-weight: bold'>Adjusted Profit/ Loss before Other Deductions</span>' "
                    "value is invalid. Kindly review and verify the entered details."
                )
            elif (self.DataFormCS_adjPLBefDed -
                 self.DataFormCS_renoWorksExpS14Q -
                 self.DataFormCS_c1_EnhancedEISDed -
                 self.DataFormCS_c1_FurtherDed) != (self.DataFormCS_sgAdjPLAft):
                message = (
                    "The value for '<span style='color: black; font-weight: bold'>Adjusted Profit/ Loss before Capital Allowances</span>' "
                    "value is invalid. Kindly review and verify the entered details."
                )
            elif (self.DataFormCS_sgAdjPLAft +
                 self.DataFormCS_c1_BC -
                 self.DataFormCS_unutilCABFNorm -
                 self.DataFormCS_cyCANorm -
                 self.DataFormCS_unutilLossBFNorm +
                 self.DataFormCS_sgRent +
                 self.DataFormCS_sgIntDisc +
                 self.DataFormCS_sgOtherI) != (self.DataFormCS_totSgFI):
                message = (
                    "The value for '<span style='color: black; font-weight: bold'>Total Income/ Losses (before Donations)</span>' "
                    "value is invalid. Kindly review and verify the entered details."
                )
            elif (self.DataFormCS_totSgFI -
                 self.DataFormCS_unutilDonationBFNorm -
                 self.DataFormCS_cyDonation) != (self.DataFormCS_ci):
                message = (
                    "The value for '<span style='color: black; font-weight: bold'>Total Income/ Losses (after Donations)</span>' "
                    "value is invalid. Kindly review and verify the entered details."
                )
        return message

    def action_perform_corppass(self):
        if self.state == 'cs_submission':
            message = self.validate_tax_compuation(during_submission=True)
            if message:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Review',
                    'res_model': 'formcs.partb.check',
                    'view_mode': 'form',
                    'view_id': self.env.ref('metroerp_iras.formcs_partb_data_check_view').id,
                    'target': 'new',
                    'context': {
                        'default_active_id': self.id,
                        'default_form_cs_id': self.id,
                        'default_message': message
                    },
                }

        print("\n\naction_perform_corppass() >>>>>>>")
        config_params = self.env['ir.config_parameter'].sudo()
        headers = {
            'Content-type': 'application/json',
            'X-IBM-Client-Id': config_params.get_param('iras_apikey'),
            'X-IBM-Client-Secret': config_params.get_param('iras_apisecret'),
            'Accept': 'application/json',
        }
        print("headers ===",headers)        
        
        if self.state == 'pre_fill':
            scope = 'CITPrefillCS'
        else:
            scope = 'CITFormCSSub'

        if self.env.user.has_group('metroerp_iras.iras_tax_agent_group'):
            tax_agent = True
        else:
            tax_agent = False            
        print("tax_agent ===",tax_agent)

        state = ''.join(random.choices(string.ascii_lowercase + string.digits, k=15))
        state += '_' + str(config_params.get_param('web.base.url')) + '_' + str(self.id) + '_' + scope + '_' + str(self.env.ref('metroerp_iras.form_cs_action').id)
        print("state ===",state)

        params = {
            'scope': scope,
            'callback_url': config_params.get_param('corppass_callback_url'),
            'tax_agent': tax_agent,
            'state': state
        }
        print("params ===",params)

        url = config_params.get_param('corppass_auth_endpoint')
        url = "{}?scope={}&callback_url={}&tax_agent={}&state={}".format(url, params['scope'], params['callback_url'], str(params['tax_agent']).lower(), params['state'])
        # response = requests.request("GET", url, params=params, headers=headers)
        response = requests.request("GET", url, headers=headers)

        res_data = json.loads(response.text)
        print("response > res_data ===",res_data)

        if res_data.get('httpCode'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': res_data.get('httpMessage') and res_data['httpMessage'] or 'Error',
                    'message': json.dumps(res_data),
                    'sticky': False,
                }
            }
        elif res_data.get('returnCode'):
            if res_data['returnCode'] in ["20","30"]:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': res_data['info'].get('message') and res_data['info']['message'] or ('Error with returnCode' + res_data['returnCode']),
                        'message': json.dumps(res_data),
                        'sticky': False,
                    }
                }

        if res_data.get('returnCode') == "10":
            self.write({
                'singpass_url': res_data['data']['url'],
                'state_identifier': state})
            return {
                'type': 'ir.actions.act_url',
                'target': 'blank',
                'url': res_data['data']['url'],
            }
        # Corppass Authentication Code ends

    def autosubmit_pre_fill(self):
        print("autosubmit_pre_fill() ...")
        ctx = self._context
        config_params = self.env['ir.config_parameter'].sudo()
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'X-IBM-Client-Id': config_params.get_param('iras_apikey'),
            'X-IBM-Client-Secret': config_params.get_param('iras_apisecret'),
            'access_token': self.access_token
        }
        print("headers ===",headers)
        payload = {
             "filingInfo": {
                 "uen": self.uen,
                 "uenType": int(self.uenType),
                 "ya": self.ya,
                 "declarantRefNo": self.declarantRefNo if self.declarantRefNo else ""
             },
             "data": {
                 "basisPeriodFrom": self.basisPeriodFrom.strftime("%Y-%m-%d"),
                 "basisPeriodTo": self.basisPeriodTo.strftime("%Y-%m-%d"),
                 "fsPrep": int(self.fsPrep) if self.fsPrep else "",
                 "firstFYE": self.firstFYE.strftime("%Y-%m-%d") if self.firstFYE else "",
                 "prevFYE": self.prevFYE.strftime("%Y-%m-%d") if self.prevFYE else ""
             }
        }
        print("payload ===",payload)
        url = config_params.get_param('cit_prefill_endpoint')
        print("url ===",url)
        self.message_post(body=_("Prefill (Corppass) Request JSON:<br> %s") % (json.dumps(payload)))
        response = requests.request("POST", url, data=json.dumps(payload), headers=headers, allow_redirects=False)
        res_data = json.loads(response.text)
        print("res_data ===",res_data)
        if res_data.get('returnCode'):
            if res_data['returnCode'] == '10':
                self.message_post(body=_("Action performed successfully.<br>Prefill (Corppass) Response JSON:<br>%s") % (json.dumps(res_data)))
                if self.skip_tax_conversion:
                    state = 'cs_submission'
                else:
                    state = 'conversion'
                self.write({
                    'cyDonation':res_data["data"]["cyDonation"],
                    'unutilCABFNorm':res_data["data"]["unutilCABFNorm"],
                    'unutilDonationBFNorm':res_data["data"]["unutilDonationBFNorm"],
                    'unutilLossBFNorm':res_data["data"]["unutilLossBFNorm"],
                    'state': state
                })
                if not ctx.get('force_submit'):
                    return {'message': 'Prefill (Corppass) successful'}
                else:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': ('Action'),
                            'message': 'Prefill (Corppass) successful',
                            'sticky': False,
                        }
                    }
            else:
                self.message_post(body=_("Prefill (Corppass) failure.<br>Prefill (Corppass) Response JSON:<br>%s") % (json.dumps(res_data)))
                if not ctx.get('force_submit'):
                    message = ('Prefill (Corppass) failure with returnCode: ' + str(res_data['returnCode']))
                    if res_data.get('info') and res_data['info'].get('message'):
                        message += '<br>' + res_data['info'].get('message')
                    return {'message': message}
                else:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': ('Prefill (Corppass) failure with returnCode: ' + str(res_data['returnCode'])),
                            'message': json.dumps(res_data),
                            'sticky': False,
                        }
                    }
        else:
            self.message_post(body="Error arised.\n" + json.dumps(res_data))
            if not ctx.get('force_submit'):
                return {'message': res_data.get('httpMessage') and res_data['httpMessage'] or 'Error'}
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': res_data.get('httpMessage') and res_data['httpMessage'] or 'Error',
                        'message': json.dumps(res_data),
                        'sticky': False,
                    }
                }

    def action_cit_conversion(self):
        if self.is_fetched ==False and self.current_accounting:
            raise ValidationError("Please click on 'Fetch' before you apply this action.")
        config_params = self.env['ir.config_parameter'].sudo()
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'X-IBM-Client-Id': config_params.get_param('iras_apikey'),
            'X-IBM-Client-Secret': config_params.get_param('iras_apisecret')
        }
        nhcce_lst,nhop_lst,nhpl_lst,hp_lst,rrs_lst,nhcce_dict,nhop_dict,nhpl_dict,hp_dict = [],[],[],[],[],{},{},{},{}
        for nhcce in self.nonHPCompCommEquipment_ids:
        #Jun2025
            nhcce_dict = {
                "descriptionEachAsset": nhcce.descriptionEachAsset,
                "yaOfPurchaseEachAsset": nhcce.yaOfPurchaseEachAsset,
                "costEachAsset": nhcce.costEachAsset,
                "salesProceedEachAsset": nhcce.salesProceedEachAsset if nhcce.salesProceedEachAsset else "",
                "yaOfDisposalEachAsset": nhcce.yaOfDisposalEachAsset if nhcce.yaOfDisposalEachAsset else ""
            }
            nhcce_lst.append(nhcce_dict)
        for nhop in self.nonHpOtherPPE_ids:
            nhop_dict = {
                "descriptionEachAsset": nhop.descriptionEachAsset,
                "yaOfPurchaseEachAsset": nhop.yaOfPurchaseEachAsset,
                "costEachAsset": nhop.costEachAsset,
                "salesProceedEachAsset": nhop.salesProceedEachAsset if nhop.salesProceedEachAsset else "",
                "yaOfDisposalEachAsset": nhop.yaOfDisposalEachAsset if nhop.yaOfDisposalEachAsset else ""
            }
            nhop_lst.append(nhop_dict)
        for nhpl in self.nonHpOtherPPElowvalueasset_ids:
            nhpl_dict = {
                "descriptionEachAsset": nhpl.descriptionEachAsset,
                "yaOfPurchaseEachAsset": nhpl.yaOfPurchaseEachAsset,
                "costEachAsset": nhpl.costEachAsset,
                "salesProceedEachAsset": nhpl.salesProceedEachAsset if nhpl.salesProceedEachAsset else "",
                "yaOfDisposalEachAsset": nhpl.yaOfDisposalEachAsset if nhpl.yaOfDisposalEachAsset else ""
            }
            nhpl_lst.append(nhpl_dict)
        for hp in self.hpOtherPPE_ids:
            hp_dict = {
                "descriptionEachAsset": hp.descriptionEachAsset,
                "yaOfPurchaseEachAsset": hp.yaOfPurchaseEachAsset,
                "costEachAsset": hp.costEachAsset,
                "salesProceedEachAsset": hp.salesProceedEachAsset if hp.salesProceedEachAsset else "",
                "yaOfDisposalEachAsset": hp.yaOfDisposalEachAsset if hp.yaOfDisposalEachAsset else "",
                "depositOrPrincipalExcludingInterestIncludingDownpaymentEachAsset": hp.depositOrPrincipalExcluding,
                "depositOrPrincipalMinus1ExcludingInterestIncludingDownpaymentEachAsset": hp.depositOrPrincipalMinus1,
                "depositOrPrincipalMinus2ExcludingInterestIncludingDownpaymentEachAsset": hp.depositOrPrincipalMinus2,
                "totalPrincipalTillDateEachAsset": hp.totalPrincipalTillDateEachAsset
            }
            hp_lst.append(hp_dict)

        leaseholdImprovementsAndRenoCostIncurredInCurrentYA, leaseholdImprovementsAndRenoCostIncurredInYAMinus1, leaseholdImprovementsAndRenoCostIncurredInYAMinus2, leaseholdImprovementsAndRenoCostIncurredInYAMinus3, leaseholdImprovementsAndRenoCostIncurredInYAMinus4 = 0,0,0,0,0
        for rrs in self.renovation_refurbishment_sch_ids:
            if rrs.tech_name == 'leaseholdImprovementsAndRenoCostIncurredInCurrentYA':
                leaseholdImprovementsAndRenoCostIncurredInCurrentYA = rrs.leaseholdImprovementsAndRenoCostIncurred
            elif rrs.tech_name == 'leaseholdImprovementsAndRenoCostIncurredInYAMinus1':
                leaseholdImprovementsAndRenoCostIncurredInYAMinus1 = rrs.leaseholdImprovementsAndRenoCostIncurred
            elif rrs.tech_name == 'leaseholdImprovementsAndRenoCostIncurredInYAMinus2':
                leaseholdImprovementsAndRenoCostIncurredInYAMinus2 = rrs.leaseholdImprovementsAndRenoCostIncurred
            elif rrs.tech_name == 'leaseholdImprovementsAndRenoCostIncurredInYAMinus3':
                leaseholdImprovementsAndRenoCostIncurredInYAMinus3 = rrs.leaseholdImprovementsAndRenoCostIncurred
            elif rrs.tech_name == 'leaseholdImprovementsAndRenoCostIncurredInYAMinus4':
                leaseholdImprovementsAndRenoCostIncurredInYAMinus4 = rrs.leaseholdImprovementsAndRenoCostIncurred


        payload = {
            "filingInfo": {"ya": self.ya},
            "declaration": {
                "isQualifiedToUseConvFormCS": self.isQualifiedToUseConvFormCS
            },
        #Jun2025
            "data": {
                "totalRevenue": int(self.totalRevenue),
                "sgIntDisc": int(self.sgIntDisc),
                "oneTierTaxDividendIncome": int(self.oneTierTaxDividendIncome),
                "c1_GrossRent": int(self.c1_GrossRent),
                "sgOtherI": int(self.sgOtherI),
                "otherNonTaxableIncome": int(self.otherNonTaxableIncome),
                "totalOtherIncome": int(self.totalOtherIncome),
                "costOfGoodsSold": int(self.costOfGoodsSold),
                "bankCharges": int(self.bankCharges),
                "commissionOther": int(self.commissionOther),
                "depreciationExpense": int(self.depreciationExpense),
                "directorsFees": int(self.directorsFees),
                "directorsRemunerationExcludingDirectorsFees": int(self.directorsRemunerationExcludingDirectorsFees),
                "donations": int(self.donations),
                "cpfContribution": int(self.cpfContribution),
                "c1_EntertainExp": int(self.c1_EntertainExp),
                "commissionExpRentalIncome": int(self.commissionExpRentalIncome),
                "insuranceExpRentalIncome": int(self.insuranceExpRentalIncome),
                "interestExpRentalIncome": int(self.interestExpRentalIncome),
                "propertyTaxExpRentalIncome": int(self.propertyTaxExpRentalIncome),
                "repairMaintenanceExpRentalIncome": int(self.repairMaintenanceExpRentalIncome),
                "otherExpRentalIncome": int(self.otherExpRentalIncome),
                "fixedAssetsExpdOff": int(self.fixedAssetsExpdOff),
                "amortisationExpense": int(self.amortisationExpense),
                "insuranceExpOther": int(self.insuranceExpOther),
                "interestExpOther": int(self.interestExpOther),
                "impairmentLossReversalOfImpairmentLossForBadDebts": int(self.impairmentLossReversalOfImpairmentLossForBadDebts),
                "medicalExpIncludingMedicalInsurance": int(self.medicalExpIncludingMedicalInsurance),
                "netGainsOrLossesOnDisposalOfPPE": int(self.netGainsOrLossesOnDisposalOfPPE),
                "netGainsOrLossesOnForex": int(self.netGainsOrLossesOnForex),
                "netGainsOrLossesOnOtherItems": int(self.netGainsOrLossesOnOtherItems),
                "miscExp": int(self.miscExp),
                "otherPrivateOrCapitalExp": int(self.otherPrivateOrCapitalExp),
                "otherFinanceCost": int(self.otherFinanceCost),
                "penaltiesOrFine": int(self.penaltiesOrFine),
                "professionalFees": int(self.professionalFees),
                "propertyTaxOther": int(self.propertyTaxOther),
                "rentExp": int(self.rentExp),
                "repairMaintenanceExcludingUpkeepOfPrivateVehiclesAndExpRentalIncome": int(self.repairMaintenanceExcludingUpkeepOfPrivateVehiclesAndExp),
                "repairsMaintenanceForPrivateVehicles": int(self.repairsMaintenanceForPrivateVehicles),
                "salesAndMarketingExpense": int(self.salesAndMarketingExpense),
                "skillsDevelopmentForeignWorkerLevy": int(self.skillsDevelopmentForeignWorkerLevy),
                "staffRemunerationOtherThanDirectorsRemuneration": int(self.staffRemunerationOtherThanDirectorsRemuneration),
                "staffWelfare": int(self.staffWelfare),
                "telecommunicationOrUtilities": int(self.telecommunicationOrUtilities),
                "training": int(self.training),
                "c1_TransportExp": int(self.c1_TransportExp),
                "upkeepNonPrivateVehicles": int(self.upkeepNonPrivateVehicles),
                "upkeepPrivateVehicles": int(self.upkeepPrivateVehicles),
                "profitLossBeforeTaxation": int(self.profitLossBeforeTaxation),
                "c1_FurtherDed": int(self.c1_FurtherDed),
                "unutilCABFNorm": int(self.unutilCABFNorm),
                "unutilLossBFNorm": int(self.unutilLossBFNorm),
                "unutilDonationBFNorm": int(self.unutilDonationBFNorm),
                "cyDonation": int(self.cyDonation),
                "fullTxX": self.fullTxX,
                "uCALDChangePrinAct": int(self.uCALDChangePrinAct),
                "sholderChange": self.sholderChange,
                "unutilCALDClaimS23S37": int(self.unutilCALDClaimS23S37),
                "expRD": int(self.expRD),
                "expRDSG": int(self.expRDSG),
                "enhanceDeductRD": int(self.enhanceDeductRD),
                "appStockConvAsset": self.appStockConvAsset,
                "tradeReceivables": int(self.tradeReceivables),
                "inventories": int(self.inventories),
                "theLeaseholdImprovementsAndRenoCostDoNotRequireTheApprovalOfCOBC": self.theLeaseholdImprovementsAndRenoCost or "",
                "firstYAInWhichS14QDeductionClaimed": self.firstYAInWhichS14QDeductionClaimed or "",
                "leaseholdImprovementsAndRenoCostIncurredInYAMinus4": int(leaseholdImprovementsAndRenoCostIncurredInYAMinus4),
                "leaseholdImprovementsAndRenoCostIncurredInYAMinus3": int(leaseholdImprovementsAndRenoCostIncurredInYAMinus3),
                "leaseholdImprovementsAndRenoCostIncurredInYAMinus2": int(leaseholdImprovementsAndRenoCostIncurredInYAMinus2),
                "leaseholdImprovementsAndRenoCostIncurredInYAMinus1": int(leaseholdImprovementsAndRenoCostIncurredInYAMinus1),
                "leaseholdImprovementsAndRenoCostIncurredInCurrentYA": int(leaseholdImprovementsAndRenoCostIncurredInCurrentYA),
                "iaAaPriorSeamlessFiling": int(self.iaAaPriorSeamlessFiling),
                "baPriorSeamlessFiling": int(self.baPriorSeamlessFiling),
                "bcPriorSeamlessFiling": int(self.bcPriorSeamlessFiling),
                "c1_EnhancedEISDed": int(self.c1_EnhancedEISDed),
                "enhancedEISCA": int(self.enhancedEISCA),
                "eis_ClaimCashPayout": self.eis_ClaimCashPayout,
                "eis_ClaimDedAll": self.eis_ClaimDedAll,
                "eis_TrainTotCost": int(self.eis_TrainTotCost),
                "eis_TrainDedAll": int(self.eis_TrainDedAll),
                "eis_InnoProjTotCost": int(self.eis_InnoProjTotCost),
                "eis_InnoProjDedAll": int(self.eis_InnoProjDedAll),
                "eis_AcqIPRTotCost": int(self.eis_AcqIPRTotCost),
                "eis_AcqIPRDedAll": int(self.eis_AcqIPRDedAll),
                "eis_LicensIPRTotCost": int(self.eis_LicensIPRTotCost),
                "eis_LicensIPRDedAll": int(self.eis_LicensIPRDedAll),
                "eis_RegIPTotCost": int(self.eis_RegIPTotCost),
                "eis_RegIPDedAll": int(self.eis_RegIPDedAll),
                "eis_RDSgTotCost": int(self.eis_RDSgTotCost),
                "eis_RDSgDedAll": int(self.eis_RDSgDedAll),
                "ptisDonInd": int(self.ptisDonInd),
                "foreignAssetsSaleGainLoss": int(self.foreignAssetsSaleGainLoss),
                "foreignSourceSaleGainsRemit": int(self.foreignSourceSaleGainsRemit),
                "foreignSourceSaleNotTax": int(self.foreignSourceSaleNotTax)
            },
            "nonHPCompCommEquipment": nhcce_lst,
            "nonHpOtherPPE": nhop_lst,
            "nonHpOtherPPE_LowValueAsset": nhpl_lst,
            "hpOtherPPE": hp_lst
        }

        print("\njson.dumps(payload) ==",json.dumps(payload))
        self.message_post(body=_("CIT Conversion Request JSON:<br> %s") % (json.dumps(payload)))

        url = config_params.get_param('cit_conversion_endpoint')
        print("url ====",url)
        response = requests.request("POST", url, data=json.dumps(payload), headers=headers, allow_redirects=False)
        res_data = json.loads(response.text)
        print("res_data ===",res_data)
        if res_data.get('returnCode'):
            if res_data['returnCode'] == '10':
                self.message_post(body=_("Action performed successfully.<br>CIT Conversion Response JSON:<br>%s") % (json.dumps(res_data)))
                #Jun2025
                vals = {
                    'DataMedExpSch_cpfContribution': res_data['data'].get('DataMedExpSch') and res_data['data']['DataMedExpSch'].get('cpfContribution'),
                    'DataMedExpSch_directorsRemExclDirectorsFees': res_data['data'].get('DataMedExpSch') and res_data['data']['DataMedExpSch'].get('directorsRemunerationExcludingDirectorsFees'),
                    'DataMedExpSch_medicalExpDisallowed': res_data['data'].get('DataMedExpSch') and res_data['data']['DataMedExpSch'].get('medicalExpDisallowed'),
                    'DataMedExpSch_medicalExpIncludingMedicalInsurance': res_data['data'].get('DataMedExpSch') and res_data['data']['DataMedExpSch'].get('medicalExpIncludingMedicalInsurance'),
                    'DataMedExpSch_onePercentOfTotalRemuneration': res_data['data'].get('DataMedExpSch') and res_data['data']['DataMedExpSch'].get('onePercentOfTotalRemuneration'),
                    'DataMedExpSch_staffRemOtherThanDirectorsRem': res_data['data'].get('DataMedExpSch') and res_data['data']['DataMedExpSch'].get('staffRemunerationOtherThanDirectorsRemuneration'),
                    'DataMedExpSch_totalRemuneration': res_data['data'].get('DataMedExpSch') and res_data['data']['DataMedExpSch'].get('totalRemuneration'),

                    'DataRentalSch_c1_GrossRent': res_data['data'].get('DataRentalSch') and res_data['data']['DataRentalSch'].get('c1_GrossRent'),
                    'DataRentalSch_commissionExpRentalIncome': res_data['data'].get('DataRentalSch') and res_data['data']['DataRentalSch'].get('commissionExpRentalIncome'),
                    'DataRentalSch_insuranceExpRentalIncome': res_data['data'].get('DataRentalSch') and res_data['data']['DataRentalSch'].get('insuranceExpRentalIncome'),
                    'DataRentalSch_interestExpRentalIncome': res_data['data'].get('DataRentalSch') and res_data['data']['DataRentalSch'].get('interestExpRentalIncome'),
                    'DataRentalSch_otherExpRentalIncome': res_data['data'].get('DataRentalSch') and res_data['data']['DataRentalSch'].get('otherExpRentalIncome'),
                    'DataRentalSch_propertyTaxExpRentalIncome': res_data['data'].get('DataRentalSch') and res_data['data']['DataRentalSch'].get('propertyTaxExpRentalIncome'),
                    'DataRentalSch_repairMaintenanceExpRentalIncome': res_data['data'].get('DataRentalSch') and res_data['data']['DataRentalSch'].get('repairMaintenanceExpRentalIncome'),
                    'DataRentalSch_sgRent': res_data['data'].get('DataRentalSch') and res_data['data']['DataRentalSch'].get('sgRent'),

                    'DataTCSch_adjPLBefDed': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('adjPLBefDed'),
                    'DataTCSch_adjustedProfitOrLossAfterCapAllowAndUnutilisedLosBF': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('adjustedProfitOrLossAfterCapitalAllowanceAndUnutilisedLossesBF'),
                    'DataTCSch_amortisationExpense': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('amortisationExpense'),
                    'DataTCSch_balancingAllowancesNonHPandHP': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('balancingAllowancesNonHPandHP'),
                    'DataTCSch_c1_BC': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('c1_BC'),
                    'DataTCSch_c1_FurtherDed': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('c1_FurtherDed'),
                    'DataTCSch_c1_NTDeductibleExp': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('c1_NTDeductibleExp'),
                    'DataTCSch_c1_GrossRent': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('c1_GrossRent'),
                    'DataTCSch_chargeableIncomeAftTaxExemptAmt': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('chargeableIncomeAftTaxExemptAmt'),
                    'DataTCSch_chargeableIncomeBefTaxExemptAmt': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('chargeableIncomeBefTaxExemptAmt'),
                    'DataTCSch_commissionExpRentalIncome': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('commissionExpRentalIncome'),
                    'DataTCSch_currentYearCapitalAllowancesNonHPAndHP': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('currentYearCapitalAllowancesNonHPAndHP'),
                    'DataTCSch_cyDonation': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('cyDonation'),
                    'DataTCSch_depreciationExpense': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('depreciationExpense'),
                    'DataTCSch_donations': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('donations'),
                    'DataTCSch_fixedAssetsExpdOff': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('fixedAssetsExpdOff'),
                    'DataTCSch_insuranceExpRentalIncome': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('insuranceExpRentalIncome'),
                    'DataTCSch_interestExpRentalIncome': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('interestExpRentalIncome'),
                    'DataTCSch_medicalExpDisallowed': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('medicalExpDisallowed'),
                    'DataTCSch_netGainsOrLossesOnDisposalOfPPE': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('netGainsOrLossesOnDisposalOfPPE'),
                    'DataTCSch_netGainsOrLossesOnOtherItems': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('netGainsOrLossesOnOtherItems'),
                    'DataTCSch_otherPrivateOrCapitalExp': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('otherPrivateOrCapitalExp'),
                    'DataTCSch_netTaxPayable': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('netTaxPayable'),
                    'netTaxPayable': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('netTaxPayable'),
                    'DataTCSch_oneTierTaxDividendIncome': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('oneTierTaxDividendIncome'),
                    'DataTCSch_otherNonTaxableIncome': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('otherNonTaxableIncome'),
                    'DataTCSch_otherExpRentalIncome': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('otherExpRentalIncome'),
                    'DataTCSch_penaltiesOrFine': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('penaltiesOrFine'),
                    'DataTCSch_profitLossBeforeTaxation': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('profitLossBeforeTaxation'),
                    'DataTCSch_propertyTaxExpRentalIncome': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('propertyTaxExpRentalIncome'),
                    'DataTCSch_repairMaintenanceExpRentalIncome': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('repairMaintenanceExpRentalIncome'),
                    'DataTCSch_sgOtherI': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('sgOtherI'),
                    'DataTCSch_sgIntDisc': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('sgIntDisc'),
                    'DataTCSch_sepSrcIncome': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('sepSrcIncome'),
                    'DataTCSch_receiptNotTxAmt': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('receiptNotTxAmt'),
                    'DataTCSch_repairsMaintenanceForPrivateVehicles': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('repairsMaintenanceForPrivateVehicles'),
                    'DataTCSch_upkeepPrivateVehicles': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('upkeepPrivateVehicles'),
                    'DataTCSch_renoWorksExpS14Q': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('renoWorksExpS14Q'),
                    'DataTCSch_sgAdjPLAft': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('sgAdjPLAft'),
                    'DataTCSch_totSgFI': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('totSgFI'),
                    'DataTCSch_unutilCABFNorm': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('unutilCABFNorm'),
                    'DataTCSch_unutilDonationBFNorm': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('unutilDonationBFNorm'),
                    'DataTCSch_taxPayable': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('taxPayable'),
                    'DataTCSch_taxRebate': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('taxRebate'),
                    'DataTCSch_unutilCACFNorm': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('unutilCACFNorm'),
                    'DataTCSch_unutilLossCFNorm': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('unutilLossCFNorm'),
                    'DataTCSch_unutilDonationCFNorm': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('unutilDonationCFNorm'),
                    'DataTCSch_taxExemptAmount': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('taxExemptAmount'),
                    'DataTCSch_unutilLossBFNorm': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('unutilLossBFNorm'),
                    'DataTCSch_sgRent': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('sgRent'),
                    'DataTCSch_c1_EnhancedEISDed': res_data['data'].get('DataTCSch') and res_data['data']['DataTCSch'].get('sgRent'),

                    'DataFormCS_adjPLBefDed': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('adjPLBefDed'),
                    'DataFormCS_c1_BC': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('c1_BC'),
                    'DataFormCS_c1_DedExp': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('c1_DedExp'),
                    'DataFormCS_c1_EntertainExp': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('c1_EntertainExp'), 
                    'DataFormCS_c1_FurtherDed': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('c1_FurtherDed'),
                    'DataFormCS_c1_GrossRent': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('c1_GrossRent'),
                    'DataFormCS_c1_NTDeductibleExp': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('c1_NTDeductibleExp'),
                    'DataFormCS_c1_TransportExp': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('c1_TransportExp'),
                    'DataFormCS_ci': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('ci'),
                    'DataFormCS_cyCANorm': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('cyCANorm'),
                    'DataFormCS_cyDonation': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('cyDonation'),
                    'DataFormCS_directorFee': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('directorFee'),
                    'DataFormCS_enhanceDeductRD': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('enhanceDeductRD'),
                    'DataFormCS_expRD': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('expRD'),
                    'DataFormCS_expRDSG': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('expRDSG'),
                    'DataFormCS_fullTxX': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('fullTxX'),
                    'DataFormCS_grossPL': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('grossPL'),
                    'DataFormCS_inventories': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('inventories'),
                    'DataFormCS_medicalExp': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('medicalExp'),
                    'DataFormCS_profitLossBeforeTaxation': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('profitLossBeforeTaxation'),
                    'DataFormCS_receiptNotTxAmt': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('receiptNotTxAmt'),
                    'DataFormCS_renoWorksExpS14Q': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('renoWorksExpS14Q'),
                    'DataFormCS_sepSrcIncome': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('sepSrcIncome'),
                    'DataFormCS_sgIntDisc': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('sgIntDisc'),
                    'DataFormCS_sgOtherI': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('sgOtherI'),
                    'DataFormCS_sgRent': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('sgRent'),
                    'DataFormCS_sholderChange': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('sholderChange'),
                    'DataFormCS_totRemuneration': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('totRemuneration'),
                    'DataFormCS_totSgFI': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('totSgFI'),
                    'DataFormCS_sgAdjPLAft': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('sgAdjPLAft'),
                    'DataFormCS_totalRevenue': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('totalRevenue'),
                    'DataFormCS_tradeReceivables': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('tradeReceivables'),
                    'DataFormCS_uCALDChangePrinAct': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('uCALDChangePrinAct'),
                    'DataFormCS_unutilLossBFNorm': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('unutilLossBFNorm'),
                    'DataFormCS_unutilCABFNorm': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('unutilCABFNorm'),
                    'DataFormCS_unutilCACFNorm': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('unutilCACFNorm'),
                    'DataFormCS_unutilLossCFNorm': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('unutilLossCFNorm'),
                    'DataFormCS_unutilDonationCFNorm': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('unutilDonationCFNorm'),
                    'DataFormCS_unutilDonationBFNorm': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('unutilDonationBFNorm'),
                    'DataFormCS_unutilCALDClaimS23S37': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('unutilCALDClaimS23S37'),
                    'DataFormCS_appStockConvAsset': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('appStockConvAsset'),
                    'DataFormCS_c1_EnhancedEISDed': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('c1_EnhancedEISDed'),
                    # 'DataFormCS_eis_ClaimCashPayout': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('eis_ClaimCashPayout'),
                    # 'DataFormCS_eis_ClaimDedAll': 
                    # 'DataFormCS_eis_TrainTotCost': 
                    # 'DataFormCS_eis_TrainDedAll':
                    # "eis_InnoProjTotCost":
                    # "eis_InnoProjDedAll":
                    # "eis_AcqIPRTotCost":
                    # "eis_AcqIPRDedAll": 
                    # "eis_LicensIPRTotCost": 
                    # "eis_LicensIPRDedAll": 
                    # "eis_RegIPTotCost": 
                    # "eis_RegIPDedAll": 
                    # "eis_RDSgTotCost": 
                    # "eis_RDSgDedAll": 
                    'DataFormCS_ptisDonInd': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('ptisDonInd'),
                    'DataFormCS_foreignSourceSaleNotTax': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('foreignSourceSaleNotTax'),
                    'DataFormCS_foreignAssetsSaleGainLoss': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('foreignAssetsSaleGainLoss'),
                    'DataFormCS_foreignSourceSaleGainsRemit': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('foreignSourceSaleGainsRemit'),

                    'adjPLBefDed': res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('adjPLBefDed'),
                    "c1_BC": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('c1_BC'),
                    "c1_DedExp": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('c1_DedExp'),
                    "c1_EntertainExp": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('c1_EntertainExp'),
                    "c1_FurtherDed": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('c1_FurtherDed'),
                    "c1_GrossRent": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('c1_GrossRent'),
                    "c1_NTDeductibleExp": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('c1_NTDeductibleExp'),
                    "c1_TransportExp": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('c1_TransportExp'),
                    "ci": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('ci'),
                    "cyCANorm": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('cyCANorm'),
                    "cyDonation": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('cyDonation'),
                    "directorFee": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('directorFee'),
                    "enhanceDeductRD": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('enhanceDeductRD'),
                    "expRD": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('expRD'),
                    "expRDSG": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('expRDSG'),
                    "fullTxX": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('fullTxX'),
                    "grossPL": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('grossPL'),
                    "inventories": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('inventories'),
                    "medicalExp": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('medicalExp'),
                    "profitLossBeforeTaxation": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('profitLossBeforeTaxation'),
                    "receiptNotTxAmt": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('receiptNotTxAmt'),
                    "renoWorksExpS14Q": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('renoWorksExpS14Q'),
                    "sepSrcIncome": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('sepSrcIncome'),
                    "sgIntDisc": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('sgIntDisc'),
                    "sgOtherI": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('sgOtherI'),
                    "sgRent": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('sgRent'),
                    "sholderChange": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('sholderChange'),
                    "totRemuneration": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('totRemuneration'),
                    "totSgFI": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('totSgFI'),
                    "sgAdjPLAft": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('sgAdjPLAft'),
                    "totalRevenue": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('totalRevenue'),
                    "tradeReceivables": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('tradeReceivables'),
                    "uCALDChangePrinAct": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('uCALDChangePrinAct'),
                    "unutilLossBFNorm": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('unutilLossBFNorm'),
                    "unutilCABFNorm": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('unutilCABFNorm'),
                    "unutilCACFNorm": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('unutilCACFNorm'),
                    "unutilLossCFNorm": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('unutilLossCFNorm'),
                    "unutilDonationCFNorm": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('unutilDonationCFNorm'),
                    "unutilDonationBFNorm": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('unutilDonationBFNorm'),
                    "unutilCALDClaimS23S37": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('unutilCALDClaimS23S37'),
                    "appStockConvAsset": res_data['data'].get('DataFormCS') and res_data['data']['DataFormCS'].get('appStockConvAsset'),
                    
                    "amortisationExpense": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('amortisationExpense'),
                    "bankCharges": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('bankCharges'),
                    "commissionOther": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('commissionOther'),
                    "depreciationExpense": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('depreciationExpense'),
                    "totalRevenue": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('totalRevenue'),
                    "sgIntDisc": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('sgIntDisc'),
                    "sgOtherI": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('sgOtherI'),
                    "repairMaintenanceExpRentalIncome": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('repairMaintenanceExpRentalIncome'),
                    "totalOtherIncome": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('totalOtherIncome'),
                    "training": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('training'),
                    "upkeepNonPrivateVehicles": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('upkeepNonPrivateVehicles'),
                    "upkeepPrivateVehicles": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('upkeepPrivateVehicles'),
                    "totalExpenses": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('totalExpenses'),
                    "profitLossBeforeTaxation": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('profitLossBeforeTaxation'),
                    "staffWelfare": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('staffWelfare'),
                    "staffRemunerationOtherThanDirectorsRemuneration": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('staffRemunerationOtherThanDirectorsRemuneration'),
                    "skillsDevelopmentForeignWorkerLevy": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('skillsDevelopmentForeignWorkerLevy'),
                    "salesAndMarketingExpense": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('salesAndMarketingExpense'),
                    "repairMaintenanceExcludingUpkeepOfPrivateVehiclesAndExp": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('repairMaintenanceExcludingUpkeepOfPrivateVehiclesAndExpRentalIncome'),
                    "repairsMaintenanceForPrivateVehicles": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('repairsMaintenanceForPrivateVehicles'),
                    "telecommunicationOrUtilities": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('telecommunicationOrUtilities'),
                    "rentExp": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('rentExp'),
                    "propertyTaxOther": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('propertyTaxOther'),
                    "professionalFees": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('professionalFees'),
                    "propertyTaxExpRentalIncome": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('propertyTaxExpRentalIncome'),
                    "penaltiesOrFine": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('penaltiesOrFine'),
                    "otherFinanceCost": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('otherFinanceCost'),
                    "otherPrivateOrCapitalExp": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('otherPrivateOrCapitalExp'),
                    "otherNonTaxableIncome": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('otherNonTaxableIncome'),
                    "otherExpRentalIncome": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('otherExpRentalIncome'),
                    "oneTierTaxDividendIncome": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('oneTierTaxDividendIncome'),
                    "netGainsOrLossesOnDisposalOfPPE": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('netGainsOrLossesOnDisposalOfPPE'),
                    "netGainsOrLossesOnForex": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('netGainsOrLossesOnForex'),
                    "netGainsOrLossesOnOtherItems": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('netGainsOrLossesOnOtherItems'),
                    "miscExp": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('miscExp'),
                    "medicalExpIncludingMedicalInsurance": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('medicalExpIncludingMedicalInsurance'),
                    "impairmentLossReversalOfImpairmentLossForBadDebts": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('impairmentLossReversalOfImpairmentLossForBadDebts'),
                    "interestExpRentalIncome": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('interestExpRentalIncome'),
                    "interestExpOther": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('interestExpOther'),
                    "insuranceExpOther": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('insuranceExpOther'),
                    "insuranceExpRentalIncome": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('insuranceExpRentalIncome'),
                    "grossPL": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('grossPL'),
                    "costOfGoodsSold": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('costOfGoodsSold'),
                    "donations": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('donations'),
                    "c1_GrossRent": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('c1_GrossRent'),
                    "directorsFees": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('directorsFees'),
                    "directorsRemunerationExcludingDirectorsFees": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('directorsRemunerationExcludingDirectorsFees'),
                    "commissionExpRentalIncome": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('commissionExpRentalIncome'),
                    "fixedAssetsExpdOff": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('fixedAssetsExpdOff'),
                    "c1_EntertainExp": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('c1_EntertainExp'),
                    "cpfContribution": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('cpfContribution'),
                    "c1_TransportExp": res_data['data'].get('DataDtlPNL') and res_data['data']['DataDtlPNL'].get('c1_TransportExp'),
                }
                if res_data['data'].get('DataRRSch'):
                    vals.update({'DataRRSch_renoWorksExpS14Q': res_data['data']['DataRRSch']['renoWorksExpS14Q']})
                    currentya = int(self.ya)
                    nlis = []
                    for ya in range(currentya - 3, currentya + 1):
                        nlis.append(str(ya))

                    currentya_dic, minus1_dic, minus2_dic = {'ya': nlis[-1]}, {'ya': nlis[-2]}, {'ya': nlis[-3]}
                    print("currentya_dic =",currentya_dic)
                    print("minus1_dic =",minus1_dic)
                    print("minus2_dic =",minus2_dic)

                    for a, b in res_data['data']['DataRRSch'].items():
                        print("For ==")
                        if 'leaseholdImprovementsAndRenoCostIncurred' in a:
                            if 'CurrentYA' in a:
                                currentya_dic.update({'leaseholdImprovementsAndRenoCostIncurred': b})
                            elif 'Minus1' in a:
                                minus1_dic.update({'leaseholdImprovementsAndRenoCostIncurred': b})
                            elif 'Minus2' in a:
                                minus2_dic.update({'leaseholdImprovementsAndRenoCostIncurred': b})
                        elif 'qualifyingRAndRCosts' in a:                            
                            if 'Minus2' in a:
                                minus2_dic.update({'qualifyingRAndRCosts': b})
                            elif 'Minus1' in a:
                                minus1_dic.update({'qualifyingRAndRCosts': b})
                            elif 'CurrentYA' in a:
                                currentya_dic.update({'qualifyingRAndRCosts': b})
                        elif 's14QDeduction' in a:
                            if 'Minus2' in a:
                                minus2_dic.update({'s14QDeduction': b})
                            elif 'Minus1' in a:
                                minus1_dic.update({'s14QDeduction': b})
                            elif 'CurrentYA' in a:
                                currentya_dic.update({'s14QDeduction': b})
                        print("currentya_dic =",currentya_dic)
                        print("minus1_dic =",minus1_dic)
                        print("minus2_dic =",minus2_dic)

                    vals.update({'renovation_refurbishment_sch_resp_ids': [(5,), (0,0,minus2_dic), (0,0,minus1_dic), (0,0,currentya_dic)]})

                nonHPCompCommEquipment_nonHPAddsDuringTheYear_ids, nonHpOtherPPE_nonHPAddsDuringTheYear_ids, nonHpOtherPPE_LowValAsset_nonHPAddsDuringTheYear_ids = [(5,)], [(5,)], [(5,)]
                for dic in res_data['data']['DataCASch']['nonHPAdditionsDuringTheYear'].get('nonHPCompCommEquipment'):
                    nonHPCompCommEquipment_nonHPAddsDuringTheYear_ids.append((0, 0, {
                        'descriptionEachAsset': dic['descriptionEachAsset'], 
                        'costEachAsset': dic['costEachAsset'], 
                        'yaOfPurchaseEachAsset': dic['yaOfPurchaseEachAsset'], 
                        'noOfYearsOfWorkingLifeBFEachAsset': dic['noOfYearsOfWorkingLifeBFEachAsset'], 
                        'taxWrittenDownValueBFEachAsset': dic['taxWrittenDownValueBFEachAsset'], 
                        'annualAllowanceEachAsset': dic['annualAllowanceEachAsset'], 
                        'taxWrittenDownValueCFEachAsset': dic['taxWrittenDownValueCFEachAsset']}))
                if nonHPCompCommEquipment_nonHPAddsDuringTheYear_ids:
                    vals.update({'nonHPCompCommEquipment_nonHPAddsDuringTheYear_ids': nonHPCompCommEquipment_nonHPAddsDuringTheYear_ids})

                for dic in res_data['data']['DataCASch']['nonHPAdditionsDuringTheYear'].get('nonHpOtherPPE'):
                    nonHpOtherPPE_nonHPAddsDuringTheYear_ids.append((0, 0, {
                        'descriptionEachAsset': dic['descriptionEachAsset'], 
                        'costEachAsset': dic['costEachAsset'], 
                        'yaOfPurchaseEachAsset': dic['yaOfPurchaseEachAsset'], 
                        'noOfYearsOfWorkingLifeBFEachAsset': dic['noOfYearsOfWorkingLifeBFEachAsset'], 
                        'taxWrittenDownValueBFEachAsset': dic['taxWrittenDownValueBFEachAsset'],
                        'annualAllowanceEachAsset': dic['annualAllowanceEachAsset'], 
                        'taxWrittenDownValueCFEachAsset': dic['taxWrittenDownValueCFEachAsset']}))
                if nonHpOtherPPE_nonHPAddsDuringTheYear_ids:
                    vals.update({'nonHpOtherPPE_nonHPAddsDuringTheYear_ids': nonHpOtherPPE_nonHPAddsDuringTheYear_ids})

                for dic in res_data['data']['DataCASch']['nonHPAdditionsDuringTheYear'].get('nonHpOtherPPE_LowValueAsset'):
                    nonHpOtherPPE_LowValAsset_nonHPAddsDuringTheYear_ids.append((0, 0, {
                        'descriptionEachAsset': dic['descriptionEachAsset'], 
                        'costEachAsset': dic['costEachAsset'], 
                        'yaOfPurchaseEachAsset': dic['yaOfPurchaseEachAsset'], 
                        'noOfYearsOfWorkingLifeBFEachAsset': dic['noOfYearsOfWorkingLifeBFEachAsset'], 
                        'taxWrittenDownValueBFEachAsset': dic['taxWrittenDownValueBFEachAsset'], 
                        'annualAllowanceEachAsset': dic['annualAllowanceEachAsset'], 
                        'taxWrittenDownValueCFEachAsset': dic['taxWrittenDownValueCFEachAsset']}))
                if nonHpOtherPPE_LowValAsset_nonHPAddsDuringTheYear_ids:
                    vals.update({'nonHpOtherPPE_LowValAsset_nonHPAddsDuringTheYear_ids': nonHpOtherPPE_LowValAsset_nonHPAddsDuringTheYear_ids})

                nonHpOtherPPE_nonHPPriorYearAdds_ids = [(5,)]
                for dic in res_data['data']['DataCASch']['nonHPPriorYearAdditions'].get('nonHpOtherPPE'):
                    nonHpOtherPPE_nonHPPriorYearAdds_ids.append((0, 0, {
                        'descriptionEachAsset': dic['descriptionEachAsset'], 
                        'yaOfPurchaseEachAsset': dic['yaOfPurchaseEachAsset'], 
                        'costEachAsset': dic['costEachAsset'], 
                        'noOfYearsOfWorkingLifeBFEachAsset': dic['noOfYearsOfWorkingLifeBFEachAsset'], 
                        'taxWrittenDownValueBFEachAsset': dic['taxWrittenDownValueBFEachAsset'], 
                        'annualAllowanceEachAsset': dic['annualAllowanceEachAsset'], 
                        'taxWrittenDownValueCFEachAsset': dic['taxWrittenDownValueCFEachAsset']}))
                if nonHpOtherPPE_nonHPPriorYearAdds_ids:
                    vals.update({'nonHpOtherPPE_nonHPPriorYearAdds_ids': nonHpOtherPPE_nonHPPriorYearAdds_ids})

                nonHpOtherPPE_nonHPDispDuringTheYear_ids, nonHpOtherPPE_LowValAsset_nonHPDispDuringTheYear_ids, nonHPCompCommEquipment_nonHPDispDuringTheYear_ids = [(5,)], [(5,)], [(5,)]
                for dic in res_data['data']['DataCASch']['nonHPDisposalsDuringTheYear'].get('nonHpOtherPPE'):
                    print("\n======= dic ===",dic)
                    nonHpOtherPPE_nonHPDispDuringTheYear_ids.append((0, 0, {
                        'descriptionEachAsset': dic['descriptionEachAsset'], 
                        'yaOfPurchaseEachAsset': dic['yaOfPurchaseEachAsset'], 
                        'costEachAsset': dic['costEachAsset'], 
                        'noOfYearsOfWorkingLifeBFEachAsset': dic.get('noOfYearsOfWorkingLifeBFEachAsset',''), 
                        'taxWrittenDownValueBFEachAsset': dic.get('taxWrittenDownValueBFEachAsset',''), 
                        'salesProceedEachAsset': dic['salesProceedEachAsset'], 
                        'yaOfDisposalEachAsset': dic['yaOfDisposalEachAsset'], 
                        'balancingChargeEachAssetDisposedOfOrWrittenOff': dic['balancingChargeEachAssetDisposedOfOrWrittenOff'], 
                        'balancingAllowanceEachAssetDisposedOfOrWrittenOff': dic['balancingAllowanceEachAssetDisposedOfOrWrittenOff']
                        }))
                if nonHpOtherPPE_nonHPDispDuringTheYear_ids:
                    vals.update({'nonHpOtherPPE_nonHPDispDuringTheYear_ids': nonHpOtherPPE_nonHPDispDuringTheYear_ids})

                for dic in res_data['data']['DataCASch']['nonHPDisposalsDuringTheYear'].get('nonHPCompCommEquipment'):
                    nonHPCompCommEquipment_nonHPDispDuringTheYear_ids.append((0, 0, {
                        'descriptionEachAsset': dic.get('descriptionEachAsset',''), 
                        'yaOfPurchaseEachAsset': dic.get('yaOfPurchaseEachAsset',''), 
                        'costEachAsset': dic.get('costEachAsset',''), 
                        'noOfYearsOfWorkingLifeBFEachAsset': dic.get('noOfYearsOfWorkingLifeBFEachAsset',''), 
                        'taxWrittenDownValueBFEachAsset': dic.get('taxWrittenDownValueBFEachAsset',''), 
                        'salesProceedEachAsset': dic.get('salesProceedEachAsset',''), 
                        'yaOfDisposalEachAsset': dic.get('yaOfDisposalEachAsset',''), 
                        'balancingChargeEachAssetDisposedOfOrWrittenOff': dic.get('balancingChargeEachAssetDisposedOfOrWrittenOff',''), 
                        'balancingAllowanceEachAssetDisposedOfOrWrittenOff': dic.get('balancingAllowanceEachAssetDisposedOfOrWrittenOff','')}))
                if nonHPCompCommEquipment_nonHPDispDuringTheYear_ids:
                    vals.update({'nonHPCompCommEquipment_nonHPDispDuringTheYear_ids': nonHPCompCommEquipment_nonHPDispDuringTheYear_ids})

                for dic in res_data['data']['DataCASch']['nonHPDisposalsDuringTheYear'].get('nonHpOtherPPE_LowValueAsset'):
                    nonHpOtherPPE_LowValAsset_nonHPDispDuringTheYear_ids.append((0, 0, {
                        'descriptionEachAsset': dic['descriptionEachAsset'], 
                        'yaOfPurchaseEachAsset': dic['yaOfPurchaseEachAsset'], 
                        'costEachAsset': dic['costEachAsset'], 
                        'noOfYearsOfWorkingLifeBFEachAsset': dic['noOfYearsOfWorkingLifeBFEachAsset'], 
                        'taxWrittenDownValueBFEachAsset': dic['taxWrittenDownValueBFEachAsset'], 
                        'salesProceedEachAsset': dic['salesProceedEachAsset'], 
                        'yaOfDisposalEachAsset': dic['yaOfDisposalEachAsset'], 
                        'balancingChargeEachAssetDisposedOfOrWrittenOff': dic['balancingChargeEachAssetDisposedOfOrWrittenOff'], 
                        'balancingAllowanceEachAssetDisposedOfOrWrittenOff': dic['balancingAllowanceEachAssetDisposedOfOrWrittenOff']}))
                if nonHpOtherPPE_LowValAsset_nonHPDispDuringTheYear_ids:
                    vals.update({'nonHpOtherPPE_LowValAsset_nonHPDispDuringTheYear_ids': nonHpOtherPPE_LowValAsset_nonHPDispDuringTheYear_ids})

                hpOtherPPE_hpAddsDuringTheYear_ids = [(5,)]
                for dic in res_data['data']['DataCASch']['hpAdditionsDuringTheYear'].get('hpOtherPPE'):
                    hpOtherPPE_hpAddsDuringTheYear_ids.append((0, 0, {
                        'descriptionEachAsset': dic['descriptionEachAsset'], 
                        'yaOfPurchaseEachAsset': dic['yaOfPurchaseEachAsset'], 
                        'costEachAsset': dic['costEachAsset'], 
                        'taxWrittenDownValueBFEachAsset': dic['taxWrittenDownValueBFEachAsset'], 
                        'annualAllowanceEachAsset': dic['annualAllowanceEachAsset'], 
                        'taxWrittenDownValueCFEachAsset': dic['taxWrittenDownValueCFEachAsset'], 
                        'deposit_OrPrincipal_ExcInterest_IncDownpay_EachAsset': dic['depositOrPrincipalExcludingInterestIncludingDownpaymentEachAsset']}))
                if hpOtherPPE_hpAddsDuringTheYear_ids:
                    vals.update({'hpOtherPPE_hpAddsDuringTheYear_ids': hpOtherPPE_hpAddsDuringTheYear_ids})

                hpOtherPPE_hpPriorYearAdditions_ids = [(5,)]
                for dic in res_data['data']['DataCASch']['hpPriorYearAdditions'].get('hpOtherPPE'):
                    hpOtherPPE_hpPriorYearAdditions_ids.append((0, 0, {
                        'descriptionEachAsset': dic['descriptionEachAsset'], 
                        'yaOfPurchaseEachAsset': dic['yaOfPurchaseEachAsset'], 
                        'costEachAsset': dic['costEachAsset'], 
                        'taxWrittenDownValueBFEachAsset': dic['taxWrittenDownValueBFEachAsset'], 
                        'annualAllowanceEachAsset': dic['annualAllowanceEachAsset'], 
                        'taxWrittenDownValueCFEachAsset': dic['taxWrittenDownValueCFEachAsset'], 
                        'deposit_OrPrincipal_ExcInterest_IncDownpay_EachAsset': dic['depositOrPrincipalExcludingInterestIncludingDownpaymentEachAsset']}))
                if hpOtherPPE_hpPriorYearAdditions_ids:
                    vals.update({'hpOtherPPE_hpPriorYearAdditions_ids': hpOtherPPE_hpPriorYearAdditions_ids})

                hpOtherPPE_hpDispDuringTheYear_ids = [(5,)]
                for dic in res_data['data']['DataCASch']['hpDisposalsDuringTheYear'].get('hpOtherPPE'):
                    hpOtherPPE_hpDispDuringTheYear_ids.append((0, 0, {
                        'descriptionEachAsset': dic['descriptionEachAsset'], 
                        'yaOfPurchaseEachAsset': dic['yaOfPurchaseEachAsset'], 
                        'costEachAsset': dic['costEachAsset'], 
                        'taxWrittenDownValueBFEachAsset': dic['taxWrittenDownValueBFEachAsset'], 
                        'salesProceedEachAsset': dic['salesProceedEachAsset'], 
                        'yaOfDisposalEachAsset': dic['yaOfDisposalEachAsset'], 
                        'balancingChargeEachAssetDisposedOfOrWrittenOff': dic['balancingChargeEachAssetDisposedOfOrWrittenOff'], 
                        'balancingAllowanceEachAssetDisposedOfOrWrittenOff': dic['balancingAllowanceEachAssetDisposedOfOrWrittenOff']}))
                if hpOtherPPE_hpDispDuringTheYear_ids:
                    vals.update({'hpOtherPPE_hpDispDuringTheYear_ids': hpOtherPPE_hpDispDuringTheYear_ids})

                vals.update({'state': 'cs_submission'})
                self.write(vals)
            else:
                if res_data.get('returnCode') == '30' and res_data.get('info') and res_data['info'].get('fieldInfoList'):
                    message = ''
                    for dic in res_data['info'].get('fieldInfoList'):
                        message += dic.get('message') + "\n"
                    
                    # if message:
                    #     raise ValidationError(_(message))

                self.message_post(body=_("Action failed.<br>CIT Conversion Response JSON:<br>%s") % (json.dumps(res_data)))
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': ('Error with returnCode' + str(res_data['returnCode'])),
                        'message': json.dumps(res_data),
                        'sticky': False,
                    }
                }
        else:
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': res_data.get('returnCode') and res_data['returnCode'] or 'Error',
                    'message': json.dumps(res_data),
                    'sticky': False,
                }
            }

    def action_view_acknowledgement(self):
        return {
            'name': _('Acknowledgement for Form C-S'),
            'view_mode': 'form',
            'res_model': 'form.cs',
            'view_id': self.env.ref('metroerp_iras.form_cs_form_acknowledgement').id,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': self.id,
        }

    def action_cs_submit(self):
        if self.env.user.has_group('metroerp_iras.iras_tax_agent_group'):
            self.write({'submitted_by_thirdparty': True})
        return {
            'name': _('Form C-S'),
            'view_mode': 'form',
            'res_model': 'form.cs',
            'view_id': self.env.ref('metroerp_iras.form_cs_form_submission').id,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': self.id,
        }

    def action_save(self):
        return

    def action_submit_cs(self):
        print("\naction_submit_cs() >>>>>")
        ctx = self._context
        # if not self.manager_signature:
        #     raise UserError(_("You cannot submit without placing the signature."))
        config_params = self.env['ir.config_parameter'].sudo()
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'X-IBM-Client-Id': config_params.get_param('iras_apikey'),
            'X-IBM-Client-Secret': config_params.get_param('iras_apisecret'),
            'access_token': self.access_token
        }
        payload = {
              "filingInfo": {
                "uen": self.uen,
                "uenType": self.uenType,
                "ya": self.ya,
                "designationOfFiler": self.designationOfFiler,
                "nameOfContactPerson": self.nameOfContactPerson,
                "contactNumber": self.contactNumber,
                "designationOfContactPerson": self.designationOfContactPerson,
                "declarantRefNo": self.declarantRefNo if self.declarantRefNo else ""
              },
              "declaration": {
                "isRevBelow5M": self.isRevBelow5M == 'Yes' and True or False,
                "isOnlyIncTxbl17": self.isOnlyIncTxbl17 == 'Yes' and True or False,
                "isNotClaimingSpecificItems": self.isNotClaimingSpecificItems == 'Yes' and True or False,
                "isFullAndTrueAccOfCompInc": self.isFullAndTrueAccOfCompInc,
                "isQualifiedToUseConvFormCS": self.isQualifiedToUseConvFormCS
              },
              "dataFormCS": {
                "sctpInd": self.sctpInd,
                "sctpName": self.sctpName or "",
                "sctpNo": self.sctpNo or "",

                "basisPeriodFrom": self.basisPeriodFrom.strftime("%Y-%m-%d"),
                "basisPeriodTo": self.basisPeriodTo.strftime("%Y-%m-%d"),
                "fsPrep": self.fsPrep if self.fsPrep else "",
                "firstFYE": self.firstFYE.strftime("%Y-%m-%d") if self.firstFYE else "",
                "prevFYE": self.prevFYE.strftime("%Y-%m-%d") if self.prevFYE else "",
                
                "profitLossBeforeTaxation": int(self.DataFormCS_profitLossBeforeTaxation),
                "sepSrcIncome": int(self.DataFormCS_sepSrcIncome),
                "receiptNotTxAmt": int(self.DataFormCS_receiptNotTxAmt),
                "c1_NTDeductibleExp": int(self.DataFormCS_c1_NTDeductibleExp),
                "adjPLBefDed": int(self.DataFormCS_adjPLBefDed),
                "renoWorksExpS14Q": int(self.DataFormCS_renoWorksExpS14Q),
                "c1_EnhancedEISDed": int(self.DataFormCS_c1_EnhancedEISDed),
                "c1_FurtherDed": int(self.DataFormCS_c1_FurtherDed),
                "sgAdjPLAft": int(self.DataFormCS_sgAdjPLAft),
                "c1_BC": int(self.DataFormCS_c1_BC),
                "unutilCABFNorm": int(self.DataFormCS_unutilCABFNorm),
                "cyCANorm": int(self.DataFormCS_cyCANorm),
                "unutilLossBFNorm": int(self.DataFormCS_unutilLossBFNorm),
                "c1_GrossRent": int(self.DataFormCS_c1_GrossRent),
                "c1_DedExp": int(self.DataFormCS_c1_DedExp),
                "sgRent": int(self.DataFormCS_sgRent),
                "sgIntDisc": int(self.DataFormCS_sgIntDisc),
                "sgOtherI": int(self.DataFormCS_sgOtherI),
                "totSgFI": int(self.DataFormCS_totSgFI),
                "unutilDonationBFNorm": int(self.DataFormCS_unutilDonationBFNorm),
                "cyDonation": int(self.DataFormCS_cyDonation),
                "ci": int(self.DataFormCS_ci),
                "unutilCACFNorm": int(self.DataFormCS_unutilCACFNorm),
                "unutilLossCFNorm": int(self.DataFormCS_unutilLossCFNorm),
                "unutilDonationCFNorm": int(self.DataFormCS_unutilDonationCFNorm),
                "totalRevenue": int(self.DataFormCS_totalRevenue),
                "grossPL": int(self.DataFormCS_grossPL),
                "directorFee": int(self.DataFormCS_directorFee),
                "totRemuneration": int(self.DataFormCS_totRemuneration),
                "medicalExp": int(self.DataFormCS_medicalExp),
                "c1_TransportExp": int(self.DataFormCS_c1_TransportExp),
                "c1_EntertainExp": int(self.DataFormCS_c1_EntertainExp),
                "inventories": int(self.DataFormCS_inventories),
                "tradeReceivables": int(self.DataFormCS_tradeReceivables),
                "sholderChange": self.DataFormCS_sholderChange,
                "uCALDChangePrinAct": self.DataFormCS_uCALDChangePrinAct,
                "unutilCALDClaimS23S37": int(self.DataFormCS_unutilCALDClaimS23S37),
                "fullTxX": self.DataFormCS_fullTxX,
                "expRD": int(self.DataFormCS_expRD),
                "expRDSG": int(self.DataFormCS_expRDSG),
                "enhanceDeductRD": int(self.DataFormCS_enhanceDeductRD),
                "appStockConvAsset": self.DataFormCS_appStockConvAsset,         

                "eis_ClaimCashPayout": self.eis_ClaimCashPayout,
                "eis_ClaimDedAll": self.eis_ClaimDedAll,
                "eis_TrainTotCost": int(self.eis_TrainTotCost),
                "eis_TrainDedAll": int(self.eis_TrainDedAll),
                "eis_InnoProjTotCost": int(self.eis_InnoProjTotCost),
                "eis_InnoProjDedAll": int(self.eis_InnoProjDedAll),
                "eis_AcqIPRTotCost": int(self.eis_AcqIPRTotCost),
                "eis_AcqIPRDedAll": int(self.eis_AcqIPRDedAll),
                "eis_LicensIPRTotCost": int(self.eis_LicensIPRTotCost),
                "eis_LicensIPRDedAll": int(self.eis_LicensIPRDedAll),
                "eis_RegIPTotCost": int(self.eis_RegIPTotCost),
                "eis_RegIPDedAll": int(self.eis_RegIPDedAll),
                "eis_RDSgTotCost": int(self.eis_RDSgTotCost),
                "eis_RDSgDedAll": int(self.eis_RDSgDedAll),
                "ptisDonInd": self.DataFormCS_ptisDonInd,
                "foreignAssetsSaleGainLoss": int(self.foreignAssetsSaleGainLoss),
                "foreignSourceSaleGainsRemit": int(self.foreignSourceSaleGainsRemit),
                "foreignSourceSaleNotTax": self.foreignSourceSaleNotTax
              }
            }

        print("payload ====",payload)
        print("json.dumps(payload) ===",json.dumps(payload))
        url = config_params.get_param('cs_submission_endpoint')
        print("url ====",url)
        print("headers ===",headers)
        self.message_post(body=_("Submission (Corppass) Request JSON:<br> %s") % (json.dumps(payload)))
        response = requests.request("POST", url, data=json.dumps(payload), headers=headers, allow_redirects=False)
        res_data = json.loads(response.text)
        print("res_data ===",res_data)
        if res_data.get('returnCode'):
            if res_data['returnCode'] == '10':
                self.message_post(body=_("Action performed successfully.<br>Submission (Corppass) Response JSON:<br>%s") % (json.dumps(res_data)))
                self.write({
                    'acknowledgementNo': str(res_data["data"]["acknowledgementNo"]),
                    'estTaxPayable': res_data["data"]["estTaxPayable"],
                    'timestamp': datetime.strptime(res_data["data"]["timestamp"], "%Y-%m-%dT%H:%M:%S"),
                    'timestamp_str': res_data["data"]["timestamp"],
                    'state': 'submitted',
                    'sctpName': res_data["data"]["dataFormCS"]["sctpName"],
                    'sctpNo': res_data["data"]["dataFormCS"]["sctpNo"],
                })
                if self.env.user.has_group('metroerp_iras.iras_tax_agent_group'):
                    self.write({'submitted_by_thirdparty': True})
                
                if not ctx.get('force_submit'):
                    return {'message': 'Submission successful!' + '<br/>' + '<h2>Acknowledgment No: ' + str(res_data["data"]["acknowledgementNo"]) + '</h2>' + '<h2>Estimated Tax Payable: $' + format(float(res_data["data"]["estTaxPayable"]), ".2f") + '</h2>'}
                else:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': ('Action'),
                            'message': 'Submission successful',
                            'sticky': False,
                        }
                    }
            else:
                self.message_post(body=_("Submission (Corppass) failure.<br>Submission (Corppass) Response JSON:<br>%s") % (json.dumps(res_data)))
                if not ctx.get('force_submit'):
                    return {'message': ('Error with returnCode: ' + str(res_data['returnCode']) + ". " + str(res_data['info']['message']))}
                else:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': ('Error with returnCode' + str(res_data['returnCode'])),
                            'message': json.dumps(res_data),
                            'sticky': False,
                        }
                    }
        else:
            self.message_post(body="Error arised.\n" + json.dumps(res_data))
            if not ctx.get('force_submit'):
                return {'message': res_data.get('httpMessage') and res_data['httpMessage'] or 'Error'}
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': res_data.get('httpMessage') and res_data['httpMessage'] or 'Error',
                        'message': json.dumps(res_data),
                        'sticky': False,
                    }
                }

    def write(self, vals):
        if vals.get('access_token'):
            self.write({
                        'access_token_datetime':fields.Datetime.now(),
                        'access_token_expired':False
                        })
        if vals.get('state') == 'conversion' and not self.renovation_refurbishment_sch_ids:
            self.action_auto_fill()
        if "declarantRefNo" in vals:
            if not self.env.user.partner_id.tax_ref_iras:
                self.env.user.partner_id.tax_ref_iras = vals.get('declarantRefNo')
                self.env.user.partner_id.is_foreigner = True
        return super(GFormCS, self).write(vals)

    def _cron_form_cs(self):
        for rec in self.env['form.cs'].search([]):
            local_time = pytz.timezone(self.env.context.get('tz', False))
            date_zone_minute = datetime.now(pytz.timezone(self.env.user.tz)).strftime('%Y-%m-%d %H:%M:%S')
            datetime_obj1 = datetime.strptime(str(date_zone_minute), '%Y-%m-%d %H:%M:%S')
            if rec.access_token_datetime:
                datetime_obj = datetime.strptime(str(rec.access_token_datetime),'%Y-%m-%d %H:%M:%S')
                time_diff = datetime_obj1 - datetime_obj
                diff_in_minutes = time_diff.total_seconds() / 60
                if diff_in_minutes >= 30:
                    rec.write({'access_token_expired':True})

    # @api.depends('revenueFromPropertyTransferredAtPointInTime','revenueFromGoodsTransferredAtPointInTime','revenueFromServicesTransferredAtPointInTime','revenueFromPropertyTransferredOverTime','revenueFromConstructionContractsOverTime','revenueFromServicesTransferredOverTime','revenueOthers')
    # def _get_totalRevenew(self):
    #     if self.revenueFromPropertyTransferredAtPointInTime or self.revenueFromGoodsTransferredAtPointInTime or self.revenueFromServicesTransferredAtPointInTime or self.revenueFromPropertyTransferredOverTime or self.revenueFromConstructionContractsOverTime or self.revenueFromServicesTransferredOverTime or self.revenueOthers:
    #         self.totalRevenue = self.revenueFromPropertyTransferredAtPointInTime + self.revenueFromGoodsTransferredAtPointInTime + self.revenueFromServicesTransferredAtPointInTime + self.revenueFromPropertyTransferredOverTime + self.revenueFromConstructionContractsOverTime + self.revenueFromServicesTransferredOverTime + self.revenueOthers
    #     else:
    #         self.totalRevenue = 0.00

    def action_auto_fill(self):
        list,vals = [],{}
        self.renovation_refurbishment_sch_ids.unlink()
        lis = [ 'leaseholdImprovementsAndRenoCostIncurredInCurrentYA',
                'leaseholdImprovementsAndRenoCostIncurredInYAMinus1',
                'leaseholdImprovementsAndRenoCostIncurredInYAMinus2',
                'leaseholdImprovementsAndRenoCostIncurredInYAMinus3',
                'leaseholdImprovementsAndRenoCostIncurredInYAMinus4']
        for i in range(5):
            vals = {'ya':str(int(self.ya)-i), 'tech_name':lis[i]}
            list.append((0,0, vals))
        list.reverse()
        self.update({'renovation_refurbishment_sch_ids': list})

    def proceed(self):
        self.state = "pre_fill"

    def action_fetch(self):

        config_params = self.env['ir.config_parameter'].sudo()
        target_move = self.company_id.target_moves_formcs

        model_fields = self._fields.keys()

        accounts = self.env['account.account'].search([('company_id','=',self.company_id.id),('iras_mapping_ids','!=',False),('iras_mapping_ids.date_as_of','=',True)])
        if accounts:
            data = {
                'init_balance': False,
                'sortby': 'sort_date',
                'display_account': 'movement',
                'form': {
                    'used_context': {
                        'journal_ids': self.env['account.journal'].search([]).ids, 
                        'state': target_move,
                        'date_from': '',
                        'date_to': str(self.basisPeriodTo), 
                        'strict_range': True, 
                        'company_id': self.company_id.id, 
                        'lang': 'en_US'
                    }
                }
            }

            print("\ndata ===",data)

            print("accounts ===",accounts)
            account_res = self._get_account_general_ledger(accounts, data)
            print("\naccount_res =====",account_res)

            dic = dict((fn, 0.0) for fn in [obj.name for obj in self.env['iras.coa.mapping'].search([('direct_mapping','=',True),('date_as_of','=',True)])])
            for account_dic in account_res:
                account = self.env['account.account'].browse(account_dic['account_id'])
                for map_obj in account.iras_mapping_ids:
                    dic[map_obj.name] += account_dic['balance']

            print("\ndic ====",dic)
            new_dic = {}
            for acc_name, amt in dic.items():
                if acc_name in model_fields:
                    if acc_name == 'totalRevenue':
                        new_dic[acc_name] = abs(math.floor(amt))
                    else:
                        new_dic[acc_name] = math.floor(amt)
            print("\nnew_dic ====",new_dic)
            self.write(new_dic)

        # Next part
        accounts = self.env['account.account'].search([('company_id','=',self.company_id.id),('iras_mapping_ids','!=',False),('iras_mapping_ids.date_as_of','=',False)])
        if accounts:
            data = {
                'init_balance': False,
                'sortby': 'sort_date',
                'display_account': 'movement',
                'form': {
                    'used_context': {
                        'journal_ids': self.env['account.journal'].search([]).ids, 
                        'state': target_move,
                        'date_from': str(self.basisPeriodFrom),
                        'date_to': str(self.basisPeriodTo), 
                        'strict_range': True, 
                        'company_id': self.company_id.id, 
                        'lang': 'en_US'
                    }
                }
            }

            print("\ndata ===",data)

            account_res = self._get_account_general_ledger(accounts, data)
            print("\naccount_res =====",account_res)

            dic = dict((fn, 0.0) for fn in [obj.name for obj in self.env['iras.coa.mapping'].search([('direct_mapping','=',True),('date_as_of','=',False)])])
            for account_dic in account_res:
                account = self.env['account.account'].browse(account_dic['account_id'])
                for map_obj in account.iras_mapping_ids:
                    dic[map_obj.name] += account_dic['balance']

            print("\ndic ====",dic)

            # Fetch all mappings just once
            mappings = {
                m.name: m for m in self.env['iras.coa.mapping'].search([
                    ('direct_mapping', '=', True),
                    ('date_as_of', '=', False)
                ])
            }

            new_dic = {}
            
            for acc_name, amt in dic.items():
                if acc_name in model_fields:
                    if acc_name == 'totalRevenue':
                        new_dic[acc_name] = abs(math.floor(amt))
                    else:
                        new_dic[acc_name] = math.floor(amt)
            print("\nnew_dic ====",new_dic)

            self.write(new_dic)

        self.is_fetched =True

    def action_go_back(self):
        if self.state == 'conversion':
            self.state = 'pre_fill'
        elif self.state == 'cs_submission':
            if self.skip_tax_conversion:
                self.state = 'pre_fill'
            else:
                self.state = 'conversion'

    def action_generate_acknowledgment_report(self):
        return self.env.ref('metroerp_iras.action_report_acknowledgment').report_action(self, config=False)
