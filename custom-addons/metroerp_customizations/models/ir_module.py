# -*- coding: utf-8 -*-
from odoo import models, fields, api, modules, _
import threading
import psycopg2
from odoo.exceptions import AccessDenied, UserError


class Module(models.Model):
    _inherit = "ir.module.module"

    to_buy = fields.Boolean('ERP Enterprise Module', default=False)

    @api.model
    def search(self, domain, offset=0, limit=None, order=None, count=False):
        domain += [("to_buy", "=", False)]
        return super().search(domain, offset, limit, order, count)

    def _button_immediate_function(self, function):
        if getattr(threading.currentThread(), 'testing', False):
            raise RuntimeError(
                "Module operations inside tests are not transactional and thus forbidden.\n"
                "If you really need to perform module operations to test a specific behavior, it "
                "is best to write it as a standalone script, and ask the runbot/metastorm team "
                "for help."
            )
        try:
            # This is done because the installation/uninstallation/upgrade can modify a currently
            # running cron job and prevent it from finishing, and since the ir_cron table is locked
            # during execution, the lock won't be released until timeout.
            self._cr.execute("SELECT * FROM ir_cron FOR UPDATE NOWAIT")
        except psycopg2.OperationalError:
            raise UserError(_("ERP system is currently processing a scheduled action.\n"
                              "Module operations are not possible at this time, "
                              "please try again later or contact your system administrator."))
        function(self)

        self._cr.commit()
        api.Environment.reset()
        modules.registry.Registry.new(self._cr.dbname, update_module=True)

        self._cr.commit()
        env = api.Environment(self._cr, self._uid, self._context)
        # pylint: disable=next-method-called
        config = env['ir.module.module'].next() or {}
        if config.get('type') not in ('ir.actions.act_window_close',):
            return config

        # reload the client; open the first available root menu
        menu = env['ir.ui.menu'].search([('parent_id', '=', False)])[:1]
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'menu_id': menu.id},
        }
