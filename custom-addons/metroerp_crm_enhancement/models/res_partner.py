
from odoo import models, fields, api,_
class ResPartnerInherited(models.Model):
    _inherit = "res.partner"


    def _compute_meeting(self):
        if not self.ids:
            return {}

        all_partners = self.with_context(active_test=False).search([
            ('id', 'child_of', self.ids)
        ])

        # FIX: Avoid empty tuple error IN ()
        partner_ids = all_partners.ids or [0]

        event_id = self.env['calendar.event']._search([])  # ir.rules applied
        subquery_string, subquery_params = event_id.select()
        subquery = self.env.cr.mogrify(subquery_string, subquery_params).decode()

        self.env.cr.execute("""
            SELECT res_partner_id, calendar_event_id, count(1)
              FROM calendar_event_res_partner_rel
             WHERE res_partner_id IN %s 
               AND calendar_event_id IN ({})
          GROUP BY res_partner_id, calendar_event_id
        """.format(subquery), [tuple(partner_ids)])

        meeting_data = self.env.cr.fetchall()

        # Build {partner_id: set(event_ids)}
        meetings = {}
        for p_id, m_id, _ in meeting_data:
            meetings.setdefault(p_id, set()).add(m_id)

        # Add parent mappings
        for p_id in list(meetings.keys()):
            partner = self.browse(p_id)
            while partner.parent_id:
                partner = partner.parent_id
                if partner.id in self.ids:
                    meetings.setdefault(partner.id, set()).update(meetings[p_id])

        return {
            p_id: list(meetings.get(p_id, []))
            for p_id in self.ids
        }

    