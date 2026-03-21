from odoo.http import request


class AccessTokenDetails():
    
    def token_access(token):
        if token:
            return True
        else:
            return False


    def token_access_user(token):
        token_key = token
        user_detail = {}
        user_id = request.env["res.users"].sudo().search([('token_key','=',token_key)],limit=1)
        if user_id :
            if user_id.has_group("base.group_user"):
                user_detail['user_id']=user_id.id
                user_detail['user_type']='internal'
                user_detail['access_key']=user_id.token_key
                user_detail['company']=user_id.company_id.id
            if user_id.has_group("base.group_portal"):
                user_detail['user_id']=user_id.id
                user_detail['user_type']='portal'
                user_detail['company']=user_id.company_id.id
                user_detail['access_key']=user_id.token_key
            if user_id.has_group("base.group_public"):
                user_detail['user_id']=user_id.id
                user_detail['user_type']='public'
                user_detail['company']=user_id.company_id.id
                user_detail['access_key']=user_id.token_key
            return user_detail
        else :
            return user_detail
        

