import copy
import functools
import dateutil.relativedelta as relativedelta
import logging

from odoo import models, fields, api, tools, _
from werkzeug import urls
from odoo.tools import safe_eval
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


try:
    # We use a jinja2 sandboxed environment to render mako templates.
    # Note that the rendering does not cover all the mako syntax, in particular
    # arbitrary Python statements are not accepted, and not all expressions are
    # allowed: only "public" attributes (not starting with '_') of objects may
    # be accessed.
    # This is done on purpose: it prevents incidental or malicious execution of
    # Python code that may break the security of the server.
    from jinja2.sandbox import SandboxedEnvironment
    jinja_template_env = SandboxedEnvironment(
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="${",
        variable_end_string="}",
        comment_start_string="<%doc>",
        comment_end_string="</%doc>",
        line_statement_prefix="%",
        line_comment_prefix="##",
        trim_blocks=True,               # do not output newline after blocks
        autoescape=True,                # XML/HTML automatic escaping
    )
    jinja_template_env.globals.update({
        'str': str,
        'quote': urls.url_quote,
        'urlencode': urls.url_encode,
        'datetime': safe_eval.datetime,
        'len': len,
        'abs': abs,
        'min': min,
        'max': max,
        'sum': sum,
        'filter': filter,
        'reduce': functools.reduce,
        'map': map,
        'round': round,

        # dateutil.relativedelta is an old-style class and cannot be directly
        # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
        # is needed, apparently.
        'relativedelta': lambda *a, **kw : relativedelta.relativedelta(*a, **kw),
    })
    jinja_safe_template_env = copy.copy(jinja_template_env)
    jinja_safe_template_env.autoescape = False
except ImportError:
    _logger.warning("jinja2 not available, templating features will not work!")


class MailRenderMixin(models.AbstractModel):
    _inherit = "mail.render.mixin"

    @api.model
    def _render_template_jinja(self, template_txt, model, res_ids, add_context=None):
        """
        override this method from mail to changes name odoo to erp when run Exception part.
        """
        # TDE FIXME: remove that brol (6dde919bb9850912f618b561cd2141bffe41340c)
        no_autoescape = self._context.get('safe')
        results = dict.fromkeys(res_ids, u"")
        if not template_txt:
            return results

        # try to load the template
        try:
            jinja_env = jinja_safe_template_env if no_autoescape else jinja_template_env
            template = jinja_env.from_string(tools.ustr(template_txt))
        except Exception:
            _logger.info("Failed to load template %r", template_txt, exc_info=True)
            return results

        # prepare template variables
        variables = self._render_jinja_eval_context()
        if add_context:
            variables.update(**add_context)
        safe_eval.check_values(variables)

        # TDE CHECKME
        # records = self.env[model].browse(it for it in res_ids if it)  # filter to avoid browsing [None]
        if any(r is None for r in res_ids):
            raise ValueError(_('Unsuspected None'))

        for record in self.env[model].browse(res_ids):
            variables['object'] = record
            try:
                render_result = template.render(variables)
            except Exception as e:
                text = str(e)
                error = text.replace('odoo', 'Erp')
                _logger.info("Failed to render template : %s" % error, exc_info=True)
                raise UserError(_("Failed to render template : %s", error))
            if render_result == u"False":
                render_result = u""
            results[record.id] = render_result
        return results