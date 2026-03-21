# -*- coding: utf-8 -*-

from odoo import api, fields, models
from lxml import etree


class UserGuideUrl(models.Model):
    _name = "user.guide.url"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'User Guide'


    name = fields.Char(string='Question')
    tags_ids = fields.Many2many('user.guide.tags', string='Tags')
    href = fields.Char('Link')

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """"
        Hide create button
        """
        res = super(UserGuideUrl, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        for node in doc.xpath("//tree"):
            node.set('create', '0')
            # node.set('import', '0')
        res['arch'] = etree.tostring(doc)
        return res

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
        return super(UserGuideUrl, self).search(args, offset, limit, order, count)
