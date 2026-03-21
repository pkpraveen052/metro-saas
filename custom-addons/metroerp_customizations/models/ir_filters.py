from odoo import models, fields, api
from odoo.http import request


class IrFilters(models.Model):
    _inherit = 'ir.filters'

    # user_ids = fields.Many2many(comodel_name='res.users', string='Allowed Users')

    company_id = fields.Many2one(comodel_name='res.company', string='Company')

    @api.model
    @api.returns('self', lambda value: value.id)
    def create_or_replace(self, vals):
        action_id = vals.get('action_id')
        current_filters = self.get_filters(vals['model_id'], action_id)
        matching_filters = [f for f in current_filters
                            if f['name'].lower() == vals['name'].lower()
                            # next line looks for matching user_ids (specific or global), i.e.
                            # f.user_id is False and vals.user_id is False or missing,
                            # or f.user_id.id == vals.user_id
                            if (f['user_id'] and f['user_id'][0]) == vals.get('user_id')]

        if vals.get('is_default'):
            if vals.get('user_id'):
                # Setting new default: any other default that belongs to the user
                # should be turned off
                domain = self._get_action_domain(action_id)
                defaults = self.search(domain + [
                    ('model_id', '=', vals['model_id']),
                    ('user_id', '=', vals['user_id']),
                    ('is_default', '=', True),
                ])
                if defaults:
                    defaults.write({'is_default': False})
            else:
                self._check_global_default(vals, matching_filters)

        # When a filter exists for the same (name, model, user) triple, we simply
        # replace its definition (considering action_id irrelevant here)
        if matching_filters:
            matching_filter = self.browse(matching_filters[0]['id'])
            matching_filter.write(vals)
            return matching_filter

        current_company = self.get_current_company()
        vals['company_id'] = current_company[0]
        return self.create(vals)

    # @api.model
    # def create(self, vals_list):
    #     # Did the changes to make filters company wise
    #     res = super(IrFilters, self).create(vals_list)
    #     current_company = self.env.company.id
    #     if current_company:
    #         res.company_id = current_company
    #     return res

    @api.model
    def get_filters(self, model, action_id=None):
        """Obtain the list of filters available for the user on the given model.

        :param action_id: optional ID of action to restrict filters to this action
            plus global filters. If missing only global filters are returned.
            The action does not have to correspond to the model, it may only be
            a contextual action.
        :return: list of :meth:`~osv.read`-like dicts containing the
            ``name``, ``is_default``, ``domain``, ``user_id`` (m2o tuple),
            ``action_id`` (m2o tuple) and ``context`` of the matching ``ir.filters``.
        """
        # available filters: private filters (user_id=uid) and public filters (uid=NULL),
        # and filters for the action (action_id=action_id) or global (action_id=NULL)
        action_domain = self._get_action_domain(action_id)
        # Start Custom changes to make filters company wise
        current_company = self.get_current_company()
        user_domain = [('model_id', '=', model), ('company_id', 'in', current_company),
                       ('user_id', 'in', [self._uid, False])]
        # End Custom changes to make filters company wise
        filters = self.search(action_domain + user_domain)
        user_context = self.env['res.users'].context_get()
        return filters.with_context(user_context).read(['name', 'is_default', 'domain', 'context', 'user_id', 'sort'])

    def get_current_company(self):
        cookies_cids = [int(r) for r in request.httprequest.cookies.get('cids').split(",")] \
            if request.httprequest.cookies.get('cids') \
            else [request.env.user.company_id.id]
        return cookies_cids
