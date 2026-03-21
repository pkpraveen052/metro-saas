from odoo import http
from odoo.http import request

class WapushPlusController(http.Controller):

    @http.route('/wapushplus/callback', type='http', auth='public', methods=['GET'], csrf=False)
    def handle_callback(self, **kwargs):
        """
        Handles the callback and updates the auth_code in ir.config_parameter.
        """
        code = kwargs.get('code')  # Extract the `code` parameter
        
        if code:
            try:
                # Store the auth_code in ir.config_parameter
                config_param = request.env['ir.config_parameter'].sudo()
                config_param.set_param('assistro.auth_code', code)
                return """
                    <html>
                        <body>
                            <h1>Successfully Authorized!</h1>
                            <p>Your authentication has been successfully completed.</p>
                            <h2><a href="%s">Click Here</a> to go back to Metro Application.</h2>
                        </body>
                    </html>
                """ % (request.env['ir.config_parameter'].sudo().get_param('web.base.url'))
            
            except Exception as e:
                # Error message if there’s an issue storing the code
                return """
                    <html>
                        <body>
                            <h1>Error occurred while processing the callback.</h1>
                            <p><strong>Reason:</strong> %s</p>
                            <h2><a href="%s">Click Here</a> to go back to the application.</h2>
                        </body>
                    </html>
                """ % (str(e), request.env['ir.config_parameter'].sudo().get_param('web.base.url'))
        
        # Error message if no code is received
        return """
            <html>
                <body>
                    <h1>Internal Error occurred while processing the request.</h1>
                    <p><strong>Reason:</strong> No authorization code received.</p>
                    <h2><a href="%s">Click Here</a> to go back to the application.</h2>
                </body>
            </html>
        """ % (request.env['ir.config_parameter'].sudo().get_param('web.base.url'))


        