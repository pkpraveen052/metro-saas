from odoo import models, fields, api, _


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _notify_classify_recipients(self, recipient_data, model_name, msg_vals=None):
        """ OVERIDDEN METHOD from mail/

        Classify recipients to be notified of a message in groups to have
        specific rendering depending on their group. For example users could
        have access to buttons customers should not have in their emails.
        Module-specific grouping should be done by overriding ``_notify_get_groups``
        method defined here-under.
        :param recipient_data:todo xdo UPDATE ME
                eg: [{'id': 3941, 'active': True, 'share': True, 'groups': [None], 'notif': 'email', 'type': 'customer'}, 
                    {'id': 41283, 'active': True, 'share': True, 'groups': [None], 'notif': 'email', 'type': 'customer'}]
        :param: msg_vals eg: {'email_layout_xmlid': 'mail.mail_notification_paynow', 'no_auto_thread': False, 'mail_server_id': False, 'mail_activity_type_id': False, 'author_id': 3, 'email_from': '"Administrator" <no-reply@metrogroup.solutions>', 'model': 'sale.order', 'res_id': 2337, 'body': '<div style=\'font-size:13px; font-family:"Lucida Grande", Helvetica, Verdana, Arial, sans-serif; margin:0px; padding:0px\'>\n    <p style=\'margin:0px; font-size:13px; font-family:"Lucida Grande", Helvetica, Verdana, Arial, sans-serif; padding:0px\'>\n        Hello,\n        <br><br>\n        Your\n            quotation <strong style="font-weight:bolder">S00052</strong>\n            amounting in <strong style="font-weight:bolder">S$\xa01.00</strong> is ready for review.\n        <br><br>\n        Do not hesitate to contact us if you have any questions.\n        <br>\n    </p>\n</div>\n            ', 'subject': 'Metro Group Pte Ltd Quotation (Ref S00052)', 'message_type': 'comment', 'parent_id': 68725, 'subtype_id': 1, 'partner_ids': {41283, 3941}, 'channel_ids': set(), 'add_sign': False, 'record_name': 'S00052', 'attachment_ids': [(4, 92607)]}
        :param model_name  eg: Quotation
        return example:
        [{
            'actions': [],
            'button_access': {'title': 'View Simple Chatter Model',
                                'url': '/mail/view?model=mail.test.simple&res_id=1497'},
            'has_button_access': False,
            'recipients': [11]
        },
        {
            'actions': [],
            'button_access': {'title': 'View Simple Chatter Model',
                            'url': '/mail/view?model=mail.test.simple&res_id=1497'},
            'has_button_access': False,
            'recipients': [4, 5, 6] 
        },
        {
            'actions': [],
            'button_access': {'title': 'View Simple Chatter Model',
                                'url': '/mail/view?model=mail.test.simple&res_id=1497'},
            'has_button_access': True,
            'recipients': [10, 11, 12]
        }]
        only return groups with recipients
        """
        # keep a local copy of msg_vals as it may be modified to include more information about groups or links
        local_msg_vals = dict(msg_vals) if msg_vals else {}
        groups = self._notify_get_groups(msg_vals=local_msg_vals)
        access_link = self._notify_get_action_link('view', **local_msg_vals)

        if model_name:
            view_title = _('View %s', model_name)
        else:
            view_title = _('View')

        # fill group_data with default_values if they are not complete
        temp_url = {} #Metro code
        for group_name, group_func, group_data in groups:
            group_data.setdefault('notification_group_name', group_name)
            group_data.setdefault('notification_is_customer', False)
            is_thread_notification = self._notify_get_recipients_thread_info(msg_vals=msg_vals)['is_thread_notification']
            group_data.setdefault('has_button_access', is_thread_notification)
            group_button_access = group_data.setdefault('button_access', {})
            group_button_access.setdefault('url', access_link)
            group_button_access.setdefault('title', view_title)
            group_data.setdefault('actions', list())
            group_data.setdefault('recipients', list())
            #Metro code starts
            if not temp_url and group_data.get('button_access', {}) and 'access_token' in group_data['button_access'].get('url'):
                temp_url = group_data['button_access'].get('url')
            #Metro code ends

        # classify recipients in each group
        for recipient in recipient_data:
            for group_name, group_func, group_data in groups:               
                if group_func(recipient):
                    group_data['recipients'].append(recipient['id'])
                    #Metro code starts
                    if not group_data.get('notification_is_customer'):
                        group_data['notification_is_customer'] = True
                        # group_data['has_button_access'] = True
                        group_data['button_access']['url'] = temp_url
                    #Metro code ends
                    break

        result = []
        for group_name, group_method, group_data in groups:
            if group_data['recipients']:
                result.append(group_data)

        return result