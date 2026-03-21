# -*- coding: utf-8 -*-

import collections
from collections import defaultdict, OrderedDict

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError


# special columns automatically created by the ORM
LOG_ACCESS_COLUMNS = ['create_uid', 'create_date', 'write_uid', 'write_date']


class BaseModelExtend(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def search(self, domain, offset=0, limit=None, order=None, count=False):
        res = super().search(domain, offset, limit, order, count)
        if not count and self._name == "payment.acquirer":
            res = res.filtered(lambda a: not a.module_to_buy)
        return res

    def write(self, vals):
        """ write(vals)

        Updates all records in the current set with the provided values.

        :param dict vals: fields to update and the value to set on them e.g::

                {'foo': 1, 'bar': "Qux"}

            will set the field ``foo`` to ``1`` and the field ``bar`` to
            ``"Qux"`` if those are valid (otherwise it will trigger an error).

        :raise AccessError: * if user has no write rights on the requested object
                            * if user tries to bypass access rules for write on the requested object
        :raise ValidationError: if user tries to enter invalid value for a field that is not in selection
        :raise UserError: if a loop would be created in a hierarchy of objects a result of the operation (such as setting an object as its own parent)

        * For numeric fields (:class:`~odoo.fields.Integer`,
          :class:`~odoo.fields.Float`) the value should be of the
          corresponding type
        * For :class:`~odoo.fields.Boolean`, the value should be a
          :class:`python:bool`
        * For :class:`~odoo.fields.Selection`, the value should match the
          selection values (generally :class:`python:str`, sometimes
          :class:`python:int`)
        * For :class:`~odoo.fields.Many2one`, the value should be the
          database identifier of the record to set
        * Other non-relational fields use a string for value

          .. danger::

              for historical and compatibility reasons,
              :class:`~odoo.fields.Date` and
              :class:`~odoo.fields.Datetime` fields use strings as values
              (written and read) rather than :class:`~python:datetime.date` or
              :class:`~python:datetime.datetime`. These date strings are
              UTC-only and formatted according to
              :const:`odoo.tools.misc.DEFAULT_SERVER_DATE_FORMAT` and
              :const:`odoo.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT`
        * .. _openerp/models/relationals/format:

          :class:`~odoo.fields.One2many` and
          :class:`~odoo.fields.Many2many` use a special "commands" format to
          manipulate the set of records stored in/associated with the field.

          This format is a list of triplets executed sequentially, where each
          triplet is a command to execute on the set of records. Not all
          commands apply in all situations. Possible commands are:

          ``(0, 0, values)``
              adds a new record created from the provided ``value`` dict.
          ``(1, id, values)``
              updates an existing record of id ``id`` with the values in
              ``values``. Can not be used in :meth:`~.create`.
          ``(2, id, 0)``
              removes the record of id ``id`` from the set, then deletes it
              (from the database). Can not be used in :meth:`~.create`.
          ``(3, id, 0)``
              removes the record of id ``id`` from the set, but does not
              delete it. Can not be used in
              :meth:`~.create`.
          ``(4, id, 0)``
              adds an existing record of id ``id`` to the set.
          ``(5, 0, 0)``
              removes all records from the set, equivalent to using the
              command ``3`` on every record explicitly. Can not be used in
              :meth:`~.create`.
          ``(6, 0, ids)``
              replaces all existing records in the set by the ``ids`` list,
              equivalent to using the command ``5`` followed by a command
              ``4`` for each ``id`` in ``ids``.
        """
        ctx = self._context or {}
        if not self:
            return True

        self.check_access_rights('write')
        self.check_field_access_rights('write', vals.keys())
        self.check_access_rule('write')
        env = self.env

        bad_names = {'id', 'parent_path'}
        if self._log_access:
            # the superuser can set log_access fields while loading registry
            if not(self.env.uid == SUPERUSER_ID and not self.pool.ready):
                bad_names.update(LOG_ACCESS_COLUMNS)

        determine_inverses = defaultdict(list)      # {inverse: fields}
        records_to_inverse = {}                     # {field: records}
        relational_names = []
        protected = set()
        check_company = False
        for fname in vals:
            field = self._fields.get(fname)
            if not field:
                raise ValueError("Invalid field %r on model %r" % (fname, self._name))
            if field.inverse:
                if field.type in ('one2many', 'many2many'):
                    # The written value is a list of commands that must applied
                    # on the field's current value. Because the field is
                    # protected while being written, the field's current value
                    # will not be computed and default to an empty recordset. So
                    # make sure the field's value is in cache before writing, in
                    # order to avoid an inconsistent update.
                    self[fname]
                determine_inverses[field.inverse].append(field)
                # DLE P150: `test_cancel_propagation`, `test_manufacturing_3_steps`, `test_manufacturing_flow`
                # TODO: check whether still necessary
                records_to_inverse[field] = self.filtered('id')
            if field.relational or self._field_inverses[field]:
                relational_names.append(fname)
            if field.inverse or (field.compute and not field.readonly):
                if field.store or field.type not in ('one2many', 'many2many'):
                    # Protect the field from being recomputed while being
                    # inversed. In the case of non-stored x2many fields, the
                    # field's value may contain unexpeced new records (created
                    # by command 0). Those new records are necessary for
                    # inversing the field, but should no longer appear if the
                    # field is recomputed afterwards. Not protecting the field
                    # will automatically invalidate the field from the cache,
                    # forcing its value to be recomputed once dependencies are
                    # up-to-date.
                    protected.update(self.pool.field_computed.get(field, [field]))
            if fname == 'company_id' or (field.relational and field.check_company):
                check_company = True
        # protect fields being written against recomputation
        with env.protecting(protected, self):
            # Determine records depending on values. When modifying a relational
            # field, you have to recompute what depends on the field's values
            # before and after modification.  This is because the modification
            # has an impact on the "data path" between a computed field and its
            # dependency.  Note that this double call to modified() is only
            # necessary for relational fields.
            #
            # It is best explained with a simple example: consider two sales
            # orders SO1 and SO2.  The computed total amount on sales orders
            # indirectly depends on the many2one field 'order_id' linking lines
            # to their sales order.  Now consider the following code:
            #
            #   line = so1.line_ids[0]      # pick a line from SO1
            #   line.order_id = so2         # move the line to SO2
            #
            # In this situation, the total amount must be recomputed on *both*
            # sales order: the line's order before the modification, and the
            # line's order after the modification.
            self.modified(relational_names, before=True)

            real_recs = self.filtered('id')

            # If there are only fields that do not trigger _write (e.g. only
            # determine inverse), the below ensures that `write_date` and
            # `write_uid` are updated (`test_orm.py`, `test_write_date`)
            if self._log_access and self.ids:
                towrite = env.all.towrite[self._name]

                for record in real_recs:
                    towrite[record.id]['write_uid'] = self.env.uid
                    if ctx.get('import_file') and self.__class__.__name__ == 'account.move':
                        if 'write_date' in vals:
                            towrite[record.id]['write_date'] = vals['write_date']
                        elif 'custom_write_date' in vals:
                            towrite[record.id]['write_date'] = vals['custom_write_date']
                        else:
                            towrite[record.id]['write_date'] = False
                    else:
                        towrite[record.id]['write_date'] = False
                self.env.cache.invalidate([
                    (self._fields['write_date'], self.ids),
                    (self._fields['write_uid'], self.ids),
                ])

            # for monetary field, their related currency field must be cached
            # before the amount so it can be rounded correctly
            for fname in sorted(vals, key=lambda x: self._fields[x].type=='monetary'):
                if fname in bad_names:
                    continue
                field = self._fields[fname]
                field.write(self, vals[fname])

            # determine records depending on new values
            #
            # Call modified after write, because the modified can trigger a
            # search which can trigger a flush which can trigger a recompute
            # which remove the field from the recompute list while all the
            # values required for the computation could not be yet in cache.
            # e.g. Write on `name` of `res.partner` trigger the recompute of
            # `display_name`, which triggers a search on child_ids to find the
            # childs to which the display_name must be recomputed, which
            # triggers the flush of `display_name` because the _order of
            # res.partner includes display_name. The computation of display_name
            # is then done too soon because the parent_id was not yet written.
            # (`test_01_website_reset_password_tour`)
            self.modified(vals)
            if self._parent_store and self._parent_name in vals:
                self.flush([self._parent_name])

            # validate non-inversed fields first
            inverse_fields = [f.name for fs in determine_inverses.values() for f in fs]
            real_recs._validate_fields(vals, inverse_fields)

            for fields in determine_inverses.values():
                # write again on non-stored fields that have been invalidated from cache
                for field in fields:
                    if not field.store and any(self.env.cache.get_missing_ids(real_recs, field)):
                        field.write(real_recs, vals[field.name])

                # inverse records that are not being computed
                try:
                    fields[0].determine_inverse(real_recs)
                except AccessError as e:
                    if fields[0].inherited:
                        description = self.env['ir.model']._get(self._name).name
                        raise AccessError(
                            _("%(previous_message)s\n\nImplicitly accessed through '%(document_kind)s' (%(document_model)s).") % {
                                'previous_message': e.args[0],
                                'document_kind': description,
                                'document_model': self._name,
                            }
                        )
                    raise

            # validate inversed fields
            real_recs._validate_fields(inverse_fields)

        if check_company and self._check_company_auto:
            self._check_company()
        return True
        # return super(BaseModelExtend, self).write(vals)