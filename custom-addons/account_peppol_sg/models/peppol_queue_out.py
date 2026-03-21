import base64
import hashlib
import hmac
import json
import logging
import requests
import traceback
from collections import defaultdict
from odoo.exceptions import UserError, ValidationError

from odoo import api, models, fields, _
from odoo.addons.iap.tools.iap_tools import InsufficientCreditError
logger = logging.getLogger(__name__)

SELECTION_PEPPOL_QUEUE_OUT_STATE = [
    ('pending', 'Pending'),
    ('sent', 'Sent'),
    ('done', 'Complete'),
    ('error', 'Failed'),
    ('cancelled', 'Cancelled'),
]

TIMEOUT = 20


class PeppolQueueOut(models.Model):
    _name = "peppol.queue.out"
    _description = "PEPPOL Outgoing Queue"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date desc, id desc"

    name = fields.Char(string="Name", compute="_compute_name", store=True)
    mode = fields.Selection([('test', 'test'), ('live', 'live')], string="Mode", readonly=True)
    document_id = fields.Integer(string="Document ID", readonly=True)
    company_id = fields.Many2one('res.company', string="Company", compute="_compute_company", store=True)
    sent = fields.Boolean(string="Sent", readonly=True)
    invoice_id = fields.Many2one("account.move", string="Invoice")
    partner_id = fields.Many2one('res.partner', related='invoice_id.partner_id', string='Customer', store=True)
    invoice_type = fields.Selection(selection=[
        ('out_invoice', 'Customer Invoice'),
        ('out_refund', 'Customer Credit Note'),
        ('in_invoice', 'Vendor Bill'),
        ('in_refund', 'Vendor Credit Note'),
    ], string='Type', required=True)
    state = fields.Selection(SELECTION_PEPPOL_QUEUE_OUT_STATE, string="Status", default='pending', readonly=True,
                             tracking=1, index=True)
    guid = fields.Char('GUID', readonly=True, help="Globally Unique Identifier")
    event = fields.Char('Event', tracking=1, help="The overall status for this Invoice Submission")
    show_invoice_submission_evidence = fields.Boolean("Show Invoice Submission Evidence (Technical field)")
    invoice_submission_evidence_action_ids = fields.One2many("invoice.submission.action.evidence", "queue_id",
                                                             string="Invoice Submission Action Evidence",
                                                             help="Get evidence for an InvoiceSubmission by GUID with "
                                                                  "corresponding status")
    attachment_ids = fields.Many2many('ir.attachment', 'queue_id', 'attachment_id', string='Documents')
    evidence_sender_identifier = fields.Char('Sender')
    evidence_receiver_identifier = fields.Char('Receiver')
    evidence_network = fields.Char('Network')
    evidence_document_ids = fields.Many2many('ir.attachment', 'queue_out_attachment_rel', 'queue_id', 'attachment_id',
                                             string='Document Submission Evidence Documents')

    _sql_constraints = [
        (
            'mode_document_unique',
            'UNIQUE(invoice_id)',
            'Can only send single Document to PEPPOL once.',
        ),
    ]

    @api.depends('invoice_id')
    def _compute_name(self):
        for entry in self:
            entry.name = "%s" % entry.invoice_id.name

    @api.depends('invoice_id')
    def _compute_company(self):
        for entry in self:
            document = entry.invoice_id
            try:
                company = document and document.company_id or None
            except AttributeError:  # Document doesn't have company_id
                company = None
            entry.company_id = company

    def _add_to_queue(self, document):
        document.ensure_one()
        entry = self.search([
            ('invoice_id', '=', document.id),
        ])
        if entry:
            return entry

        report = self.env.ref('account.account_invoices')._render_qweb_pdf(document.id)
        return self.create({
            'invoice_type': document.move_type,
            'invoice_id': document.id,
            'attachment_ids': [(0, 0, {
                'type': 'binary',
                'name': document.state == 'posted' and (
                        (document.name or 'INV').replace('/', '_') + '.pdf') or 'INV.pdf',
                'datas': str(base64.b64encode(report[0]), 'UTF-8'),
                'mimetype': 'application/pdf',
                'res_model': 'peppol.queue.out',
                'res_id': document.id
            })]

        })

    def _document(self):
        self.ensure_one()

        document = None

        model_name = self.document_type_id.model_name
        if model_name and (model_name in self.env):
            document = self.env[model_name].sudo().browse(self.document_id)
            if not document.exists():
                document = None

        return document

    def _set_state(self, new_state, message=None, activity_for_error=True, raise_error=True):
        changed = self.filtered(lambda e: e.state != new_state)
        changed.write({'state': new_state})
        if message:
            for entry in changed:
                entry.message_post(body=message)
                if (new_state == 'error') and activity_for_error:
                    entry._activity_for_error()

    def _activity_for_error(self):
        self.ensure_one()

        queue_out_error_type = self.env.ref('base_peppol_sg.mail_activity_peppol_queue_out_error')

        # Only add activity if there's not already one.
        if self.activity_ids.filtered(lambda a: a.activity_type_id == queue_out_error_type):
            return

        mode = self._context.get('peppol_iap_mode') or ''

        summary = _('Error Sending Document')
        note = _(
            "An error occurred sending this document to PEPPOL in '%s' mode.\n"
            "Check the chatter for error details."
        ) % (
                   mode,
               )

        for user in self.env.user._peppol_administrators():
            self.activity_schedule(
                summary=summary,
                note=note,
                **{
                    'activity_type_id': queue_out_error_type.id,
                    'user_id': user.id,
                })

    @api.model
    def _calc_checksum(self, key, data):
        if (not key) or (not data):
            return ''

        key = key.encode('utf-8')
        data = base64.b64decode(data)
        return hmac.new(key=key, msg=data, digestmod=hashlib.sha256).hexdigest()

    def _document_data(self, account):
        """Return dict with data to send for this document.

        The values to return are:
            - sender: Document sender ID.
            - receiver: Document receiver ID.
            - content: base64 encoded document content.
        """
        self.ensure_one()

        document = self._document()

        if not hasattr(document, '_peppol_document_data_4type'):
            raise PeppolQueueError(_(
                "Can't generate document data for %s: %s."
                " Can't find method '_peppol_document_data_4type' for model '%s'.") % (
                                       self.document_type_id.name,
                                       document.display_name or '',
                                       document._description or document._name,
                                   ))
        return document._peppol_document_data_4type(account)

    @api.model
    def _find_documents(self, documents):
        mode = self.env.user.peppol_mode

        by_document_type = defaultdict(documents.browse)
        for document in documents:
            document_type = document._peppol_document_type_4type()
            by_document_type[document_type] += document

        res = self.browse()
        for document_type, documents_this_type in by_document_type.items():
            res |= self.search([
                ('mode', '=', mode),
                ('document_type_id', '=', document_type.id),
                ('document_id', 'in', documents_this_type.ids),
            ])

        return res

    def _group_by_company(self):
        """Group queue entries by company.
        """
        by_company = defaultdict(self.browse)
        for entry in self:
            document = entry._document()
            if not document:
                entry._set_state('error', _("Can't find Odoo document for this queue entry."))
                continue

            company = document._peppol_company()
            by_company[company] += entry

        return by_company

    def _send_old(self):
        Log = self.env['peppol.log']

        logs = Log.browse()
        entries_sent = self.browse()
        try:
            with self._cr.savepoint():
                # Send for live/test mode separately - send_documents request is for a single mode only.
                for send_for_mode in [m[0] for m in SELECTION_PEPPOL_MODE]:
                    to_send = self.filtered(
                        lambda e: (e.mode == send_for_mode) and (e.state == 'pending')).with_context(
                        peppol_iap_mode=send_for_mode)

                    # Group documents by company and send for each company separately using its account.
                    by_company = to_send._group_by_company()
                    for company, entries in by_company.items():
                        this_entries_sent, this_logs = entries._send_one_company(send_for_mode, company)
                        entries_sent += this_entries_sent
                        logs += this_logs

        # Because _send() is called from a cron,
        # ensure any errors raised are recorded.
        except Exception as e:
            # Trap exceptions here to prevent calling _cron job from being stopped.
            # Assume any exception getting here has prevented the request from
            # happening.

            e = PeppolConcurrencyError.check("Sending documents", e)
            if not isinstance(e, PeppolConcurrencyError):
                if not isinstance(e, PeppolError):
                    tb = traceback.format_exc()
                else:
                    tb = False
                logs += Log.log(
                    PEPPOL_LOG_TYPE_ERROR,
                    _("Error sending documents. %s") % exception_msg(e),
                    traceback=tb,
                )

        return entries_sent, logs

    def _send_one_company(self, send_for_mode, company):
        Log = self.env['peppol.log']
        Account = self.env['peppol.account']

        logs = Log.browse()
        entries_sent = self.browse()
        try:
            account = Account.get_peppol(company, send_for_mode)
            server = ServerAPI(account)
            insufficient_credits = False

            # Savepoint here to rollback if an exception is raised.
            with self._cr.savepoint():
                # Lock all queue entries. This will raise a concurrency error if any other
                # process is writing/locked any of the entries.
                #
                # WARNING: The lock is in place until this transaction is committed,
                # so it will remain in place during the serverAPI request and subsequent
                # processing.
                self._cr.execute("select id from peppol_queue_out for update nowait")
                self.write({'insufficient_credit_data': False})

            for entry in self:
                try:
                    # Savepoint here to rollback if an exception is raised.
                    with self._cr.savepoint():
                        document = entry._document()
                        if not document:
                            entry._set_state('error', _("Can't find Odoo document for this queue entry."))
                            continue

                        entries_sent += entry

                        document_data, errs = entry._document_data(account)
                        if errs:
                            raise PeppolDataError(
                                _("Can't send document %s: %s. The document has data errors:\n\n%s") % (
                                    self.document_type_id.name,
                                    document.display_name or '',
                                    '\n'.join(errs),
                                ))

                        document_data.update({
                            'odoo_document_id': entry.request_ident,
                            'document_type': entry.document_type_id.code,
                            'odoo_document_name': document.display_name,
                            'odoo_company_name': company.display_name,
                            'checksum': self._calc_checksum(account.hmac_secret, document_data.get('content')),
                        })
                        response = server.send_document(send_for_mode, document_data)

                        request_ident = response.get('odoo_document_id')
                        if not request_ident:
                            raise PeppolQueueError(_("Document send response has no Odoo document ID."))
                        if entry.request_ident != request_ident:
                            raise PeppolQueueError(
                                _("Document send response has invalid Odoo document ID. Found '%s', but expecting '%s'.") % (
                                    request_ident, entry.request_ident))

                        status_code = response.get('request_status_code')
                        status_message = response.get('request_status_message') or ''

                        error = None
                        if status_code < ERROR_STATUS_CODE:
                            entry._set_state('sent', _("Document sent OK. %s") % status_message)
                            entry.sent = True
                        elif status_code == DOCUMENT_SEND_REGISTRATION_ERROR:
                            error = _("Account registration error. %s") % status_message
                        elif status_code == DOCUMENT_SEND_SENDER_UNRECOGNISED:
                            error = _("Document sender not recognised. %s") % status_message
                        elif status_code == DOCUMENT_SEND_RECEIVER_UNRECOGNISED:
                            error = _("Document receiver not recognised. %s") % status_message
                        elif status_code == DOCUMENT_SEND_DOCUMENT_INVALID:
                            error = _("Document content not valid. %s") % status_message
                        elif status_code == DOCUMENT_SEND_AUTHENTICATION_FAILURE:
                            error = _("Document authentication not valid. %s") % status_message
                        elif status_code == DOCUMENT_SEND_IAP_INSUFFICIENT_CREDITS:
                            insufficient_credits = True
                            # For insufficient credits the status_message has json encoded data to be forwarded to
                            # Odoo for purchasing more credits. If multiple docs rejected due to insufficient
                            # credits they should all have the same status_message details because they were
                            # all rejected as part of the same request.
                            entry.insufficient_credit_data = status_message
                            error = _(
                                "Insufficient credits available on Odoo In App Purchases account '%s'. Please purchase additional credits.") % account.display_name
                        else:
                            error = _("Error sending document (%s). %s") % ((status_code or ''), status_message)

                        if error:
                            entry._set_state('error', error)
                            logs += Log.log(
                                PEPPOL_LOG_TYPE_ERROR,
                                error,
                                queue_out_entry=entry,
                            )
                except Exception as e:
                    # This exception is raised while handling a single document. Log the error and continue.
                    e = PeppolConcurrencyError.check("Sending documents", e)
                    if not isinstance(e, PeppolConcurrencyError):
                        if not isinstance(e, PeppolError):
                            tb = traceback.format_exc()
                        else:
                            tb = False
                        logs += Log.log(
                            PEPPOL_LOG_TYPE_ERROR,
                            _("Error sending document for outgoing queue entry '%s' (id=%s).\n"
                              "%s") % (
                                entry.display_name,
                                entry.id,
                                exception_msg(e),
                            ),
                            queue_out_entry=entry,
                            traceback=tb,
                        )
            if insufficient_credits:
                account._activity_for_insufficient_credits(send_for_mode)
        except Exception as e:
            # Trap exceptions here to prevent calling _cron job from being stopped.
            # Assume any exception getting here has prevented the request from
            # happening. Exceptions during response processing are captured by
            # the response loop.

            e = PeppolConcurrencyError.check("Sending documents", e)
            if not isinstance(e, PeppolConcurrencyError):
                if not isinstance(e, PeppolError):
                    tb = traceback.format_exc()
                else:
                    tb = False
                co = company and (_(" (for company: %s)") % company.display_name) or ''
                logs += Log.log(
                    PEPPOL_LOG_TYPE_ERROR,
                    _("Error sending documents%s. %s") % (co, exception_msg(e)),
                    traceback=tb,
                )

        return entries_sent, logs

    @api.model
    def _cron_send_confirm(self):
        to_confirm = self.search([('state', '=', 'sent'), ('event', '=', 'succeeded')])
        if to_confirm:
            to_confirm._confirm()

        to_send = self.search([('state', '=', 'pending')])
        if to_send:
            to_send._send()

    def _send(self):
        for obj in self:
            invoice_obj = obj.invoice_id
            access_point = self.env['peppol.access.point.sg'].search(
                [('company_id', '=', invoice_obj.company_id.id)], order="create_date")
            if not access_point:
                obj.write({'state': 'error'})
                log = _("Access Point configuration is not defined for the Company %s") % invoice_obj.company_id.name
                obj.message_post(body=log)
                continue
            end_point = access_point.endpoint
            api_key = access_point.authorization_key
            legalEntityId = invoice_obj.company_id.legal_entity_identifier

            version = invoice_obj.get_ubl_version()
            xml_string = invoice_obj.generate_ubl_xml_string(version=version)

            headers = {
                "Accept": "application/json",
                "Authorization": "Bearer {}".format(api_key),
                "Content-Type": "application/json"
            }
            data = {
                "legalEntityId": int(legalEntityId),
                "routing": {
                    "eIdentifiers": [
                        {
                            "scheme": self.env['ir.config_parameter'].sudo().get_param(
                                'electronic_address_scheme_identifier', default="SG:UEN"),
                            "id": invoice_obj.partner_id.peppol_identifier,
                        },
                    ],
                },
            }

            invoice_type = self.env['ir.config_parameter'].sudo().get_param('settings_invoice_type', 'UBL')
            if invoice_type == 'UBL':
                data.update({
                    "document": {
                        "documentType": "invoice",
                        "rawDocumentData": {
                            "document": str(base64.b64encode(xml_string), 'UTF-8'),
                            "parse": True,
                            "parseStrategy": "ubl",
                        }
                    }
                })
            else:
                invoice_dic = {
                    "invoiceNumber": invoice_obj.name,
                    "issueDate": str(invoice_obj.invoice_date),
                    "documentCurrencyCode": invoice_obj.currency_id.name,
                    "taxSystem": "tax_line_percentages",
                    "accountingCustomerParty": {
                        "party": {
                            "companyName": invoice_obj.partner_id.name,
                            "address": {
                                "country": invoice_obj.partner_id.country_id.code
                            },
                        },
                        "publicIdentifiers": [
                            {
                                "scheme": self.env['ir.config_parameter'].sudo().get_param(
                                    'electronic_address_scheme_identifier', default="SG:UEN"),
                                "id": invoice_obj.partner_id.peppol_identifier
                            }
                        ]
                    },
                }
                customer_obj = invoice_obj.partner_id
                if customer_obj.street:
                    invoice_dic["accountingCustomerParty"]["party"]["address"]["street1"] = customer_obj.street
                if customer_obj.street2:
                    invoice_dic["accountingCustomerParty"]["party"]["address"]["street2"] = customer_obj.street2
                if customer_obj.city:
                    invoice_dic["accountingCustomerParty"]["party"]["address"]["city"] = customer_obj.city
                if customer_obj.zip:
                    invoice_dic["accountingCustomerParty"]["party"]["address"]["zip"] = customer_obj.zip

                invoice_dic.update({"invoiceLines": [], "taxSubtotals": []})
                tax_subtotals = {}
                for inv_line in invoice_obj.invoice_line_ids:
                    invoice_dic["invoiceLines"].append({
                        "lineId": str(inv_line.id),
                        "description": inv_line.name,
                        "name": inv_line.product_id.name,
                        "quantity": inv_line.quantity,
                        "itemPrice": inv_line.price_unit,
                        "amountExcludingVat": inv_line.price_subtotal,
                        "tax": {
                            "percentage": inv_line.tax_ids[0].amount,
                            "category": inv_line.tax_ids[0].unece_categ_id.technical_value,
                            "country": invoice_obj.company_id.country_id.code
                        },
                    })

                    category = inv_line.tax_ids[0].unece_categ_id.technical_value
                    if inv_line.tax_ids[0].unece_categ_id.technical_value in tax_subtotals:
                        tax_subtotals[category]["taxableAmount"] += inv_line.price_subtotal
                        tax_amount = tax_subtotals[category]["taxAmount"] + round((round(inv_line.price_total, 2) - round(inv_line.price_subtotal, 2)), 2)
                        tax_subtotals[category].update({"taxAmount": tax_amount})
                    else:
                        tax_subtotals.update({
                            category: {
                                "taxableAmount": inv_line.price_subtotal,
                                "taxAmount": round((round(inv_line.price_total, 2) - round(inv_line.price_subtotal, 2)), 2),
                                "percentage": inv_line.tax_ids[0].amount,
                                "country": invoice_obj.company_id.country_id.code,
                            }
                        })

                for category, dic in tax_subtotals.items():
                    invoice_dic["taxSubtotals"].append({
                        "taxableAmount": dic["taxableAmount"],
                        "taxAmount": dic["taxAmount"],
                        "percentage": dic["percentage"],
                        "country": dic["country"],
                        "category": category,
                    })
                invoice_dic.update({
                    "amountIncludingVat": invoice_obj.amount_total
                })
                data.update({
                    "document": {
                        "documentType": "invoice",
                        "invoice": invoice_dic
                    }
                })
            report = self.env.ref('account.account_invoices')._render_qweb_pdf(invoice_obj.id)
            if report:
                data.update({
                    "attachments": [
                        {
                            "document": str(base64.b64encode(report[0]), 'UTF-8'),
                            "filename": invoice_obj.state == 'posted' and (
                                    (invoice_obj.name or 'INV').replace('/', '_') + '.pdf') or 'INV.pdf',
                            "mimeType": "application/pdf"}]})

            try:
                response = requests.post('%s/document_submissions' % end_point,
                                         headers=headers,
                                         json=data,
                                         timeout=TIMEOUT)
            except requests.exceptions.Timeout:
                obj.write({'state': 'error'})
                log = _(
                    '<b>An Exception has arised.</b><br/>A timeout occured while trying to reach the Invoice Submission Api.')
                obj.message_post(body=log)
                continue
            except requests.exceptions.HTTPError:
                obj.write({'state': 'error'})
                log = _(
                    '<b>An Exception has arised.</b><br/>HTTP error occurred while trying to reach the Invoice Submission Api.')
                obj.message_post(body=log)
                continue
            except Exception as e:
                obj.write({'state': 'error'})
                log = _(
                    '<b>An Exception has arised.</b><br/>The Invoice Submission Api is not reachable, please try again later.<br/>'
                    'Exception handler details: %s') % (
                          repr(e))
                obj.message_post(body=log)
                continue

            json_data = json.loads(response.text)

            if response.status_code != 200:
                obj.write({'state': 'error'})
                http_code = response.status_code
                response_desc = json_data
                if http_code == 401:
                    http_codename = 'Unauthorized'
                    response_desc = 'No Content'
                elif http_code == 403:
                    http_codename = 'Forbidden'
                elif http_code == 422:
                    http_codename = 'Unprocessable Entity'
                else:
                    http_codename = 'Undefined Error Occured'
                log = _("<b>Document Submission API Responded as</b><br/>{} {}<br/>{}".format(http_code, http_codename,
                                                                                              response_desc))
                obj.message_post(body=log)
            elif response.status_code == 200:
                obj.write({'state': 'sent',
                           'guid': json_data['guid']})

    def action_send(self):
        if self.filtered(lambda q: q.state != 'pending'):
            raise ValidationError(_("Please select only 'Pending' queue entries to perform this action."))
        self._send()

    def _confirm(self):
        for obj in self:
            access_point = self.env['peppol.access.point.sg'].search(
                [('company_id', '=', obj.invoice_id.company_id.id)])
            if not access_point:
                obj.write({'state': 'error'})
                log = _("Access Point configuration is not defined for the Company %s") % obj.invoice_id.company_id.name
                obj.message_post(body=log)
                continue
            end_point = access_point.endpoint
            api_key = access_point.authorization_key

            headers = {
                "Accept": "application/json",
                "Authorization": "Bearer {}".format(api_key),
                "Content-Type": "application/json"
            }

            try:
                response = requests.get('%s/document_submissions/%s/evidence' % (end_point, obj.guid),
                                        headers=headers,
                                        timeout=TIMEOUT)
            except requests.exceptions.Timeout:
                obj.write({'state': 'error'})
                log = _(
                    '<b>An Exception has arised.</b><br/>A timeout occured while trying to reach the Invoice Submission Evidence Api.')
                obj.message_post(body=log)
                continue
            except requests.exceptions.HTTPError:
                obj.write({'state': 'error'})
                log = _(
                    '<b>An Exception has arised.</b><br/>HTTP error occurred while trying to reach the Invoice Submission Evidence Api.')
                obj.message_post(body=log)
                continue
            except Exception as e:
                obj.write({'state': 'error'})
                log = _(
                    '<b>An Exception has arised.</b><br/>The Invoice Submission Evidence Api is not reachable, please try again later.<br/>'
                    'Exception handler details: %s') % (
                          repr(e))
                obj.message_post(body=log)
                continue

            json_data = json.loads(response.text)

            if response.status_code != 200:
                obj.write({'state': 'error'})
                http_code = response.status_code
                response_desc = json_data
                if http_code == 401:
                    http_codename = 'Unauthorized'
                    response_desc = 'No Content'
                elif http_code == 403:
                    http_codename = 'Forbidden'
                elif http_code == 404:
                    http_codename = 'Not Found'
                else:
                    http_codename = 'Undefined Error Occured'
                log = _("<b>Invoice Submission Evidence Response</b><br/><b>{} {}</b><br/>{}".format(http_code,
                                                                                                     http_codename,
                                                                                                     response_desc))
                obj.message_post(body=log)

            elif response.status_code == 200 and "evidence" in json_data:
                attachment_ids = []
                for document_dic in json_data.get('documents', []):
                    if document_dic.get('document'):
                        attachment_ids.append(self.env['ir.attachment'].create({
                            'type': 'url',
                            'name': document_dic.get('expires_at') and 'Document_Expires_at_' + document_dic.get(
                                'expires_at') or 'Document',
                            'url': document_dic['document'],
                            'mimetype': document_dic.get('mime_type'),
                        }).id)

                obj.write({'state': 'done',
                           'show_invoice_submission_evidence': True,
                           'invoice_submission_evidence_action_ids': json_data.get('evidence') and [
                               (0, 0, json_data['evidence'])] or False,
                           'evidence_sender_identifier': json_data.get('sender'),
                           'evidence_receiver_identifier': json_data.get('receiver'),
                           'evidence_network': json_data.get('network'),
                           'evidence_document_ids': attachment_ids and [(6, 0, attachment_ids)] or False})

    def action_confirm(self):
        if self.filtered(lambda q: q.state != 'sent' or q.event != 'succeeded'):
            raise ValidationError(_("Please select only 'Sent' queue entries for evidence submission results."))

        self._confirm()

    def action_retry(self):
        if self.filtered(lambda q: q.state not in ('error', 'cancelled')):
            raise ValidationError(_("Please select only 'Error' or 'Cancelled' queue entries to perform this action."))
        sent = self.filtered(lambda q: q.sent)
        sent.write({'state': 'sent'})

        not_sent = self - sent
        not_sent.write({'state': 'pending'})

    def action_cancel(self):
        if self.filtered(lambda q: q.state not in ('pending', 'error')):
            raise ValidationError(_("Please select only 'Pending' or 'Error' queue entries to perform this action."))
        self.write({'state': 'cancelled'})
