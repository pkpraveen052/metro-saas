# -*- coding: utf-8 -*-

from odoo import api, fields, models


class UserGuide(models.Model):
    _name = "user.guide"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'User Guide'


    name = fields.Char(string='Question')
    tags_ids = fields.Many2many('user.guide.tags', string='Tags')
    href = fields.Char('Link')
    user_guide_url_id = fields.Many2one('user.guide.url', 'User Guide')

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        for arg in args:
            if len(arg) > 1 and isinstance(arg, list):
                terms = arg[2].split()
                if len(terms) > 1:
                    for term in terms:
                        if term:
                            args = ['|'] + args
                            args += [['name', 'ilike', term]]
        return super(UserGuide, self).search(args, offset, limit, order, count)

    @api.model
    def create(self, vals):
        user_guide_dict = {
            'name': vals.get('name'),
            'tags_ids': vals.get('tags_ids'),
            'href': vals.get('href')
        }
        user_guide_url = self.env['user.guide.url'].create(user_guide_dict)
        result = super(UserGuide, self).create(vals)
        result.user_guide_url_id = user_guide_url.id
        return result

    def write(self, values):
        if values.get('name'):
            self.user_guide_url_id.name = values.get('name')
        if values.get('tags_ids'):
            self.user_guide_url_id.tags_ids = values.get('tags_ids')
        if values.get('href'):
            self.user_guide_url_id.href = values.get('href')
        result = super(UserGuide, self).write(values)
        return result


    def assign_user_on_group_user_guide(self):
        users = self.env['res.users'].search([])
        self.env.ref('metroerp_userguide.all_user_guide_url_groups').write({'users': [(4, user.id) for user in users]})

