# -*- coding: utf-8 -*-
from odoo import models, fields, api
import re
from odoo.exceptions import ValidationError


class ResPartnerInherited(models.Model):
    _inherit = "res.partner"

    signup_token = fields.Char(copy=False, groups="base.group_erp_manager,metroerp_customizations.sub_admin_group")
    signup_type = fields.Char(string='Signup Token Type', copy=False,
                              groups="base.group_erp_manager,metroerp_customizations.sub_admin_group")
    signup_expiration = fields.Datetime(copy=False,
                                        groups="base.group_erp_manager,metroerp_customizations.sub_admin_group")
    company_id = fields.Many2one('res.company', 'Company', index=True, track_visibility=True) #default=lambda self: self.env.company.id
    property_product_pricelist = fields.Many2one(
        'product.pricelist', 'Pricelist',
        help="This pricelist will be used, instead of the default one, for sales to the current partner", track_visibility=True, store=True) # Overidden this field from base.
    latest_followup_level_id = fields.Many2one('followup.line', compute='_get_latest',
                                               string="Latest Follow-up Level", help="The maximum follow-up level",
                                               store=True)
    fax = fields.Char(string='Fax', size=64, tracking=True)

    @api.model
    def create(self, vals):
        """ To set the partner with the logged in User's Company while creating a User. """
        # print("\n Partner Create() >>>>>>")
        # print("vals ===",vals)
        ctx = self._context
        print("\nCUSTOM PARTNER create() >>>> ",vals)
        print("ctx ====",ctx)
        # print("ctxxxxxx ====",ctx)
        # if 'params' in ctx and ctx['params'].get('model') == 'res.company':
        #     return super(ResPartnerInherited, self).create(vals)
        if 'new_company' in ctx:
            vals.update({'company_id': False})
        else:
            if not vals.get('company_id', False):
                if ctx.get('allowed_company_ids'):
                    vals.update({'company_id': ctx.get('allowed_company_ids')[0]})
                elif not vals.get('is_company', False):
                    vals.update({'company_id': self.env.user.company_id.id})

        if vals.get('company_id', False):
            public_pricelist = self.env['product.pricelist'].sudo().search([('company_id', '=', vals.get('company_id'))], limit=1)
            vals.update({'property_product_pricelist': public_pricelist and public_pricelist.id or False})

        obj = super(ResPartnerInherited, self).create(vals)
        if obj.message_partner_ids:
            obj.message_unsubscribe(obj.message_partner_ids.ids)    
        return obj

    def write(self, vals):
        """ Set the Accounting Full Group as False when Billing User is set. """
        print("\n CUSTOM Partner Write() >>>>>>",vals)
        # print("vals ===",vals)
        # self.ensure_one()
        # print(self.message_partner_ids)
        if vals.get('company_id', False):
            public_pricelist = self.env['product.pricelist'].sudo().search([('company_id', '=', vals.get('company_id'))], limit=1)
            vals.update({'property_product_pricelist': public_pricelist and public_pricelist.id or False})

        res = super(ResPartnerInherited, self).write(vals)

        if 'user_id' in vals and self.message_partner_ids:
            self.message_unsubscribe([self.user_id.partner_id.id])

        return res

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        ctx = self._context

        # 🔹 Extra check: if POS user or POS manager → always restrict
        if self.user_has_groups('point_of_sale.group_pos_user') or self.user_has_groups('point_of_sale.group_pos_manager'):
            if ctx.get('allowed_company_ids'):
                args = args or []
                args.append(('company_id', 'in', ctx['allowed_company_ids']))
            return super(ResPartnerInherited, self).search(args, offset=offset, limit=limit, order=order, count=count)

        # ================= Existing logic (unchanged) =================
        if self.user_has_groups('base.group_system,base.group_erp_manager'):
            return super(ResPartnerInherited, self).search(args, offset=offset, limit=limit, order=order, count=count)

        if ctx.get('create_user'): 
            return super(ResPartnerInherited, self).search(args, offset=offset, limit=limit, order=order, count=count)

        if ctx.get('allowed_company_ids') and (limit and limit > 1):
            if not args:
                args = [('company_id','in',ctx['allowed_company_ids'])]
            else:
                args.append(('company_id','in',ctx['allowed_company_ids']))

        res = super(ResPartnerInherited, self).search(args, offset=offset, limit=limit, order=order, count=count)        
        return res

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        ctx = self._context

        # 🔹 Extra check: if POS user or POS manager → always restrict
        if self.user_has_groups('point_of_sale.group_pos_user') or self.user_has_groups('point_of_sale.group_pos_manager'):
            if ctx.get('allowed_company_ids'):
                domain = domain or []
                domain.append(('company_id', 'in', ctx['allowed_company_ids']))
            return super(ResPartnerInherited, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        # ================= Existing logic (unchanged) =================
        if self.user_has_groups('base.group_system,base.group_erp_manager'):
            return super(ResPartnerInherited, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        
        if ctx.get('allowed_company_ids') and (limit and limit > 1):
            if not domain:
                domain = [('company_id','in',ctx['allowed_company_ids'])]
            else:
                domain.append(('company_id','in',ctx['allowed_company_ids']))

        return super(ResPartnerInherited, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.model
    def search_count(self, args):
        ctx = self._context

        # 🔹 Extra check: if POS user or POS manager → always restrict
        if self.user_has_groups('point_of_sale.group_pos_user') or self.user_has_groups('point_of_sale.group_pos_manager'):
            if ctx.get('allowed_company_ids'):
                args = args or []
                args.append(('company_id', 'in', ctx['allowed_company_ids']))
            return super(ResPartnerInherited, self).search_count(args)

        # ================= Existing logic (unchanged) =================
        if self.user_has_groups('base.group_system,base.group_erp_manager'):
            return super(ResPartnerInherited, self).search_count(args)

        if ctx.get('allowed_company_ids'):
            if not args:
                args = [('company_id','in',ctx['allowed_company_ids'])]
            else:
                args.append(('company_id','in',ctx['allowed_company_ids']))

        return super(ResPartnerInherited, self).search_count(args)

    @api.onchange('company_id')
    def onchange_company_id(self):
        if self.company_id:
            public_pricelist = self.env['product.pricelist'].sudo().search([('company_id', '=', self.company_id.id)], limit=1)
            self.property_product_pricelist = public_pricelist and public_pricelist.id or False
        else:
            self.property_product_pricelist = False

    # @api.model
    # def default_get(self, fields):
    #     ctx = self._context
    #     print("\ndefault_get() >>>> ctx", ctx)
    #     rec = super(ResPartnerInherited, self).default_get(fields)
    #     if ctx.get('allowed_company_ids'):
    #         public_pricelist = self.env['product.pricelist'].sudo().search([('company_id', '=', ctx.get('allowed_company_ids')[0])], limit=1)
    #     rec['property_product_pricelist'] = public_pricelist.id or False
    #     print("rec ===",rec)
    #     return rec

class PartnerCategory(models.Model):
    _inherit = "res.partner.category"

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.constrains('name', 'company_id')
    def _check_unique_name_within_company(self):
        for record in self:
            if self.search_count([('name', '=', record.name), ('company_id', '=', record.company_id.id)]) > 1:
                raise ValidationError('Tag name already exists !')
