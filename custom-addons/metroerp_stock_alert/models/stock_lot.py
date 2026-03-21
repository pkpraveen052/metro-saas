from datetime import timedelta
from odoo import models, fields, api

class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"
    _description = "Expiry Product Lot/Serial"

    # def cron_generate_expiry_alerts(self):
    #     company = self.env.company
    #     days = company.expiry_alert_days or 30

    #     today = fields.Date.today()
    #     alert_before = today + timedelta(days=days)

    #     lots = self.search([
    #         ('expiration_date', '!=', False),
    #     ])

    #     activity_type = self.env.ref('mail.mail_activity_data_todo')

    #     for lot in lots:

    #         # Normalize expiration_date to date only (fix for TypeError)
    #         exp_date = lot.expiration_date
    #         if hasattr(exp_date, 'date'):
    #             exp_date = exp_date.date()

    #         # Remove old activity if date changed or no longer valid
    #         existing_activities = self.env['mail.activity'].search([
    #             ('res_id', '=', lot.id),
    #             ('res_model', '=', 'stock.production.lot'),
    #             ('activity_type_id', '=', activity_type.id),
    #             ('summary', '=', 'Product Near Expiry')
    #         ])
    #         for act in existing_activities:
    #             # If date is extended or expired beyond range → delete old activity
    #             if not (today <= exp_date <= alert_before):
    #                 act.unlink()

    #         # If date not in range → skip creating new alert
    #         if not (today <= exp_date <= alert_before):
    #             continue

    #         # If an activity already exists → skip creation
    #         if existing_activities:
    #             continue

    #         # Create new updated activity
    #         lot.activity_schedule(
    #             activity_type_id=activity_type.id,
    #             user_id=lot.create_uid.id or self.env.uid,
    #             summary="Product Near Expiry",
    #             note=(
    #                 f"Lot {lot.name} of product {lot.product_id.display_name} "
    #                 f"is expiring on {exp_date}."
    #             )
    #         )

    def cron_generate_expiry_alerts(self):
        self = self.sudo()
        today = fields.Date.today()

        activity_type = self.env.ref('mail.mail_activity_data_todo')
        lot_model = self.env['ir.model'].sudo().search([('model', '=', 'stock.production.lot')])

        # Group from your XML
        group = self.env.ref('metroerp_stock_alert.group_notify_expiry_alert')

        for company in self.env['res.company'].sudo().search([]):

            days_before = company.expiry_alert_days or 30
            alert_before = today + timedelta(days=days_before)

            company_user_ids = group.users.filtered(
                lambda u: u.company_ids and company in u.company_ids
            )

            if not company_user_ids:
                continue  # No user in this company → skip

            # Lots for this company
            lots = self.env['stock.production.lot'].sudo().search([
                ('expiration_date', '!=', False),
                ('company_id', '=', company.id),
            ])

            for lot in lots:
                exp_date = lot.expiration_date
                if hasattr(exp_date, 'date'):
                    exp_date = exp_date.date()

                if not (today <= exp_date <= alert_before):
                    continue

                existing = self.env['mail.activity'].sudo().search([
                    ('res_model_id', '=', lot_model.id),
                    ('res_id', '=', lot.id),
                    ('summary', '=', 'Product Near Expiry'),
                    ('activity_type_id', '=', activity_type.id),
                ])

                if existing:
                    continue  # Already exists → skip

                # HTML note
                note_html = f"""
                    <p><b>Product Near Expiry</b></p>
                    <p>Lot {lot.name} for product {lot.product_id.display_name} is expiring on {exp_date}.</p>
                """

                for user in company_user_ids:
                    self.env['mail.activity'].sudo().create({
                        'activity_type_id': activity_type.id,
                        'user_id': user.id,
                        'res_id': lot.id,
                        'res_model_id': lot_model.id,
                        'summary': 'Product Near Expiry',
                        'note': note_html,
                        'date_deadline': today,
                    })


