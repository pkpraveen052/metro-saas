import json
import logging
import requests
import traceback
from odoo.exceptions import UserError, ValidationError
import random
import string
import re

import urllib.parse

from odoo import api, models, fields, _
from datetime import datetime

logger = logging.getLogger(__name__)


class GSTReturnsF5F8(models.Model):
    _name = "gst.returns.f5f8"
    _description = "GST Returns F5 and F8"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'base.gst.accounts']
    _order = "create_date desc"
    _rec_name = "id"

    @api.depends('totStdSupply','totZeroSupply','totExemptSupply')
    def _compute_supply(self):
        if self.totStdSupply or self.totZeroSupply or self.totExemptSupply:
            self.totalSupply = self.totStdSupply + self.totZeroSupply + self.totExemptSupply
        else:
            self.totalSupply = 0.0

    @api.depends('outputTaxDue', 'inputTaxRefund')
    def _compute_tax(self):
        if self.outputTaxDue or self.inputTaxRefund:
            self.totalTax = self.outputTaxDue - self.inputTaxRefund
        else:
            self.totalTax = 0.0

    @api.constrains('dtPeriodEnd')
    def constrain_dtPeriodEnd(self):
        if self.dtPeriodEnd <= self.dtPeriodStart:
            raise UserError(_('Sorry, GST End Period Date must be next date of GST Start Period Date...'))

    @api.model
    def create(self, vals):
        vals['state'] = 'draft'
        return super(GSTReturnsF5F8, self).create(vals)

    def action_ready_submit(self):
        if self.contactEmail:
            if re.match(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$", self.contactEmail) != None:
                pass
            else:
                raise ValidationError(_('Please enter a proper format for Contact Email field.'))
        if self.contactNumber:
            if len(self.contactNumber) != 8:
                raise UserError(_("Telephone number entered must be a 8-digit local number."))
            if re.match("^[0-9]+$", self.contactNumber) == None:
                raise UserError(_("Telephone number entered must be a 8-digit local number."))

        if self.badDebtReliefClaimAmt < 0:
            raise UserError(_("Negative value is not allowed in Bad Debt Relief Claims and/or refund for reverse charge Amount."))

        if self.preRegistrationClaimAmt < 0:
            raise UserError(_("Negative value is not allowed in Pre-registration Claims Amount."))

        if self.defImpPayableAmt < 0 and self.defTotalGoodsImp > 0:
            raise UserError(_("Total value of goods imported under IGDS is in positive value, deferred import GST payable should not be in negative value. Please re-enter value."))

        if self.defImpPayableAmt == 0 and (self.defTotalGoodsImp > 0 or self.defTotalGoodsImp < 0):
            raise UserError(_("Total value of goods imported under IGDS is completed; deferred import GST payable should not be zero value. Please re-enter value."))

        if self.defTotalGoodsImp == 0 and (self.defImpPayableAmt < 0 or self.defImpPayableAmt > 0):
            raise UserError(_("As deferred import GST payable is completed, Total value of goods imported under IGDS should not be zero value. Please re-enter the value."))

        if self.defTotalGoodsImp < 0 and self.defImpPayableAmt > 0:
            raise UserError(_("Total value of goods imported under IGDS should be more than deferred import GST payable. Please re-enter the value."))
        elif self.defTotalGoodsImp < 0 and self.defImpPayableAmt < 0 and self.defImpPayableAmt <= self.defTotalGoodsImp:
            raise UserError(_("Total value of goods imported under IGDS should be more than deferred import GST payable. Please re-enter the value."))
        elif self.defTotalGoodsImp > 0 and self.defImpPayableAmt > 0 and self.defImpPayableAmt >= self.defTotalGoodsImp:
            raise UserError(_("Total value of goods imported under IGDS should be more than deferred import GST payable. Please re-enter the value."))

        if not self.revenue or not self.revenue.isdigit():
            raise ValidationError("Revenue for the accounting period box is not entered with figure.")
        if (self.badDebtChk or self.touristRefundChk or self.preRegistrationChk) and self.inputTaxRefund == 0: #add in f7
            raise ValidationError("Input tax and refund claims should not be Nil if you are claiming for Tourist Refund/Pre-registration claim/Bad debt relief claim.")
        if (self.badDebtChk == False and self.badDebtReliefClaimAmt != 0) or (self.touristRefundChk == False and self.touristRefundAmt != 0) or (self.preRegistrationChk == False and self.preRegistrationClaimAmt != 0): #add in f7
            raise ValidationError("Please select Yes if you are claiming for Tourist Refund/Pre-registration claim/Bad debt relief claim.")
        if (self.totStdSupply > 0 and self.outputTaxDue < 0) and self.validation_sn7_done == False:
            return {
                'name': _('GST Returns Prompt'),
                'view_mode': 'form',
                'res_model': 'gst.returns.prompt.wizard',
                'view_id': self.env.ref('metroerp_iras.gst_returns_prompt_wizard_view_sn7').id,
                'type': 'ir.actions.act_window',
                'target': 'new'
            }
        else:
            self.validation_sn7_done = True

        if (self.totStdSupply != 0 and self.outputTaxDue == 0) and self.validation_sn8_done == False:
            return {
                'name': _('GST Returns Prompt'),
                'view_mode': 'form',
                'res_model': 'gst.returns.prompt.wizard',
                'view_id': self.env.ref('metroerp_iras.gst_returns_prompt_wizard_view_sn8').id,
                'type': 'ir.actions.act_window',
                'target': 'new'
            }
        else:
            self.validation_sn8_done = True

        if (self.totStdSupply == 0 and self.outputTaxDue != 0) and self.validation_sn9_done == False:
            return {
                'name': _('GST Returns Prompt'),
                'view_mode': 'form',
                'res_model': 'gst.returns.prompt.wizard',
                'view_id': self.env.ref('metroerp_iras.gst_returns_prompt_wizard_view_sn9').id,
                'type': 'ir.actions.act_window',
                'target': 'new'
            }
        else:
            self.validation_sn9_done = True

        if (self.totStdSupply < self.outputTaxDue or (self.totStdSupply != 0 and self.outputTaxDue != 0 and self.totStdSupply == self.outputTaxDue)) and self.validation_sn10_done == False:
            return {
                'name': _('GST Returns Prompt'),
                'view_mode': 'form',
                'res_model': 'gst.returns.prompt.wizard',
                'view_id': self.env.ref('metroerp_iras.gst_returns_prompt_wizard_view_sn10').id,
                'type': 'ir.actions.act_window',
                'target': 'new'
            }
        else:
            self.validation_sn10_done = True

        if (self.totTaxPurchase < self.inputTaxRefund) and self.validation_sn11_done == False:
            return {
                'name': _('GST Returns Prompt'),
                'view_mode': 'form',
                'res_model': 'gst.returns.prompt.wizard',
                'view_id': self.env.ref('metroerp_iras.gst_returns_prompt_wizard_view_sn11').id,
                'type': 'ir.actions.act_window',
                'target': 'new'
            }
        else:
            self.validation_sn11_done = True

        if (self.inputTaxRefund != 0 and self.totTaxPurchase == 0) and self.validation_sn12_done == False:
            return {
                'name': _('GST Returns Prompt'),
                'view_mode': 'form',
                'res_model': 'gst.returns.prompt.wizard',
                'view_id': self.env.ref('metroerp_iras.gst_returns_prompt_wizard_view_sn12').id,
                'type': 'ir.actions.act_window',
                'target': 'new'
            }
        else:
            self.validation_sn12_done = True

        if (self.inputTaxRefund != 0 and self.totValueScheme == self.totTaxPurchase) and self.validation_sn13_done == False:
            return {
                'name': _('GST Returns Prompt'),
                'view_mode': 'form',
                'res_model': 'gst.returns.prompt.wizard',
                'view_id': self.env.ref('metroerp_iras.gst_returns_prompt_wizard_view_sn13').id,
                'type': 'ir.actions.act_window',
                'target': 'new'
            }
        else:
            self.validation_sn13_done = True

        if (self.totValueScheme != 0 and self.totTaxPurchase < self.totValueScheme) and self.validation_sn14_done == False:
            return {
                'name': _('GST Returns Prompt'),
                'view_mode': 'form',
                'res_model': 'gst.returns.prompt.wizard',
                'view_id': self.env.ref('metroerp_iras.gst_returns_prompt_wizard_view_sn14').id,
                'type': 'ir.actions.act_window',
                'target': 'new'
            }
        else:
            self.validation_sn14_done = True

        if not self.declareTrueCompleteChk or not self.declareIncRtnFalseInfoChk:
            raise UserError("Please accept the declaration before you submit the form.")

        self.state = "ready_submit"

    def action_click_me_edit(self):
        self.write({
            'state': "draft",
            'validation_sn7_done': False,
            'validation_sn8_done': False,
            'validation_sn9_done': False,
            'validation_sn10_done': False,
            'validation_sn11_done': False,
            'validation_sn12_done': False,
            'validation_sn13_done': False,
            'validation_sn14_done': False,
            'grp1BadDebtRecoveryChk': False,
            'grp1PriorToRegChk': False,
            'grp1OtherReasonChk': False,
            'grp1OtherReasons': "",
            'grp2TouristRefundChk': False,
            'grp2AppvBadDebtReliefChk': False,
            'grp2CreditNotesChk': False,
            'grp2OtherReasonsChk': False,
            'grp2OtherReasons': "",
            'grp3CreditNotesChk': False,
            'grp3OtherReasonsChk': False,
            'grp3OtherReasons': ""
        })

    def write(self, vals):
        if vals.get('manager_signature'):
            vals['signed_by'] = self.env.user.name if self.env.user else self.partner_id.name
            vals['manager_signature_done'] = True
        return super(GSTReturnsF5F8, self).write(vals)

    @api.onchange('dtPeriodEnd')
    def onchange_periodend(self):
        print("onchange_periodend =====",self.dtPeriodEnd, type(self.dtPeriodEnd))
        if self.dtPeriodEnd:
            print(self.dtPeriodEnd.year)
            current_date = datetime.now().date()
            print(current_date.year)
            self.RedlvrMktOprLVGChk = False
            self.totRedlvrMktOprLVGAmt = 0
            self.OwnImpLVGChk = False
            self.totOwnImpLVGAmt = 0
            if self.dtPeriodEnd.year < current_date.year:
                self.is_before_year = True
                self.OVRRSChk_beforeyear = False
                self.RCLVGChk_beforeyear = False
            else:
                self.is_before_year = False
                self.OVRRSChk = False
                self.RCLVGChk = False

    @api.onchange('touristRefundChk','badDebtChk','preRegistrationChk','RCLVGChk', 'RCLVGChk_beforeyear', 'OVRRSChk', 'OVRRSChk_beforeyear', 'RedlvrMktOprLVGChk','OwnImpLVGChk')
    def onchange_sn_16(self):
        if not self.touristRefundChk:
            self.write({'touristRefundAmt':0})
        if not self.badDebtChk:
            self.write({'badDebtReliefClaimAmt':0})
        if not self.preRegistrationChk:
            self.write({'preRegistrationClaimAmt': 0})
        if not self.RCLVGChk or not self.RCLVGChk_beforeyear:
            self.write({'totImpServLVGAmt': 0})
        if not self.OVRRSChk or not self.OVRRSChk_beforeyear:
            self.write({'totRemServAmt': 0})
        if not self.RedlvrMktOprLVGChk:
            self.write({'totRedlvrMktOprLVGAmt': 0})
        if not self.OwnImpLVGChk:
            self.write({'totOwnImpLVGAmt': 0})

    def action_claim_f7(self):
        context = {
            'default_company_id': self.company_id.id,
            'default_taxRefNo': self.taxRefNo,
            'default_formType': 'F7',
            'default_dtPeriodStart': self.dtPeriodStart,
            'default_dtPeriodEnd': self.dtPeriodEnd,
            'default_totStdSupply': self.totStdSupply,
            'default_totZeroSupply': self.totZeroSupply,
            'default_totExemptSupply': self.totExemptSupply,
            'default_totTaxPurchase': self.totTaxPurchase,
            'default_outputTaxDue': self.outputTaxDue,
            'default_inputTaxRefund': self.inputTaxRefund,
            'default_declareTrueCompleteChk': self.declareTrueCompleteChk,
            'default_declareIncRtnFalseInfoChk': self.declareIncRtnFalseInfoChk,
            'default_declarantDesgtn': self.declarantDesgtn,
            'default_contactPerson': self.contactPerson,
            'default_contactNumber': self.contactNumber,
            'default_contactEmail': self.contactEmail,
            'default_gst_f5f8_id': self.id,
            'default_defTotalGoodsImp': 0,
            'default_prevGSTPaid': self.totalTax,
            'default_revenue': self.revenue
        }
        return {
            'view_mode': 'form',
            'res_model': 'gst.returns.f7',
            'view_id': self.env.ref('metroerp_iras.gst_returns_f7_form').id,
            'type': 'ir.actions.act_window',
            'context': context,
        }

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            self.company_name = self.company_id.name
        else:
            self.company_name = False
        
    singpass_url = fields.Char("Singpass Login URL", tracking=True)
    access_token = fields.Text("Access Token", tracking=True)
    auth_code = fields.Char("Auth Code", tracking=True)
    state_identifier = fields.Char("State Identifier", tracking=True)
    online_gst_registered = fields.Boolean("Is Online GST Registered?", tracking=True)
    active = fields.Boolean('Active', default=True)
    company_name = fields.Char(string="Company Name")
    company_id = fields.Many2one('res.company', string='Filing Company', required=True, default=lambda self: self.env.company, readonly=True, tracking=True)
    state = fields.Selection([('new',"New"), ('draft',"Draft"), ('ready_submit','Ready to Submit'),('submitted','Submitted')], default='new', string='Status', tracking=True, copy=False)
    taxRefNo = fields.Char(string="Tax Ref No (GST)", required=True, size=30, tracking=True, default=lambda self: self.env.company.vat)
    formType = fields.Selection([("F5","F5"), ("F8","F8")],string="Form Type", required=True, tracking=True)
    dtPeriodStart = fields.Date(string="GST Start Period Date", required=True, tracking=True)
    dtPeriodEnd = fields.Date(string="GST End Period Date", required=True, tracking=True)
    totStdSupply = fields.Float(string="Total value of standard-rated supplies", digits=(14, 0), required=True, tracking=True, default=0)
    totZeroSupply = fields.Float(string="Total value of zero-rated supplies", digits=(14, 0), required=True, tracking=True, default=0)
    totExemptSupply = fields.Float(string="Total value of exempt supplies", digits=(14, 0), required=True, tracking=True, default=0)
    totalSupply = fields.Float(string="Total Supply of (1) + (2) + (3)", compute="_compute_supply", store=True, digits=(14, 0), tracking=True)
    totValueSupply = fields.Float(string='Total value of (1) + (2) + (3)', readonly=True, digits=(15,0), tracking=True)
    totTaxPurchase = fields.Float(string="Total value of taxable purchases", digits=(14, 0), required=True, tracking=True, default=0)
    outputTaxDue = fields.Float(string="Output tax due", digits=(14, 2), required=True, tracking=True, default=0)
    inputTaxRefund = fields.Float(string="Input tax and refunds claimed", digits=(14, 2), required=True, tracking=True, default=0)
    totalTax = fields.Float(string="Total Tax", digits=(14, 2), compute="_compute_tax", store=True, tracking=True)
    totValueScheme = fields.Float(string="Total value of goods imported under import GST suspension schemes", digits=(14, 0), required=True, tracking=True, copy=False, default=0)
    touristRefundChk = fields.Boolean(string="Did you claim for GST you had refunded to tourists?", tracking=True, copy=False)
    touristRefundAmt = fields.Float(string="Tourist Refund Amount", digits=(14, 2), tracking=True, copy=False)
    badDebtChk = fields.Boolean(string="Did you make any bad debt relief claims and/or refund for reverse charge transactions?", tracking=True, copy=False)
    badDebtReliefClaimAmt = fields.Float(string=" Bad Debt Relief Claims and/or refund for reverse charge Amount", digits=(14, 2), tracking=True, copy=False)
    preRegistrationChk = fields.Boolean(string=" Did you make any pre-registration claims?", tracking=True, copy=False)
    preRegistrationClaimAmt = fields.Float(string="Pre-registration Claims Amount", digits=(14, 2), tracking=True, copy=False, default=0)
    revenue = fields.Char(string=" Revenue for the accounting period", tracking=True, copy=False, default='0')
    RCLVGChk_beforeyear = fields.Boolean(string="Did you import services subject to GST under Reverse Charge?", tracking=True, copy=False)
    RCLVGChk = fields.Boolean(string="Did you import services and/or low-value goods subject to GST under reverse charge?", tracking=True, copy=False)
    totImpServLVGAmt = fields.Float(string="Value of imported services and/or low-value goods subject to reverse charge", digits=(14, 0), required=True, tracking=True, copy=False, default=0)
    OVRRSChk_beforeyear = fields.Boolean(string="Did you operate an electronic marketplace to supply digital services subject to GST on behalf of third-party suppliers?", tracking=True, copy=False)
    OVRRSChk = fields.Boolean(string="Did you operate an electronic marketplace to supply remote services (includes digital and nondigital services) subject to GST on behalf of thirdparty suppliers?", tracking=True, copy=False)
    totRemServAmt = fields.Float(string="Value of remote services supplied by electronic marketplace operator", digits=(14, 0), tracking=True, copy=False)
    RedlvrMktOprLVGChk = fields.Boolean(string="Did you operate as a redeliverer, or an electronic marketplace to supply imported low-value goods subject to GST on behalf of third-party suppliers?", tracking=True, copy=False)
    totRedlvrMktOprLVGAmt = fields.Float(string="Value of imported low-value goods supplied by electronic marketplace operator/ redeliverer", compute="_compute_tax", store=True, digits=(14, 0), tracking=True, copy=False)
    OwnImpLVGChk = fields.Boolean(string="Did you make your own supply of imported low-value goods that is subject to GST?", tracking=True, copy=False)
    totOwnImpLVGAmt = fields.Float(string="Value of own supply of imported lowvalue goods", digits=(14, 0), tracking=True, copy=False)
    defNetGst = fields.Float('Net GST per box 8 above', digits=(14, 2), tracking=True, copy=False, default=0)
    defImpPayableAmt = fields.Float(string="Deferred import GST payable", digits=(14, 2), required=True, tracking=True, copy=False, default=0)
    defTotalTaxAmt = fields.Float('Equals: Total tax to be paid to/claimed from IRAS', digits=(14, 2), tracking=True, copy=False, default=0)
    defTotalGoodsImp = fields.Float(string="Total value of goods imported under Import GST Deferment Scheme", digits=(15, 0), required=True, tracking=True, copy=False, default=0)
    declareTrueCompleteChk = fields.Boolean(string="I declare that the information provided in this return is true and complete.", tracking=True, copy=False, default=True)
    declareIncRtnFalseInfoChk = fields.Boolean(string="I understand that penalties may be imposed for the submission of an incorrect return and/or provision of false information to the Comptroller of GST.", tracking=True, copy=False, default=True)
    declarantDesgtn = fields.Char(string="Designation", size=60, tracking=True, default=lambda self: self.env.user.function)
    contactPerson = fields.Char(string="Contact Person", size=100, tracking=True, default=lambda self: self.env.user.name)
    contactNumber = fields.Char(string="Contact Tel No. (+65)", size=8, tracking=True, default=lambda self: self.env.user.phone)
    contactEmail = fields.Char(string="Contact Email", size=50, tracking=True, default=lambda self: self.env.user.login)
    grp1BadDebtRecoveryChk = fields.Boolean(string="TotStdSupply less than OutputTaxDue - Bad Debt Recovery", tracking=True, copy=False)
    grp1PriorToRegChk = fields.Boolean(string="TotStdSupply less than OutputTaxDue - Prior To Registration", tracking=True, copy=False)
    grp1OtherReasonChk = fields.Boolean(string="TotStdSupply less than OutputTaxDue - Other Reasons", tracking=True, copy=False)
    grp1OtherReasons = fields.Text(string="TotStdSupply less than OutputTaxDue - Other Reasons Specification", size=200, tracking=True, copy=False)
    grp2TouristRefundChk = fields.Boolean(string="TotTaxPurchase less than InputTaxRefund - Tourist Refund", tracking=True, copy=False)
    grp2AppvBadDebtReliefChk = fields.Boolean(string="TotTaxPurchase less than InputTaxRefund - Approved Bad Debt Relief and/or Refund Claims for Reverse Charge", tracking=True, copy=False)
    grp2CreditNotesChk = fields.Boolean(string="TotTaxPurchase less than InputTaxRefund - Credit Notes", tracking=True, copy=False)
    grp2OtherReasonsChk = fields.Boolean(string="TotTxPurchase less than InputTaxRefund - Other Reasons", tracking=True, copy=False)
    grp2OtherReasons = fields.Text(string="TotTaxPurchase less than InputTaxRefund - Other Reasons Specification", size=200, tracking=True, copy=False)
    grp3CreditNotesChk = fields.Boolean(string="TotTaxPurchase less than totValueScheme - Credit Notes", tracking=True, copy=False)
    grp3OtherReasonsChk = fields.Boolean(string="TotTaxPurchase less than totValueScheme - Other Reasons", tracking=True, copy=False)
    grp3OtherReasons = fields.Text(string="TotTaxPurchase less than totValueScheme - Other Reasons Specification", size=200, tracking=True, copy=False)
    json_iras = fields.Text(copy=False)
    signed_by = fields.Char('Signed By', tracking=True, copy=False)
    manager_signature_done = fields.Boolean(copy=False)
    manager_signature = fields.Binary(string="Signature", attachment=True, tracking=True, copy=False)
    ackNo = fields.Char(string="Acknowledgement", size=20, tracking=True, readonly=True, copy=False)
    pymtRefNo = fields.Char(string="Payment Reference No",tracking=True, readonly=True, copy=False)
    json_response = fields.Text(string="JSON Response", tracking=True, readonly=False, copy=False)
    validation_sn7_done = fields.Boolean(copy=False)
    validation_sn8_done = fields.Boolean(copy=False)
    validation_sn9_done = fields.Boolean(copy=False)
    validation_sn10_done = fields.Boolean(copy=False)
    validation_sn11_done = fields.Boolean(copy=False)
    validation_sn12_done = fields.Boolean(copy=False)
    validation_sn13_done = fields.Boolean(copy=False)
    validation_sn14_done = fields.Boolean(copy=False)
    declaration_label = fields.Char("Declaration Label", readonly=True)
    gst_f7_id = fields.Many2one("gst.returns.f7", "Past GST Return (GST F7)")
    is_before_year = fields.Boolean('Is before year')
    is_fetched = fields.Boolean('Is Fetched?')
    

    def extract_payment_reference(self):
        for record in self:
            if not record.json_response:
                continue
            try:
                data = json.loads(record.json_response)
                pymt_ref_no = data.get('data', {}).get('filingInfo', {}).get('pymtRefNo', '')
                if pymt_ref_no:
                    record.pymtRefNo = pymt_ref_no
            except Exception as e:
                raise UserError(_('Error parsing JSON response: %s') % str(e))

    def action_open_f7(self):
        return {
            'view_mode': 'tree,form',
            'res_model': 'gst.returns.f7',
            'type': 'ir.actions.act_window',
            'domain': [('id','=',self.gst_f7_id.id)]
        }
    @api.onchange('formType')
    def onchange_formtype(self):
        if self.formType == 'F5':
            self.declaration_label = 'GST F5'
        elif self.formType == 'F8':
            self.declaration_label = 'GST F8'

    @api.onchange('taxRefNo')
    def onchange_taxrefno(self):
        if self.taxRefNo:
            self.online_gst_registered = False

    def check_gst_registered(self):
        config_params = self.env['ir.config_parameter'].sudo()

        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'X-IBM-Client-Id': config_params.get_param('iras_apikey'),
            'X-IBM-Client-Secret': config_params.get_param('iras_apisecret')
        }

        payload = {
          "clientID": config_params.get_param('iras_apikey'),
          "regID": self.taxRefNo
        }

        url = config_params.get_param('searchgst_registered_endpoint')
        response = requests.request("POST", url, data=json.dumps(payload), headers=headers, allow_redirects=False)

        res_data = json.loads(response.text)
        if res_data.get('returnCode'):
            if res_data['returnCode'] == "10":
                self.message_post(body="GST Registered.\n" + json.dumps(res_data))
                self.write({'online_gst_registered': True})
            else:
                msg = ""
                for field_info in res_data['info']['fieldInfoList']:
                    msg += field_info['message'] + "\n"
                if not msg:
                    msg = res_data['info']['message']
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': ('Error'),
                        'message': msg,
                        'sticky': False,
                    }
                }
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

    def action_submit(self):        
        if not self.manager_signature_done:
            return {
                'name': _('Signature'),
                'view_mode': 'form',
                'res_model': 'gst.returns.f5f8',
                'view_id': self.env.ref('metroerp_iras.gst_returns_signature_f5f8_form').id,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': self.id,
            }

        config_params = self.env['ir.config_parameter'].sudo()

        # Corppass Authentication Code starts
        headers = {
            'Content-type': 'application/json',
            'X-IBM-Client-Id': config_params.get_param('iras_apikey'),
            'X-IBM-Client-Secret': config_params.get_param('iras_apisecret'),
            'Accept': 'application/json',
            # 'Host': 'apisandbox.iras.gov.sg'
        }

        if self.env.user.has_group('metroerp_iras.iras_tax_agent_group'):
            tax_agent = True
        else:
            tax_agent = False

        state = ''.join(random.choices(string.ascii_lowercase + string.digits, k=15))
        state += '_' + str(config_params.get_param('web.base.url')) + '_' + str(self.id) + '_' + 'GSTF5F8SubCP' + '_' + str(self.env.ref('metroerp_iras.gst_returns_f5f8_action').id)

        params = {
            'scope': 'GSTF5F8SubCP',
            'callback_url': config_params.get_param('corppass_callback_url'),
            'tax_agent': tax_agent,
            'state': state,
        }

        url = config_params.get_param('corppass_auth_endpoint')
        url = "{}?scope={}&callback_url={}&tax_agent={}&state={}".format(url, params['scope'], params['callback_url'], str(params['tax_agent']).lower(), params['state'])
        # response = requests.request("GET", url, params=params, headers=headers)
        print("url ===",url)
        print("headers ===",headers)
        response = requests.request("GET", url, headers=headers)

        res_data = json.loads(response.text)

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
                'target': 'self',
                'url': res_data['data']['url'],
            }
        # Corppass Authentication Code ends

    def generate_json_request(self):
        if self.is_before_year:
            RCLVGChk = self.RCLVGChk_beforeyear
            OVRRSChk = self.OVRRSChk_beforeyear
        else:
            RCLVGChk = self.RCLVGChk
            OVRRSChk = self.OVRRSChk
        data = {
                 "filingInfo":{
                     "taxRefNo":self.taxRefNo,
                     "formType":self.formType,
                     "dtPeriodStart":self.dtPeriodStart.strftime("%Y-%m-%d"),
                     "dtPeriodEnd":self.dtPeriodEnd.strftime("%Y-%m-%d")
                 },
                 "supplies":{
                     "totStdSupply":self.totStdSupply,
                     "totZeroSupply":self.totZeroSupply,
                     "totExemptSupply":self.totExemptSupply
                 },
                 "purchases":{
                 "totTaxPurchase":self.totTaxPurchase
                 },
                 "taxes":{
                 "outputTaxDue":self.outputTaxDue,
                 "inputTaxRefund":self.inputTaxRefund
                 },
                 "schemes":{
                 "totValueScheme":self.totValueScheme,
                 "touristRefundChk":self.touristRefundChk,
                 "touristRefundAmt":self.touristRefundAmt,
                 "badDebtChk":self.badDebtChk,
                 "badDebtReliefClaimAmt":self.badDebtReliefClaimAmt,
                 "preRegistrationChk":self.preRegistrationChk,
                 "preRegistrationClaimAmt":self.preRegistrationClaimAmt
                 },
                 "revenue":{
                 "revenue":int(self.revenue)
                 },
                 "RevChargeLVG":{
                 "RCLVGChk":RCLVGChk,
                 "totImpServLVGAmt":self.totImpServLVGAmt
                 },
                 "ElectronicMktplaceOprRedlvr":{
                 "OVRRSChk":OVRRSChk,
                 "totRemServAmt":self.totRemServAmt,
                 "RedlvrMktOprLVGChk":self.RedlvrMktOprLVGChk,
                 "totRedlvrMktOprLVGAmt":self.totRedlvrMktOprLVGAmt
                 },
                 "SupplierOfImpLVG":{
                 "OwnImpLVGChk":self.OwnImpLVGChk,
                 "totOwnImpLVGAmt":self.totOwnImpLVGAmt
                 },
                 "igdScheme":{
                 "defImpPayableAmt":self.defImpPayableAmt,
                 "defTotalGoodsImp":self.defTotalGoodsImp
                 },
            "declaration": {
                "declareTrueCompleteChk": self.declareTrueCompleteChk,
                "declareIncRtnFalseInfoChk": self.declareIncRtnFalseInfoChk,
                "declarantDesgtn": self.declarantDesgtn,
                "contactPerson": self.contactPerson,
                "contactNumber": self.contactNumber,
                "contactEmail": self.contactEmail
            },
            "reasons": {
                "grp1BadDebtRecoveryChk": self.grp1BadDebtRecoveryChk,
                "grp1PriorToRegChk": self.grp1PriorToRegChk,
                "grp1OtherReasonChk": self.grp1OtherReasonChk,
                "grp1OtherReasons": self.grp1OtherReasons or "",
                "grp2TouristRefundChk": self.grp2TouristRefundChk,
                "grp2AppvBadDebtReliefChk": self.grp2AppvBadDebtReliefChk,
                "grp2CreditNotesChk": self.grp2CreditNotesChk,
                "grp2OtherReasonsChk": self.grp2OtherReasonsChk,
                "grp2OtherReasons": self.grp2OtherReasons or "",
                "grp3CreditNotesChk": self.grp3CreditNotesChk,
                "grp3OtherReasonsChk": self.grp3OtherReasonsChk,
                "grp3OtherReasons": self.grp3OtherReasons or ""
            },
        }

        self.write({'json_iras':json.dumps(data)})
        return data

    def autosubmit_gst_data(self):
        print("\nautosubmit_gst_data() >>>>>")
        if not self.access_token:
            return self.action_submit()
        ctx = self._context
        config_params = self.env['ir.config_parameter'].sudo()
        headers = {
            'Accept': 'application/json',
            'Content-type': 'application/json',
            'X-IBM-Client-Id': config_params.get_param('iras_apikey'),
            'X-IBM-Client-Secret': config_params.get_param('iras_apisecret'),
            'access_token': self.access_token
        }
        data = self.generate_json_request()
        url = config_params.get_param('gstreturns_f5f8_endpoint')
        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        res_data = json.loads(response.text)
        print("res_data ====",res_data)
        if res_data.get('returnCode'):
            if res_data['returnCode'] == '10':
                self.message_post(body="Submission successful.\n" + json.dumps(res_data))
                self.write({
                    'state': 'submitted',                            
                    'ackNo': res_data["data"]["filingInfo"]["ackNo"],
                    'pymtRefNo': res_data["data"]["filingInfo"]["pymtRefNo"],
                    'totValueSupply': res_data["data"]["supplies"]["totValueSupply"] and float(res_data["data"]["supplies"]["totValueSupply"]) or 0,
                    'defNetGst': res_data["data"]["igdScheme"]["defNetGst"] and float(res_data["data"]["igdScheme"]["defNetGst"]) or 0,
                    'defTotalTaxAmt': res_data["data"]["igdScheme"]["defTotalTaxAmt"] and float(res_data["data"]["igdScheme"]["defTotalTaxAmt"]) or 0,
                    'json_response': json.dumps(res_data),
                })
                if not ctx.get('force_submit'):
                    return {'message': 'Submission successful'}
            else:
                self.message_post(body="Submission failure.\n" + json.dumps(res_data))
                if not ctx.get('force_submit'):
                    return {'message': ('Error with returnCode: ' + str(res_data['returnCode']))}
                else:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': ('Error with returnCode: ' + str(res_data['returnCode'])),
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

    def gst_summary(self):
        module = self.env['ir.module.module'].search([('name', '=', 'ks_dynamic_financial_report'), ('state', '=', 'installed')], limit=1)
        if not module:
            raise UserError(f'The module "ks_dynamic_financial_report" is not installed. Please install it to proceed. Contact your Administrator')

        tax_sheet_config_obj = self.env.ref('ks_dynamic_financial_report.ks_df_tax_report')

        target_move = self.company_id.target_moves
        if target_move == 'posted':
            ks_posted_entries = True
        else:
            ks_posted_entries = False

        tax_sheet_config_obj = self.env.ref('ks_dynamic_financial_report.ks_df_tax_report')

        # ctx = {'external_call_tax': 
        #         {'date': 
        #             {'ks_interval_type': 'quarter', 'ks_process': 'range', 'ks_range_constrain': False, 'ks_start_date': str(self.dtPeriodStart), 'ks_end_date': str(self.dtPeriodEnd), 'ks_filter': 'this_quarter'}, 
        #             'ks_posted_entries': ks_posted_entries}}

        ctx = {'external_call_tax': 
                {'date':
                    {'ks_interval_type': 'custom', 'ks_process': 'range', 'ks_range_constrain': False, 'ks_start_date': str(self.dtPeriodStart), 'ks_end_date': str(self.dtPeriodEnd), 'ks_filter': 'custom'}, 
                    'ks_posted_entries': ks_posted_entries}}
        # ctx = {}
        ctx.update({'model': 'ks.dynamic.financial.reports', 'id': tax_sheet_config_obj.id})
        return {
            'name': 'Tax Report',
            'type': 'ir.actions.client',
            'tag': 'ks_dynamic_report',
            'res_model': 'ks_dynamic_financial_report.ks_df_tax_report_action',
            'target': 'current',
            'context': ctx,
            'binding_model_id': None,
            'binding_type': 'action',
            'binding_view_types': 'list,form',
        }

    def fetch_details(self):
        """The data is fetched from the Dynamic reports (tax Report) and general Ledger. """
        module = self.env['ir.module.module'].search([('name', '=', 'ks_dynamic_financial_report'), ('state', '=', 'installed')], limit=1)
        if not module:
            raise UserError(f'The module "ks_dynamic_financial_report" is not installed. Please install it to proceed. Contact your Administrator')

        target_move = self.company_id.target_moves
        print("target_move ==",target_move)
        if target_move == 'posted':
            ks_posted_entries = True
        else:
            ks_posted_entries = False

        tax_sheet_config_obj = self.env.ref('ks_dynamic_financial_report.ks_df_tax_report')

        result = tax_sheet_config_obj.with_context({'external_call_tax': 
            {'date': 
                {'ks_string': 'Quarter', 'ks_interval_type': 'quarter', 'ks_process': 'range', 'ks_range_constrain': False, 'ks_start_date': str(self.dtPeriodStart), 'ks_end_date': str(self.dtPeriodEnd), 'ks_filter': 'this_quarter'}, 'ks_posted_entries': ks_posted_entries}}).ks_get_dynamic_fin_info(False, {})

        totStdSupply, totZeroSupply, totExemptSupply, totTaxPurchase = 0.0, 0.0, 0.0, 0.0
        outputTaxDue, inputTaxRefund = 0.0, 0.0

        filtered_list = [dic for dic in result['ks_report_lines'] if 'id' in dic]
        for dic in filtered_list:
            tax_obj = self.env['account.tax'].browse(dic['id'])
            if tax_obj.type_tax_use == 'sale' and tax_obj.for_IRAS:
                if tax_obj.iras_supplies_type == 'standard' and dic['balance_cmp'][0][0]['ks_com_net'] > 0:
                    totStdSupply += dic['balance_cmp'][0][0]['ks_com_net']
                    outputTaxDue += dic['balance_cmp'][0][1]['ks_com_tax']
                elif tax_obj.iras_supplies_type == 'zerorated' and dic['balance_cmp'][0][0]['ks_com_net'] > 0:
                    totZeroSupply += dic['balance_cmp'][0][0]['ks_com_net']
                    outputTaxDue += dic['balance_cmp'][0][1]['ks_com_tax']
                elif tax_obj.iras_supplies_type == 'exempt' and dic['balance_cmp'][0][0]['ks_com_net'] > 0:
                    totExemptSupply += dic['balance_cmp'][0][0]['ks_com_net']
                    outputTaxDue += dic['balance_cmp'][0][1]['ks_com_tax']
            elif tax_obj.type_tax_use == 'purchase' and dic['balance_cmp'][0][0]['ks_com_net'] > 0:
                totTaxPurchase += dic['balance_cmp'][0][0]['ks_com_net']
                inputTaxRefund += dic['balance_cmp'][0][1]['ks_com_tax']

        totRevenue = 0.0
        # accounts = self.env['account.account'].search([('company_id','=',self.company_id.id),('iras_mapping_ids','in',[self.env.ref('metroerp_iras.demo_data_1').id])])
        # if accounts:
        #     data = {
        #         'init_balance': False,
        #         'sortby': 'sort_date',
        #         'display_account': 'movement',
        #         'form': {
        #             'used_context': {
        #                 'journal_ids': self.env['account.journal'].search([]).ids, 
        #                 'state': target_move,
        #                 'date_from': str(self.dtPeriodStart),
        #                 'date_to': str(self.dtPeriodEnd), 
        #                 'strict_range': True, 
        #                 'company_id': self.company_id.id, 
        #                 'lang': 'en_US'
        #             }
        #         }
        #     }

        #     account_res = self._get_account_general_ledger(accounts, data)
        #     for account_dic in account_res:
        #         totRevenue += account_dic['balance']
        self.write({
            'totStdSupply': totStdSupply,
            'totZeroSupply': totZeroSupply,
            'totExemptSupply': totExemptSupply,
            'totTaxPurchase': totTaxPurchase,
            'outputTaxDue': outputTaxDue,
            'inputTaxRefund': inputTaxRefund,
            'revenue': str(int(abs(totStdSupply + totZeroSupply + totExemptSupply))),
            'is_fetched': True
        })

    def fetch_details_OLD(self):
        config_params = self.env['ir.config_parameter'].sudo()
        target_move = self.company_id.target_moves

        options = {
            'date_from': self.dtPeriodStart, 
            'date_to': self.dtPeriodEnd, 
            'journal_ids': [], 
            'target_move': target_move, 
            'company_id': [self.company_id.id, self.company_id.name], 
            'used_context': {
                'journal_ids': False, 
                'state': target_move, 
                'date_from': self.dtPeriodStart, 
                'date_to': self.dtPeriodEnd, 
                'strict_range': True, 
                'company_id': self.company_id.id, 
                'lang': 'en_US'
            }}
        result = self.get_lines(options)

        totStdSupply, totZeroSupply, totExemptSupply, totTaxPurchase = 0.0, 0.0, 0.0, 0.0
        outputTaxDue, inputTaxRefund = 0.0, 0.0
        for tax in self.env['account.tax'].search([('for_IRAS','=',True),('iras_supplies_type','=','standard')]):
            for dic in result['sale']:
                if dic['id'] == tax.id:
                    totStdSupply += dic['net']
                    outputTaxDue += dic['tax']

        for tax in self.env['account.tax'].search([('for_IRAS','=',True),('iras_supplies_type','=','zerorated')]):
            for dic in result['sale']:
                if dic['id'] == tax.id:
                    totZeroSupply += dic['net']

        for tax in self.env['account.tax'].search([('for_IRAS','=',True),('iras_supplies_type','=','exempt')]):
            for dic in result['sale']:
                if dic['id'] == tax.id:
                    totExemptSupply += dic['net']

        for dic in result['purchase']:
            totTaxPurchase += dic['net']
            inputTaxRefund += dic['tax']

        totRevenue = 0.0
        accounts = self.env['account.account'].search([('company_id','=',self.company_id.id),('iras_mapping_ids','in',[self.env.ref('metroerp_iras.demo_data_1').id])])
        if accounts:
            data = {
                'init_balance': False,
                'sortby': 'sort_date',
                'display_account': 'movement',
                'form': {
                    'used_context': {
                        'journal_ids': self.env['account.journal'].search([]).ids, 
                        'state': target_move,
                        'date_from': str(self.dtPeriodStart),
                        'date_to': str(self.dtPeriodEnd), 
                        'strict_range': True, 
                        'company_id': self.company_id.id, 
                        'lang': 'en_US'
                    }
                }
            }

            print("\ndata ===",data)

            account_res = self._get_account_general_ledger(accounts, data)
            print("\naccount_res =====",account_res)
            for account_dic in account_res:
                totRevenue += account_dic['balance']
        self.write({
            'totStdSupply': totStdSupply,
            'totZeroSupply': totZeroSupply,
            'totExemptSupply': totExemptSupply,
            'totTaxPurchase': totTaxPurchase,
            'outputTaxDue': outputTaxDue,
            'inputTaxRefund': inputTaxRefund,
            'revenue': str(int(abs(totRevenue)))
        })


    def _sql_from_amls_one(self):
        sql = """SELECT "account_move_line".tax_line_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0)
                    FROM %s
                    WHERE %s AND "account_move_line".tax_exigible GROUP BY "account_move_line".tax_line_id"""
        return sql

    def _sql_from_amls_two(self):
        sql = """SELECT r.account_tax_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0)
                 FROM %s
                 INNER JOIN account_move_line_account_tax_rel r ON ("account_move_line".id = r.account_move_line_id)
                 INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                 WHERE %s AND "account_move_line".tax_exigible GROUP BY r.account_tax_id"""
        return sql

    def _compute_from_amls(self, options, taxes):
        #compute the tax amount
        sql = self._sql_from_amls_one()
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        query = sql % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['tax'] = abs(result[1])

        #compute the net amount
        sql2 = self._sql_from_amls_two()
        query = sql2 % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['net'] = abs(result[1])

    @api.model
    def get_lines(self, options):
        taxes = {}
        for tax in self.env['account.tax'].search([('type_tax_use', '!=', 'none')]):
            if tax.children_tax_ids:
                for child in tax.children_tax_ids:
                    if child.type_tax_use != 'none':
                        continue
                    taxes[child.id] = {'id': child.id, 'tax': 0, 'net': 0, 'name': child.name, 'type': tax.type_tax_use}
            else:
                taxes[tax.id] = {'id': tax.id, 'tax': 0, 'net': 0, 'name': tax.name, 'type': tax.type_tax_use}
        self.with_context(date_from=options['date_from'], date_to=options['date_to'],
                          state=options['target_move'],
                          strict_range=True)._compute_from_amls(options, taxes)
        groups = dict((tp, []) for tp in ['sale', 'purchase'])
        for tax in taxes.values():
            if tax['tax']:
                groups[tax['type']].append(tax)
        return groups
    
    def action_generate_acknowledgment_report(self):
        return self.env.ref('metroerp_iras.action_report_gst_f5f8').report_action(self, config=False)

class FetchIras(models.Model):
    _name = 'fetch.iras.details'

