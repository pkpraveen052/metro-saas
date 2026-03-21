# -*- coding: utf-8 -*-
import json
from odoo import api, models, http
from odoo.http import request


class VendorListSync(http.Controller):

    @http.route('/unlink/vendor/list', auth="none", methods=['DELETE'], csrf=False)
    def unlink_vendor_list(self, **kw):
        delete_data = json.loads(request.httprequest.data)
        uen_no = delete_data.get('uen_no')
        if uen_no:
            company = request.env['res.company'].sudo().search([('l10n_sg_unique_entity_number', '=', uen_no)], limit=1)
            if company:
                vendor_list_records = request.env['vendor.list.peppol'].sudo().search([('company_id', '=', company.id)])
                vendor_list_records.sudo().unlink()

        return http.Response(
            status=200,
            content_type="application/json",
            response=json.dumps({}),
        )

    @http.route('/create/vendors/list', auth="none", methods=['POST'], csrf=False)
    def create_vendors_list(self, **kw):
        datas = json.loads(request.httprequest.data)
        if datas:
            for data in datas:
                uen_no = data.get('marketplace_uenNo')
                company = request.env['res.company'].sudo().search([('l10n_sg_unique_entity_number', '=', uen_no)], limit=1)
                if company:
                    data['company_id'] = company.id
                    data.pop('marketplace_uenNo')
                    request.env['vendor.list.peppol'].sudo().create(data)

        return http.Response(
            status=200,
            content_type="application/json",
            response=json.dumps({}),
        )
