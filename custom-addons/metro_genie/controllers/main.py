# import tempfile
import whisper
import requests
from odoo import http
from odoo.http import request

class MetroGenieController(http.Controller):

    @http.route('/metro_genie/transcribe', type='http', auth='user', methods=['POST'], csrf=False)
    def transcribe(self, **kw):
        audio = request.httprequest.files.get('audio')
        if audio:
            with tempfile.NamedTemporaryFile(suffix=".wav") as f:
                audio.save(f.name)
                model = whisper.load_model("base")
                result = model.transcribe(f.name)
                return request.make_response(result["text"])
        return request.make_response("")

    @http.route('/metro_genie/parse_intent', type='json', auth='user', methods=['POST'], csrf=False)
    def parse_intent(self, **post):
        text = post.get('text')
        company_id = request.env.company.id
        api_url = "https://api.gemini-flash.com/v2/parse"
        api_key = "YOUR_GEMINI_API_KEY"
        payload = {
            "text": text,
            "company_id": company_id,
            "user_id": request.env.user.id,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        resp = requests.post(api_url, json=payload, headers=headers)
        if resp.ok:
            return resp.json()
        return {"error": "Failed to call Gemini API."}