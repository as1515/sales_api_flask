from flask import request
from flask_restful import Resource
from flask_jwt_extended import (create_access_token,create_refresh_token,jwt_required,
                                fresh_jwt_required,jwt_refresh_token_required,get_jwt_claims,
                                get_jwt_identity,get_raw_jwt)
from sqlalchemy import func
from marshmallow import ValidationError
import re
from flask import current_app as app
from db import db
from blacklist import BLACKLIST
from models.users import UserModel
from models.logged import LoggedModel

class LoggedUserGet(Resource):
    @jwt_required
    def get(self):
        app.logger.info('Logged In user Get')
        claims = get_jwt_claims()
        if not claims['is_admin']:
            app.logger.info('admin previlege required')
            return {'message': 'admin previlege required'},400
        
        current_user = UserModel.find_by_user(get_jwt_identity())
        
        return [log.json() for log in LoggedModel.find_all_user(current_user.businessId)],200
    
class LoggedUserDelete(Resource):
    @jwt_required
    def delete (self, username ,businessId):
        app.logger.info('Logged In user Delete')
        claims = get_jwt_claims()
        if not claims['is_admin']:
            app.logger.info('admin previlege required')
            return {'message': 'admin previlige required'},400

        
        loggedUserDetail = LoggedModel.find_by_user_businessid(username, businessId)

        if loggedUserDetail:
            loggedUserDetail.delete_from_db()

        return {'message':'User logged status has been removed'},200