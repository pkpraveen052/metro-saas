from odoo import fields, models,_,api


class PrefillStatusWizard(models.TransientModel):
    _name = 'invoice.response.prefill.status'
    _description = 'Invoice Response Prefill Status Wizard'

    response_code = fields.Selection([('AB','Message acknowledgement'), ('AP','Accepted'),('RE','Rejected'), ('IP','In process'),('UQ','Under query'),
                                    ('CA','Conditionally accepted'),('PD','Paid')], string="Response Code", required=True)
    message = fields.Text(readonly=True)
    
    @api.onchange('response_code')
    def status_code_message(self):
        for rec in self:
            if rec.response_code == 'AB':
                rec.message = "Indicates that an acknowledgement relating to receipt of message or transaction is required."
            elif rec.response_code == 'AP':
                rec.message = "Indication that the referenced offer or transaction has been accepted."
            elif rec.response_code == 'RE':
                rec.message = "Indication that the referenced offer or transaction is not accepted."
            elif rec.response_code == 'IP':
                rec.message = "Indicates that the referenced message or transaction is being processed."
            elif rec.response_code == 'UQ':
                rec.message = "Indicates that the processing of the referenced message has been halted pending response to a query."
            elif rec.response_code == 'CA':
                rec.message = "Indication that the referenced offer or transaction has been accepted under conditions indicated in this message."
            elif rec.response_code == 'PD':
                rec.message = "Indicates that the referenced document or transaction has been paid."
    
    def action_invoice_response_queue_out(self):
        ctx = self._context or {}
        active_obj = self.env[ctx.get('active_model')].browse(ctx.get('active_id'))
        sender_party_contact_name, sender_party_contact_telephone, sender_party_contact_email = False, False, False

        print("active_obj.company_id = ",active_obj.company_id)
        print("active_obj.company_id.child_ids =",active_obj.company_id.child_ids)
        if active_obj.company_id and active_obj.company_id.partner_id.child_ids:
            print("active_obj.company_id.child_ids.filtered(lambda x:x.type == 'contact') ==",active_obj.company_id.partner_id.child_ids.filtered(lambda x:x.type == 'contact'))
            contact_obj = active_obj.company_id.partner_id.child_ids.filtered(lambda x:x.type == 'contact')[0]
            if contact_obj:
                sender_party_contact_name = contact_obj.name
                sender_party_contact_telephone = contact_obj.phone or contact_obj.mobile
                sender_party_contact_email = contact_obj.email

        action = {
            'name': _('Response'),
            'type': 'ir.actions.act_window',
            'res_model': 'invoice.responses.queue.out',
            'context': {
                'default_response_code': self.response_code,
                'default_source_doc_id': active_obj.id,
                'default_inv_no': active_obj.invoice_no,
                'default_inv_issue_date': active_obj.issue_date,
                'default_doc_type_code': active_obj.doc_type_code,
                'default_doc_type': active_obj.doc_type,
                'default_sender_party_id': active_obj.extracted_receiverid,
                'default_sender_party_name': active_obj.company_id.name,
                'default_receiver_party_id': active_obj.extracted_senderid,
                'default_receiver_party_name': active_obj.sender_party_name,
                'default_company_id': active_obj.company_id and active_obj.company_id.id or False,
                'default_sender_party_contact_name': sender_party_contact_name,
                'default_sender_party_contact_telephone': sender_party_contact_telephone,
                'default_sender_party_contact_email': sender_party_contact_email
            },
            'view_mode': 'form', 
        }
        return action
