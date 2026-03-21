from odoo import models, fields, api, _
# import subprocess
# import tempfile
# import whisper
# import openai
# import json
# import pyaudio
# import wave

class MetroGenieDashboard(models.TransientModel):
    _name = "metro.genie.dashboard"
    _description = "MetroGenie AI Dashboard"

    @api.model
    def default_get(self, fields_list):
        res = super(MetroGenieDashboard, self).default_get(fields_list)
        res['current_user_name'] = self.env.user.name
        return res

    action_input = fields.Text("Search Suggestion")
    current_user_name = fields.Char(string="Current User")
    chat_input = fields.Text("Chat Input")

