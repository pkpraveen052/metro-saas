from odoo import models, fields, api,_
from odoo.exceptions import UserError, AccessError      

class GstReturnsF5F8Inherit(models.Model):
    _inherit = 'gst.returns.f5f8'
    
 
    @api.model
    def create(self, vals):
        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user'):
            raise UserError(_(
                        "This feature is not available in the free InvoiceNow solution.\n\n"
                        "To avail this function:\n"
                        "WhatsApp: +65323242342\n"
                        "Email: sales@metrogroup.solutions"
                    ))

        return super(GstReturnsF5F8Inherit, self).create(vals)



class GstReturnsF7Inherit(models.Model):
    _inherit = 'gst.returns.f7'
    
 
    @api.model
    def create(self, vals):
        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user'):
            raise UserError(_(
                        "This feature is not available in the free InvoiceNow solution.\n\n"
                        "To avail this function:\n"
                        "WhatsApp: +65323242342\n"
                        "Email: sales@metrogroup.solutions"
                    ))

        return super(GstReturnsF7Inherit, self).create(vals)
    

class FormCs(models.Model):
    _inherit = 'form.cs'
    
 
    @api.model
    def create(self, vals):
        if self.env.user.has_group('metro_invoice_user.group_account_invoice_user'):
            raise UserError(_(
                        "This feature is not available in the free InvoiceNow solution.\n\n"
                        "To avail this function:\n"
                        "WhatsApp: +65323242342\n"
                        "Email: sales@metrogroup.solutions"
                    ))

        return super(FormCs, self).create(vals)
