# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import AccessError


class ResUsersInherited(models.Model):
    _inherit = "res.users"

    @api.model
    def _default_chatter_position(self):
        return 'normal'

    def default_enable_pos(self):
        if self.env.user.has_group('base.group_system') or (self.env.user.has_group('metroerp_customizations.sub_admin_group') and self.env.user.has_group('point_of_sale.group_pos_manager')):
            return True
        else:
            return False

    is_admin_flag = fields.Boolean('Is Admin', compute="_compute_is_admin",store=True)
    notification_type = fields.Selection([
        ('email', 'Handle by Emails'),
        ('inbox', 'Handle in ERP')],
        'Notification', required=True, default='inbox',
        help="Policy on how to handle Chatter notifications:\n"
             "- Handle by Emails: notifications are sent to your email address\n"
             "- Handle in Odoo: notifications appear in your Odoo Inbox")
    odoobot_state = fields.Selection(
        [
            ('not_initialized', 'Not initialized'),
            ('onboarding_emoji', 'Onboarding emoji'),
            ('onboarding_attachement', 'Onboarding attachement'),
            ('onboarding_command', 'Onboarding command'),
            ('onboarding_ping', 'Onboarding ping'),
            ('idle', 'Idle'),
            ('disabled', 'Disabled'),
        ], string="ERP Bot Status", readonly=True, required=False)
    odoobot_failed = fields.Boolean(readonly=True, string="ERP Bot Failed")

    enable_pos = fields.Boolean(compute='_compute_enable_pos', string='Enable POS' ,default=default_enable_pos)

    def _compute_enable_pos(self):
        for obj in self:
            if self.env.user.has_group('base.group_system') or (self.env.user.has_group('metroerp_customizations.sub_admin_group') and self.env.user.has_group('point_of_sale.group_pos_manager')):
                obj.enable_pos = True
            else:
                obj.enable_pos = False
 
    @api.depends('groups_id')
    def _compute_is_admin(self):
        for rec in self:
            if rec.has_group('base.group_system') or rec.has_group('base.group_erp_manager'):
                rec.is_admin_flag = True
            else:
                rec.is_admin_flag = False

    def _is_admin(self):
        """ ERP Admin get General Settings With out (Only administrators can change the settings). """
        self.ensure_one()
        return self._is_superuser() or self.has_group('base.group_erp_manager') or self.has_group('metroerp_customizations.sub_admin_group')
    
    def get_powerby_title(self):
        """ Method utilized from Mail Templates. """
        odoo_text_replacement = self.env['ir.default'].sudo().get('res.config.settings', "odoo_text_replacement")
        if odoo_text_replacement:
            return odoo_text_replacement
        else:
            return "Odoo"

    # def write(self, vals):
    #     """ Set the Accounting Full Group as False when Billing User is set. """
    #     # print("\n USERS Write() >>>>>>")
    #     # print("vals ===",vals)
    #     for user_field in list(vals):
    #         if 'sel_groups' in user_field and self.env['ir.model.data'].xmlid_to_res_id('account.group_account_invoice') and vals[user_field] == self.env.ref('account.group_account_invoice').id:
    #             userfield = 'in_group_' + str(self.env.ref('account.group_account_user').id)
    #             vals.update({userfield: False})
    #     res = super(ResUsersInherited, self).write(vals)
    #     if 'company_id' in vals:
    #         self.partner_id.write({'company_id': vals['company_id']})
    #     return res


    def write(self, vals):
        """ 
        - Keep existing Accounting group logic
        - HARD BLOCK unauthorized admin (base.group_system) assignment
        - SaaS & multi-company safe
        """

        # HARD SECURITY BLOCK (MOST IMPORTANT)
        if 'groups_id' in vals:
            system_group = self.env.ref('base.group_system', raise_if_not_found=False)

            if system_group:
                for cmd in vals.get('groups_id', []):
                    if (
                        isinstance(cmd, (list, tuple)) and
                        system_group.id in cmd
                    ):
                        # Allow Odoo internal operations (Settings, install, upgrade)
                        if self.env.is_superuser():
                            continue

                        user = self.env.user

                        # Allow System Administrator
                        if user.has_group('base.group_system'):
                            continue

                        # Allow ERP Admin (as per your senior's logic)
                        if (
                            user.has_group('base.group_erp_manager') or
                            user.has_group('metroerp_customizations.sub_admin_group')
                        ):
                            continue

                        # Block everyone else
                        raise AccessError(
                            "Security restriction: You are not allowed to assign "
                            "System Administrator rights."
                        )

        # 2️⃣ YOUR EXISTING ACCOUNTING LOGIC (UNCHANGED)
        for user_field in list(vals):
            if (
                'sel_groups' in user_field and
                self.env['ir.model.data'].xmlid_to_res_id('account.group_account_invoice') and
                vals[user_field] == self.env.ref('account.group_account_invoice').id
            ):
                userfield = 'in_group_' + str(self.env.ref('account.group_account_user').id)
                vals.update({userfield: False})

        # 3️⃣ CALL SUPER
        res = super(ResUsersInherited, self).write(vals)

        # 4️⃣ COMPANY SYNC (MULTI-COMPANY SAFE)
        if 'company_id' in vals:
            for user in self:
                if user.partner_id:
                    user.partner_id.write({'company_id': vals['company_id']})

        return res


    @api.model
    def create(self, vals):
        ctx = self._context
        obj = super(ResUsersInherited, self).create(vals)
        # Assign the group_view_cost_price group to the new user
        # new create user to remove default location group
        company_location_group = self.env.company.group_stock_multi_locations
        if not company_location_group:
        #     group_stock_multi_warehouses = self.env.ref('stock.group_stock_multi_warehouses')
            group_stock_multi_locations = self.env.ref('stock.group_stock_multi_locations')
        #     group_stock_multi_warehouses.write({'users': [(3, obj.id)]})
            group_stock_multi_locations.write({'users': [(3, obj.id)]})
        obj.partner_id.write({'company_id': obj.company_id.id})
        return obj

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        ctx = self._context
        # print("\nUSERS Search()   ctx ====",ctx)
        # print("     args =",args, "offset =",offset, "limit =",limit, "order =",order, "count =",count)  

        # Return super() while the User is Settings/Accessrights group.
        if self.user_has_groups('base.group_system,base.group_erp_manager'): # and 'allowed_company_ids' not in ctx
            return super(ResUsersInherited, self).search(args, offset=offset, limit=limit, order=order, count=count)        

        if ctx.get('allowed_company_ids') and limit and limit > 1:
            if not args:
                args = [('company_id','in',ctx['allowed_company_ids'])]
            else:
                args.append(('company_id','in',ctx['allowed_company_ids']))
        res = super(ResUsersInherited, self).search(args, offset=offset, limit=limit, order=order, count=count)
        # print("     ",res)
        return res

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        ctx = self._context
        # print("\nUSERS read_group()   ctx ====",ctx)
        # print("     domain =",domain, "fields =",fields, "groupby =",groupby, "offset =",offset, "limit =",limit, "orderby =",orderby, "lazy =",lazy)  
        # Return super() while the User is Settings/Accessrights group.      
        if self.user_has_groups('base.group_system,base.group_erp_manager'): # and 'allowed_company_ids' not in ctx
            return super(ResUsersInherited, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        if ctx.get('allowed_company_ids') and limit and limit > 1:
            if not domain:
                domain = [('company_id','in',ctx['allowed_company_ids'])]
            else:
                domain.append(('company_id','in',ctx['allowed_company_ids']))
        return super(ResUsersInherited, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)


    def old_user_group_remove(self):
        users = self.env['res.users'].search([])
        for user in users:
            if user.has_group('stock.group_stock_multi_warehouses'):
                self.env.ref('stock.group_stock_multi_warehouses').write({'users': [(3, user.id)]})


    
   
