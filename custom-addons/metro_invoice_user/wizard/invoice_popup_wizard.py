from odoo import models, fields

class InvoicePopupWizard(models.TransientModel):
    _name = 'invoice.popup.wizard'
    _description = 'Invoice Feature Popup'

    message = fields.Html(default="""
        <div style="font-size:15px;">
        <p><b>This feature is not available in the free InvoiceNow solution.</b></p>
        <p>
        To avail this function, kindly whatsapp us at
        <a href="https://wa.me/65323242342" target="_blank">+65323242342</a>
        </p>
        <p>
        or email
        <a href="mailto:sales@metrogroup.solutions">sales@metrogroup.solutions</a>
        </p>
        </div>
    """)