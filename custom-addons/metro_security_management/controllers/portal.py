import binascii
from odoo import http,fields, http, _,SUPERUSER_ID
from odoo.addons.portal.controllers.portal import CustomerPortal,pager
from odoo.exceptions import AccessError, MissingError
from collections import OrderedDict
from odoo.http import request
from odoo.addons.portal.controllers.mail import _message_post_helper
from datetime import datetime
import logging
import base64
_logger = logging.getLogger(__name__)


class PortalVisitor(CustomerPortal):

    def _prepare_home_portal_values(self,counters):
        rtn = super(PortalVisitor,self)._prepare_home_portal_values(counters)
        rtn['visitor_counts'] = request.env['pre.approved.visitor'].search_count([])
        return rtn

    @http.route(["/new/visitor"], type="http", auth="public", website=True, csrf=True)
    def RegisterVisitorProfile(self,model=None, res_id=None, access_token=None, **kw):
        if request.httprequest.method == 'POST':
            # Handle the form submission
            try:
                location_id = int(kw.get('location_id', 0))
                ic_number_value = kw.get('ic_number', '').strip()  # Retrieve entered IC number as text
                name = kw.get('name', '').strip()  # Retrieve entered name
                phone = kw.get('phone', '').strip()  # Retrieve entered phone number
                email = kw.get('email', '').strip()  # Retrieve entered email
                check_in_raw = kw.get('check_in')
                check_in = datetime.strptime(check_in_raw, '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d %H:%M:%S')

                check_in_type = kw.get('check_in_type', 'walk_in')
                # company_id = int(kw.get('visitor_company_id', 0)) if kw.get('visitor_company_id') else False
                visit_type_id = int(kw.get('visit_type_id', 0)) if kw.get('visit_type_id') else False
                visit_category_id = int(kw.get('visit_category_id', 0)) if kw.get('visit_category_id') else False
                pass_number = kw.get('pass_number', '')
                unit_id = int(kw.get('unit_location_id', 0)) if kw.get('unit_location_id') else False
                vehicle_number = kw.get('vehicle_number') if check_in_type == 'vehicle' else ''

                if not location_id or not ic_number_value:
                    return request.redirect("/new/visitor")

                # Check if an IC number record already exists
                company_id = request.env['block.location'].sudo().browse(unit_id).company_id.id if unit_id else request.env.company.id
                ic_number_record = request.env['ic.number'].sudo().search([
                        ('ic_number', '=', ic_number_value),
                        ('company_id', '=', company_id)  # Use the same company_id used in visitor creation
                    ], limit=1)

                if ic_number_record:
                    ic_number_record.write({
                        'name': name,
                        'phone': phone,
                        'email': email,
                    })
                else:
                    # If the record doesn't exist, create a new one
                    ic_number_record = request.env['ic.number'].sudo().create({
                        'ic_number': ic_number_value,
                        'name': name,
                        'phone': phone,
                        'email': email,
                        'company_id': company_id
                    })


                # Create the visitor record
                visitor = request.env['pre.approved.visitor'].sudo().create({
                'location_id': location_id,
                'unit_location_id': unit_id,
                'company_id': request.env['block.location'].sudo().browse(unit_id).company_id.id if unit_id else request.env.company.id,
                'ic_number_id': ic_number_record.id,
                'check_in': check_in,
                'check_in_type': check_in_type,
                'visit_type_id': visit_type_id,
                'visit_category_id': visit_category_id,
                'pass_number': pass_number,
                'vehicle_number': vehicle_number
            })
                

                return request.render("metro_security_management.visitor_success_page", {
                'model': model,
                'res_id': res_id,
                'access_token': access_token,
            })

            except Exception as e:
                _logger.error(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>Error in visitor registration: {e}")
                return request.redirect('/new/visitor')

        # For GET request: Retrieve defaults using access_token
        location_id = None
        unit_location_id = None
        if access_token:
            # Fetch the block location using the access token
            block_location = request.env['block.location'].sudo().search([('access_token', '=', access_token)], limit=1)
            if block_location:
                location_id = block_location.security_location_id.id
                unit_location_id = block_location.id

        # Render the form
        locations = request.env['security.location'].sudo().search([])
        visit_types = request.env['visitor.type'].sudo().search([])
        visit_categories = request.env['visitor.category'].sudo().search([])
        units = request.env['block.location'].sudo().search([])

        return request.render("metro_security_management.new_visitor_form_view_portal", {
            'locations': locations,
            'visit_types': visit_types,
            'visit_categories': visit_categories,
            'units': units,
            'default_location_id': location_id,
            'default_unit_location_id': unit_location_id,
            'page_name': 'register_visitor'
        })
    