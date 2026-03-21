# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models,_
import logging
_logger = logging.getLogger(__name__)
from odoo.addons.base.models.ir_mail_server import MailDeliveryException

class MailMessage(models.Model):
    _inherit = "mail.message"

    company_id = fields.Many2one("res.company", "Company")

    
    @api.model_create_multi
    def create(self, values_list):
        for vals in values_list:
            # Set company_id from related record if available
            if vals.get("model") and vals.get("res_id"):
                current_object = self.env[vals["model"]].browse(vals["res_id"])
                if hasattr(current_object, "company_id") and current_object.company_id:
                    vals["company_id"] = current_object.company_id.id

            if not vals.get("company_id"):
                vals["company_id"] = self.env.company.id

            # Handle mail server selection
            if not vals.get("mail_server_id"):
                mail_server = self.env["ir.mail_server"].sudo().search(
                    [("company_id", "=", vals["company_id"])],
                    order="sequence",
                    limit=1
                )

                if not mail_server:
                    mail_server = self.env["ir.mail_server"].sudo().search(
                        [("company_id", "=", False)],
                        order="sequence",
                        limit=1
                    )

                if mail_server:
                    vals["mail_server_id"] = mail_server.id
                else:
                    vals["mail_server_id"] = False  # This could prevent sending — you may choose to raise warning

        return super(MailMessage, self).create(values_list)
    


class MailMail(models.Model):
    _inherit = "mail.mail"

    #Overriden existing method
    def send(self, auto_commit=False, raise_exception=False):
        """ Safely sends emails with company-based SMTP selection and batching. """
        for server_id, batch_ids in self._split_by_server():
            smtp_session = None
            try:
                # Fetch company-based mail server
                mail_sample = self.browse(batch_ids[0])  # use first mail for company info
                company = mail_sample.company_id

                mail_server = None
                if company:
                    mail_server = self.env['ir.mail_server'].sudo().search(
                        [('company_id', '=', company.id)], limit=1
                    )
                    if not mail_server:
                        mail_server = self.env['ir.mail_server'].sudo().search(
                            [('company_id', '=', False)], order='sequence ASC', limit=1
                        )
                else:
                    mail_server = self.env['ir.mail_server'].sudo().search(
                        [('company_id', '=', False)], order='sequence ASC', limit=1
                    )

                if not mail_server:
                    batch = self.browse(batch_ids)
                    batch.write({'state': 'exception', 'failure_reason': _('No suitable SMTP server found.')})
                    batch._postprocess_sent_message(success_pids=[], failure_type="SMTP")
                    continue

                smtp_session = self.env['ir.mail_server'].connect(mail_server_id=mail_server.id)

                self.browse(batch_ids)._send(
                    auto_commit=auto_commit,
                    raise_exception=raise_exception,
                    smtp_session=smtp_session
                )

            except Exception as exc:
                batch = self.browse(batch_ids)
                batch.write({'state': 'exception', 'failure_reason': str(exc)})
                batch._postprocess_sent_message(success_pids=[], failure_type="SMTP")
                if raise_exception:
                    raise MailDeliveryException(_('Unable to send email'), exc)

            finally:
                if smtp_session:
                    smtp_session.quit()
