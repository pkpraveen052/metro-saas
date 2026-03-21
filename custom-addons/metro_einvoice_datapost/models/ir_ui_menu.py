from odoo import fields, models, api


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def load_menus(self, debug=False):
        res = super(IrUiMenu, self).load_menus(debug)
        user = self.env.user

        try:
            menu_id = self.env.ref('metro_einvoice_datapost.menu_peppol_root').id
        except Exception:
            menu_id = False

        def update_menu_name(children):
            """Recursively find and rename target menu."""
            for child in children:
                if child['id'] == menu_id:
                    if user.has_group('metro_einvoice_datapost.group_c5_submitter'):
                        child['name'] = "GST InvoiceNow"
                    else:
                        child['name'] = "InvoiceNow"
                    return True  # stop recursion once found
                if child.get('children'):
                    if update_menu_name(child['children']):
                        return True
            return False

        # Start recursive search
        update_menu_name(res.get('children', []))
        return res