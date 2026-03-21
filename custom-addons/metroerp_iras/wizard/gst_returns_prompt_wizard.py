from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError

class gstReturnsPromptWizard(models.TransientModel):
    _name = "gst.returns.prompt.wizard"
    _description = "GST Returns Prompt"

    message_content = fields.Text(string="Message Content")
    gstOnBadDebtRecoveryChk = fields.Boolean(string="GST On Bad Debt Recovery")
    gstCollectedPriorToRegistrationChk = fields.Boolean(string="GST collected prior to registration")
    otherReasonsChk = fields.Boolean(string="Others, please specify reasons")
    touristRefundChk = fields.Boolean(string="Tourist Refund")
    badDebtsReliefChk = fields.Boolean(string="Bad Debts Relief")
    creditNotesChk = fields.Boolean(string="Credit Notes")
    others_reason = fields.Text(string="Other Reason")
    set_others_readonly = fields.Boolean()

    @api.onchange('others_reason')
    def onchange_others_reason(self):
        print("\nonchange_others_reason() >>>>")
        if self.others_reason:
            self.set_others_readonly = True
        else:
            self.set_others_readonly = False

    @api.onchange('otherReasonsChk')
    def onchange_otherReasonsChk(self):
        print("\nonchange_otherReasonsChk() >>>>")
        if self.otherReasonsChk == True:
            self.gstOnBadDebtRecoveryChk = False
            self.gstCollectedPriorToRegistrationChk = False
            self.touristRefundChk = False
            self.badDebtsReliefChk = False
            self.creditNotesChk = False
            self.others_reason = False


    def process_sn_7_8_9_10(self):
        ctx = self._context
        print("process_sn_7_8_9_10()....",ctx)
        active_id = self.env.context.get('active_id')
        if ctx.get('active_model') == 'gst.returns.f5f8':
            gst_obj = self.env['gst.returns.f5f8'].browse(active_id)
        else:
            gst_obj = self.env['gst.returns.f7'].browse(active_id)
        if self.gstOnBadDebtRecoveryChk == False and self.gstCollectedPriorToRegistrationChk == False and self.otherReasonsChk == False:
            raise UserError(_("You have not specified the reasons."))
        if self.gstOnBadDebtRecoveryChk == True:
            gst_obj.write({'grp1BadDebtRecoveryChk':True})
        if self.gstCollectedPriorToRegistrationChk == True:
            gst_obj.write({'grp1PriorToRegChk': True})
        if self.otherReasonsChk == True:
            gst_obj.write({'grp1OtherReasonChk': True})
        if self.others_reason:
            gst_obj.write({'grp1OtherReasons': self.others_reason})

    def action_proceed_sn7(self):
        ctx = self._context
        print("action_proceed_sn7()....",self._context)
        active_id = self.env.context.get('active_id')        
        self.process_sn_7_8_9_10()
        if ctx.get('active_model') == 'gst.returns.f5f8':
            gst_obj = self.env['gst.returns.f5f8'].browse(active_id)
        else:
            gst_obj = self.env['gst.returns.f7'].browse(active_id)
        gst_obj.write({'validation_sn7_done': True})        


    def action_proceed_sn8(self):
        print("action_proceed_sn8()....")
        ctx = self._context
        self.process_sn_7_8_9_10()
        active_id = ctx.get('active_id')
        if ctx.get('active_model') == 'gst.returns.f5f8':
            gst_obj = self.env['gst.returns.f5f8'].browse(active_id)
        else:
            gst_obj = self.env['gst.returns.f7'].browse(active_id)
        gst_obj.write({'validation_sn8_done': True})

    def action_proceed_sn9(self):
        print("action_proceed_sn9()....")
        ctx = self._context
        self.process_sn_7_8_9_10()
        active_id = ctx.get('active_id')
        if ctx.get('active_model') == 'gst.returns.f5f8':
            gst_obj = self.env['gst.returns.f5f8'].browse(active_id)
        else:
            gst_obj = self.env['gst.returns.f7'].browse(active_id)
        gst_obj.write({'validation_sn9_done': True})

    def action_proceed_sn10(self):
        print("action_proceed_sn10()....")
        ctx = self._context
        self.process_sn_7_8_9_10()
        active_id = ctx.get('active_id')
        if ctx.get('active_model') == 'gst.returns.f5f8':
            gst_obj = self.env['gst.returns.f5f8'].browse(active_id)
        else:
            gst_obj = self.env['gst.returns.f7'].browse(active_id)
        gst_obj.write({'validation_sn10_done': True})

    def process_sn_11_12_13(self):
        ctx = self._context
        print("process_sn_11_12_13()....",ctx)
        active_id = self.env.context.get('active_id')
        if ctx.get('active_model') == 'gst.returns.f5f8':
            gst_obj = self.env['gst.returns.f5f8'].browse(active_id)
        else:
            gst_obj = self.env['gst.returns.f7'].browse(active_id)
        if self.touristRefundChk == False and self.badDebtsReliefChk == False and self.creditNotesChk == False and self.otherReasonsChk == False:
            raise UserError(_("You have not specified the reasons."))
        if self.touristRefundChk == True:
            gst_obj.write({'grp2TouristRefundChk': True})
        if self.badDebtsReliefChk == True:
            gst_obj.write({'grp2AppvBadDebtReliefChk': True})
        if self.creditNotesChk == True:
            gst_obj.write({'grp2CreditNotesChk': True})
        if self.otherReasonsChk == True:
            gst_obj.write({'grp2OtherReasonsChk': True})
        if self.others_reason:
            gst_obj.write({'grp2OtherReasons': self.others_reason})

    def action_proceed_sn11(self):
        print("action_proceed_sn11()....")
        ctx = self._context
        self.process_sn_11_12_13()
        active_id = ctx.get('active_id')
        if ctx.get('active_model') == 'gst.returns.f5f8':
            gst_obj = self.env['gst.returns.f5f8'].browse(active_id)
        else:
            gst_obj = self.env['gst.returns.f7'].browse(active_id)
        gst_obj.write({'validation_sn11_done': True})

    def action_proceed_sn12(self):
        print("action_proceed_sn12()....")
        ctx = self._context
        self.process_sn_11_12_13()
        active_id = ctx.get('active_id')
        if ctx.get('active_model') == 'gst.returns.f5f8':
            gst_obj = self.env['gst.returns.f5f8'].browse(active_id)
        else:
            gst_obj = self.env['gst.returns.f7'].browse(active_id)
        gst_obj.write({'validation_sn12_done': True})

    def action_proceed_sn13(self):
        print("action_proceed_sn13()....")
        ctx = self._context
        
        self.process_sn_11_12_13()
        active_id = ctx.get('active_id')
        if ctx.get('active_model') == 'gst.returns.f5f8':
            gst_obj = self.env['gst.returns.f5f8'].browse(active_id)
        else:
            gst_obj = self.env['gst.returns.f7'].browse(active_id)
        gst_obj.write({'validation_sn13_done': True})

    def action_proceed_sn14(self):
        print("action_proceed_sn14()....")
        ctx = self._context
        active_id = ctx.get('active_id')
        if ctx.get('active_model') == 'gst.returns.f5f8':
            gst_obj = self.env['gst.returns.f5f8'].browse(active_id)
        else:
            gst_obj = self.env['gst.returns.f7'].browse(active_id)
        if self.creditNotesChk == False and self.otherReasonsChk == False:
            raise UserError(_("You have not specified the reasons."))
        if self.creditNotesChk == True:
            gst_obj.write({'grp3CreditNotesChk': True})
        if self.otherReasonsChk == True:
            gst_obj.write({'grp3OtherReasonsChk': True})
        if self.others_reason:
            gst_obj.write({'grp3OtherReasons': self.others_reason})
        gst_obj.write({'validation_sn14_done': True})

    # def action_proceed_sn_f7_11_12_13(self):
    #     active_id = self.env.context.get('active_id')
    #     gst_obj = self.env['gst.returns.f7'].browse(active_id)
    #     if self.touristRefundChk == False and self.badDebtsReliefChk == False and self.creditNotesChk == False and self.otherReasonsChk == False:
    #         raise UserError(_("You have not specified the reasons."))
    #     if self.touristRefundChk == True:
    #         gst_obj.write({'grp2TouristRefundChk': True})
    #     if self.badDebtsReliefChk == True:
    #         gst_obj.write({'grp2AppvBadDebtReliefChk': True})
    #     if self.creditNotesChk == True:
    #         gst_obj.write({'grp2CreditNotesChk': True})
    #     if self.otherReasonsChk == True:
    #         gst_obj.write({'grp2OtherReasonsChk': True})
    #     if self.others_reason:
    #         gst_obj.write({'grp2OtherReasons': self.others_reason})
            
    # def action_proceed_f7_sn16(self):
    #     active_id = self.env.context.get('active_id')
    #     gst_obj = self.env['gst.returns.f7'].browse(active_id)
    #     self.action_proceed_sn_f7_11_12_13()
    #     gst_obj.write({'validation_sn16_done': True})

    # def action_proceed_sn17(self):
    #     active_id = self.env.context.get('active_id')
    #     gst_obj = self.env['gst.returns.f7'].browse(active_id)
    #     if self.creditNotesChk == False and self.otherReasonsChk == False:
    #         raise UserError(_("You have not specified the reasons."))
    #     if self.creditNotesChk == True:
    #         gst_obj.write({'grp3CreditNotesChk': True})
    #     if self.otherReasonsChk == True:
    #         gst_obj.write({'grp3OtherReasonsChk': True})
    #     if self.others_reason:
    #         gst_obj.write({'grp3OtherReasons': self.others_reason})
    #     gst_obj.write({'validation_sn14_done': True})