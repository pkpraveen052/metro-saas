from odoo import models, fields, api

VIEW_TYPES = [
    ('tree', 'Tree'),
    ('form', 'Form'),
    ('graph', 'Graph'),
    ('pivot', 'Pivot'),
    ('calendar', 'Calendar'),
    ('gantt', 'Gantt'),
    ('kanban', 'Kanban'),
]

class MetroGenieSuggestion(models.Model):
    _name = "metro.genie.suggestion"
    _description = "MetroGenie Quick Search Suggestion"
    _rec_name = "name"
    _order = "sequence, name"

    name = fields.Char("Suggestion", required=True)
    # action_xml_id = fields.Char("Metro Action XML ID", required=True)
    description = fields.Text("Description")
    sequence = fields.Integer("Sequence", default=10)
    view_types = fields.Selection(VIEW_TYPES, string='View Type')
    # menu_xml_id = fields.Char("Metro Menu XML ID")
    is_button = fields.Boolean('Enable Button')
    window_action_id = fields.Many2one(
        'ir.actions.act_window',
        string='Window Action',
        help='Select the window action to be used.'
    )
    client_actions_id = fields.Many2one(
        'ir.actions.actions',
        string='Client Action',
        help='Select the window action to be used.'
    )
    menu_id = fields.Many2one(
        'ir.ui.menu',
        string='Menu Item',
        help='Select a menu to link or display'
    )
    group_ids = fields.Many2many(
        'res.groups',
        string='Access Group',
        help='Select a user group',
    compute = "_compute_model"
    )
    model = fields.Char("Model", compute = "_compute_model")
    is_accounting_report = fields.Boolean("Is Accounting Report")

    @api.depends('window_action_id', 'menu_id')
    def _compute_model(self):
        for rec in self:
            rec.model = rec.window_action_id.res_model if rec.window_action_id else False
            rec.group_ids = rec.menu_id.groups_id.ids if rec.menu_id else False

    # @api.model
    # def get_group_filtered_suggestions(self):
    #     current_user_groups = self.env.user.groups_id.ids
    #     return self.search([
    #         '|', ('group_ids', '=', False),
    #         ('group_ids', 'in', current_user_groups)
    #     ]).read(['name', 'action_id', 'menu_id', 'view_types', 'model'])

    @api.model
    def get_group_filtered_suggestions(self):
        """
        this method used to filtered record on user access group base and
        also it return record set of suggestion list.
        """
        user_group_ids = self.env.user.groups_id.ids
        suggestions = self.search([])
        result = []
        for rec in suggestions:
            if not rec.group_ids or any(g.id in user_group_ids for g in rec.group_ids):
                result.append({
                    'id': rec.id,
                    'name': rec.name,
                    'window_action_id': rec.window_action_id.id,
                    'client_actions_id': rec.client_actions_id.id,
                    'menu_id': rec.menu_id.id if rec.menu_id else False,
                    'view_types': rec.view_types,
                    'model': rec.model,
                    'is_button': rec.is_button,
                    'is_accounting_report': rec.is_accounting_report,
                })
        return result

    @api.model
    def get_sample_files(self):
        user_group_ids = self.env.user.groups_id.ids

        attachments = self.env['ir.attachment'].search([
            ('is_export', '=', True),
            ('group_ids', 'in', user_group_ids),
        ])
        print('\n\n\nattachments', attachments)
        result = []
        for att in attachments:
            result.append({
                'id': att.id,
                'name': att.name,
                'url': f'/web/content/{att.id}?download=true',
            })
        return result

