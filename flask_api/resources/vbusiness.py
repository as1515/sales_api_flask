from flask import request,current_app as app
from flask_restful import Resource
from flask_jwt_extended import (jwt_required, fresh_jwt_required,
                                jwt_refresh_token_required,get_jwt_claims, get_jwt_identity)

from marshmallow import ValidationError
import datetime

from models.zbusiness import ZbusinessModel
from models.hierarchy import HierarchyModel
from models.vbusiness import VbusinessModel
from schemas.users import vbusinessSchema


class Vbusiness(Resource):
    @jwt_required
    def get(self):
        app.logger.info('Vbusiness get')
        claims = get_jwt_claims()
        if not claims['is_superuser']:
            app.logger.info('superuser previlege required')
            return {'message': 'superuser previlege required'},400

        vbusinessDetail = VbusinessModel.find_all_business()

        return [vbusDetail.json() for vbusDetail in vbusinessDetail],200


    @jwt_required
    def post(self):
        app.logger.info('Vbusiness post')
        claims = get_jwt_claims()
        if not claims['is_superuser']:
            app.logger.info('superuser previlege required')
            return {'message': 'superuser previlege required'},400

        json_data = request.get_json()

        if not json_data:
            app.logger.info('No input data provided')
            return {'message': 'No input data provided'},400

        try:
            data = vbusinessSchema.load(json_data).data
        except ValidationError as err:
            app.logger.info(err.messages)
            return {'message':err.messages},400

        if VbusinessModel.find_by_zid(data['business_Id']):
            app.logger.info('This Business has already been registered')
            return {'message':'This Business has already been registered'},400
        
        if not ZbusinessModel.find_by_businessId(data['business_Id']):
            app.logger.info('This Business does not exist in your system')
            return {'message':'This Business does not exist in your system'},400

        ztime = datetime.datetime.now()

        vbusinessDetail = VbusinessModel(
                                        ztime=ztime,
                                        zid=data['business_Id']
                                        )

        try:
            vbusinessDetail.save_to_db()
        except Exception as e:
            app.logger.info(e)
            return {"message":"An error occured inserting the customer"},400

        return vbusinessDetail.json(),200

class VbusinessDelete(Resource):
    @jwt_required
    def delete (self, business_Id):
        app.logger.info('VbusinessDelete Delete')
        claims = get_jwt_claims()
        if not claims['is_superuser']:
            app.logger.info('admin previlige required')
            return {'message': 'admin previlige required'},400

        vbusinessDetail = VbusinessModel.find_by_zid(business_Id)

        if vbusinessDetail:
            vbusinessDetail.delete_from_db()
        app.logger.info('Business has been deleted, Admin/Users cannot access information from these businesses anymore')
        return {'message':'Business has been deleted, Admin/Users cannot access information from these businesses anymore'},200

class VbusinessNonapproved(Resource):
    @jwt_required
    def get(self):
        app.logger.info('VbusinessNonapproved get')
        claims = get_jwt_claims()
        if not claims['is_superuser']:
            app.logger.info('superuser previlege required')
            return {'message': 'superuser previlege required'},400

        zbusinessDetail = [zbusDetail.json() for zbusDetail in ZbusinessModel.find_all_business()]

        vbusinessDetail = [vbusDetail.json() for vbusDetail in VbusinessModel.find_all_business()]

        vbusinessList = [z['business_id'] for z in vbusinessDetail]
        zbusinessDict = [d for d in zbusinessDetail if d['business_id'] not in vbusinessList]


        return zbusinessDict,200

class VbusinessRegular(Resource):
    def get(self):
        app.logger.info('VbusinessRegular Get')
        vbusinessDetail = VbusinessModel.find_all_business()

        return [vbusDetail.json() for vbusDetail in vbusinessDetail],200
