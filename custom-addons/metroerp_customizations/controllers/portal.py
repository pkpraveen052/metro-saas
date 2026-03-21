import binascii
from odoo import http,fields, http, _,SUPERUSER_ID
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from collections import OrderedDict
from odoo.http import request
from urllib.parse import urlparse
from werkzeug.utils import redirect as werkzeug_redirect
from odoo.addons.portal.controllers.mail import _message_post_helper


class SecurePortal(http.Controller):

    @http.route('/web/session/logout', type='http', auth='none', csrf=False)
    def secure_logout(self, redirect_url=None, **kw):
        request.session.logout(keep_db=True)

        safe_redirect = '/web/login'

        if redirect_url:
            parsed = urlparse(redirect_url)

            # Allow only internal relative paths
            if not parsed.netloc and redirect_url.startswith('/'):
                safe_redirect = redirect_url
            else:
                request.env['ir.logging'].sudo().create({
                    'name': 'Security',
                    'type': 'server',
                    'level': 'WARNING',
                    'message': f'Blocked open redirect attempt: {redirect_url}',
                    'path': 'portal.py',
                    'func': 'secure_logout',
                    'line': 'secure_logout',
                })

        return werkzeug_redirect(safe_redirect)



class PortalDelivery(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'delivery_count' in counters:
            delivery_count = request.env['stock.picking'].search_count(self._get_delivery_domain()) \
                if request.env['stock.picking'].check_access_rights('read', raise_exception=False) else 0
            values['delivery_count'] = delivery_count
        return values

    # ------------------------------------------------------------
    # My Delivery
    # ------------------------------------------------------------

    def _delivery_get_page_view_values(self, delivery, access_token, **kwargs):
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>method call")
        values = {
            'page_name': 'delivery',
            'delivery_order': delivery,
            'token': access_token,
            'report_type': 'html',
            'action': delivery._get_portal_return_action(),
        }
        if delivery.company_id:
            values['res_company'] = delivery.company_id
        return self._get_page_view_values(delivery, access_token, values, 'my_delivery_history', False, **kwargs)
    


    def _get_delivery_domain(self):
        return [('state', 'not in', ('cancel', 'draft'))]

    @http.route(['/my/deliveries', '/my/deliveries/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_deliveries(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        DeliveryOrder = request.env['stock.picking'].search([('picking_type_code', '=', 'outgoing')])

        domain = self._get_delivery_domain()

        searchbar_sortings = {
            'date': {'label': _('Shipping Date'), 'order': 'scheduled_date desc'},
            'duedate': {'label': _('Deadline Date'), 'order': 'date_deadline desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        # default sort by order
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        searchbar_filters = {
                'all': {'label': _('All'), 'domain': [('picking_type_code', '=', 'outgoing')]},
                # 'outgoing': {'label': _('Delivery'), 'domain': [('picking_type_code', '=', 'outgoing')]},
                # 'incoming': {'label': _('Receipts'), 'domain': [('picking_type_code', '=', 'incoming')]},
                # 'internal': {'label': _('Internal'), 'domain': [('picking_type_code', '=', 'internal')]},
            }
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        delivery_count = DeliveryOrder.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/deliveries",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=delivery_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        deliveries = DeliveryOrder.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_delivery_history'] = deliveries.ids[:100]

        values.update({
            'date': date_begin,
            'deliveries': deliveries,
            'page_name': 'delivery',
            'pager': pager,
            'default_url': '/my/deliveries',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby':filterby,
        })
        return request.render("metroerp_customizations.portal_my_delivery", values)
    

    @http.route(['/my/deliveries/<int:delivery_id>'], type='http', auth="public", website=True)
    def portal_my_delivery_detail(self, delivery_id, access_token=None, report_type=None, download=False, **kw):
        values = {"delivery_order": delivery_id}
        try:
            delivery_sudo = self._document_check_access('stock.picking', delivery_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=delivery_sudo, report_type=report_type, report_ref='stock.action_report_delivery', download=download)

        values = self._delivery_get_page_view_values(delivery_sudo, access_token, **kw)

        return request.render("metroerp_customizations.portal_delivery_page", values)
    


    @http.route(['/my/deliveries/<int:delivery_id>/accept'], type='json', auth="public", website=True)
    def portal_delivery_sign(self, delivery_id, access_token=None, name=None, signature=None):
        # get from query string if not on json param
        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            order_sudo = self._document_check_access('stock.picking', delivery_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'error': _('Invalid order.')}

        if not order_sudo.has_to_be_signed():
            return {'error': _('The order is not in a state requiring customer signature.')}
        if not signature:
            return {'error': _('Signature is missing.')}

        try:
            order_sudo.write({
                'signed_by': name,
                'signed_on': fields.Datetime.now(),
                'signature': signature,
            })
            request.env.cr.commit()
        except (TypeError, binascii.Error) as e:
            return {'error': _('Invalid signature data.')}

        pdf = request.env.ref('stock.action_report_delivery').with_user(SUPERUSER_ID)._render_qweb_pdf([order_sudo.id])[0]

        _message_post_helper(
            'stock.picking', order_sudo.id, _('Order signed by %s') % (name,),
            attachments=[('%s.pdf' % order_sudo.name, pdf)],
            **({'token': access_token} if access_token else {}))

        query_string = '&message=sign_ok'

        return {
            'force_refresh': True,
            'redirect_url': order_sudo.get_portal_url(query_string=query_string),
        }

#Inherited Invoice Portal To Pass Company ID.    

class InvoicePortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        AccountMove = request.env['account.move']
        
        if 'invoice_count' in counters:
            domain = self._get_invoices_domain() + [('is_progressive_invoice', '=', False)]
            invoice_count = AccountMove.search_count(domain) if AccountMove.check_access_rights('read', raise_exception=False) else 0
            values['invoice_count'] = invoice_count

        if 'progressive_invoice_count' in counters:
            domain = self._get_invoices_domain() + [('is_progressive_invoice', '=', True)]
            prog_invoice_count = AccountMove.search_count(domain) if AccountMove.check_access_rights('read', raise_exception=False) else 0
            values['progressive_invoice_count'] = prog_invoice_count

        return values
    
    @http.route(['/my/invoices', '/my/invoices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_invoices(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        AccountInvoice = request.env['account.move']

        domain = self._get_invoices_domain()

        # 🔸 Add filter for only normal invoices (not progressive)
        domain += [('is_progressive_invoice', '=', False)]

        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'invoice_date desc'},
            'duedate': {'label': _('Due Date'), 'order': 'invoice_date_due desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'invoices': {'label': _('Invoices'), 'domain': [('move_type', 'in', ('out_invoice', 'out_refund'))]},
            'bills': {'label': _('Bills'), 'domain': [('move_type', 'in', ('in_invoice', 'in_refund'))]},
        }
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        invoice_count = AccountInvoice.search_count(domain)
        pager = portal_pager(
            url="/my/invoices",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=invoice_count,
            page=page,
            step=self._items_per_page
        )
        invoices = AccountInvoice.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_invoices_history'] = invoices.ids[:100]

        values.update({
            'date': date_begin,
            'invoices': invoices,
            'page_name': 'invoice',
            'pager': pager,
            'default_url': '/my/invoices',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        return request.render("account.portal_my_invoices", values)

    # ------------------------------------------------------------
    # My Invoices
    # ------------------------------------------------------------
    @http.route(['/my/progressive/invoices', '/my/progressive/invoices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_progressive_invoices(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        AccountInvoice = request.env['account.move']

        domain = self._get_invoices_domain() + [('is_progressive_invoice', '=', True)]

        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'invoice_date desc'},
            'duedate': {'label': _('Due Date'), 'order': 'invoice_date_due desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'invoices': {'label': _('Invoices'), 'domain': [('move_type', 'in', ('out_invoice', 'out_refund'))]},
            'bills': {'label': _('Bills'), 'domain': [('move_type', 'in', ('in_invoice', 'in_refund'))]},
        }
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        invoice_count = AccountInvoice.search_count(domain)
        pager = portal_pager(
            url="/my/progressive/invoices",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=invoice_count,
            page=page,
            step=self._items_per_page
        )
        invoices = AccountInvoice.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_invoices_history'] = invoices.ids[:100]

        values.update({
            'date': date_begin,
            'invoices': invoices,
            'page_name': 'progressive_invoice',
            'pager': pager,
            'default_url': '/my/progressive/invoices',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        return request.render("metroerp_customizations.portal_my_progressive_invoices", values)


    
    def _invoice_get_page_view_values(self, invoice, access_token, **kwargs):
        values = super(InvoicePortal, self)._invoice_get_page_view_values(invoice, access_token, **kwargs)
        # Added the company_id to the values
        if invoice.company_id:
            values['res_company'] = invoice.company_id
        
        return values


    @http.route(['/my/invoices/<int:invoice_id>'], type='http', auth="public", website=True)
    def portal_my_invoice_detail(
        self, invoice_id, access_token=None, report_type=None,
        download=False, **kw
    ):
        try:
            invoice_sudo = self._document_check_access(
                'account.move', invoice_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):

            # 🔥 KEY FIX HERE
            report_ref = 'account.account_invoices'
            if invoice_sudo.is_progressive_invoice:
                report_ref = 'ks_custom_report_layouts.action_progressive_invoice_report'

            return self._show_report(
                model=invoice_sudo,
                report_type=report_type,
                report_ref=report_ref,
                download=download
            )

        values = self._invoice_get_page_view_values(
            invoice_sudo, access_token, **kw
        )

        acquirers = values.get('acquirers')
        if acquirers:
            country_id = (
                values.get('partner_id')
                and values.get('partner_id')[0].country_id.id
            )
            values['acq_extra_fees'] = acquirers.get_acquirer_extra_fees(
                invoice_sudo.amount_residual,
                invoice_sudo.currency_id,
                country_id
            )

        return request.render("account.portal_invoice_page", values)



        
