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
from .increment import increment
from models.users import UserModel
from models.hrmst import HrmstModel
from models.zbusiness import ZbusinessModel
from models.hierarchy import HierarchyModel
from models.vbusiness import VbusinessModel
from schemas.users import hierarchySchema,hierarchyUpdateSchema

class Hierarchy(Resource):
    @jwt_required
    def post(self):
        app.logger.info('Hierarchy post')
        claims = get_jwt_claims()
        if not claims['is_admin']:
            app.logger.info('admin previlege required')
            return {'message': 'admin previlege required'},400

        current_user = UserModel.find_by_user(get_jwt_identity())

        approved_zid_list = VbusinessModel.find_all_business_list()

        if (current_user.businessId not in approved_zid_list):
            app.logger.info('Error # 180 in Product Resource, You have not been authorized to use this business')
            return {'message': 'Error # 180 in Product Resource, You have not been authorized to use this business'},400

        json_data = request.get_json()

        if not json_data:
            app.logger.info('No input data provided')
            return {'message': 'No input data provided'},400

        try:
            data = hierarchySchema.load(json_data).data
        except ValidationError as err:
            app.logger.info(err.messages)
            return err.messages,400

        if not UserModel.find_by_user(data['username']):
            app.logger.info('This user has not registered yet')
            return {'message':'This user has not registered yet'},400

        if not HrmstModel.find_by_EmployeeDetail(data['business_Id'],data['employee_code']):
            app.logger.info('The employee code you provided does not exist in our system')
            return {'message':'The employee code you provided does not exist in our system'},400

        if not current_user.businessId == data['business_Id']:
            app.logger.info('You are not the admin for this user')
            return {'message': 'You are not the admin for this user'},400

        if HierarchyModel.find_by_hierarchy(data['username']):
            app.logger.info('This user name has already been activated by the admin')
            return {'message':'This user name has already been activated by the admin'},400

        new_user = HierarchyModel(username = data['username'],
                                business_Id = data['business_Id'],
                                employee_code = data['employee_code'],
                                employee_name = data['employee_name'],
                                child_of_code = data['child_of_code'],
                                child_of_name = data['child_of_name'])

        try:
            new_user.save_to_db()
            activeUser = UserModel.find_by_user(data['username'])
            activeUser.status = 'active'
            activeUser.save_to_db()
            app.logger.info('User has been added to hierarchy and activated')
            return {'message':'User has been added to hierarchy and activated'},200
        except:
            app.logger.info('Something went wrong')
            return {'message':'Something went wrong'},400

    @jwt_required
    def put(self):
        app.logger.info('hierarchy put')
        claims = get_jwt_claims()
        if not claims['is_admin']:
            app.logger.info('admin previlege required')
            return {'message': 'admin previlege required'},400

        current_user = UserModel.find_by_user(get_jwt_identity())

        json_data = request.get_json()

        if not json_data:
            app.logger.info('No input data provided')
            return {'message': 'No input data provided'},400

        try:
            data = hierarchyUpdateSchema.load(json_data).data
        except ValidationError as err:
            app.logger.info(err.messages)
            return err.messages,400

        if not current_user.businessId == data['business_Id']:
            app.logger.info('You are not the admin for this user')
            return {'message': 'You are not the admin for this user'},400

        employee_to_change = HierarchyModel.find_by_employee_code(data['employee_code'])
        

        if employee_to_change.child_of_code == data['child_of_code']:
            app.logger.info('You cannot change the parent to the already existing parent')
            return {'message':'You cannot change the parent to the already existing parent'},400

        employee_to_change.child_of_code = data['child_of_code']
        employee_to_change.child_of_name = data['child_of_name']

        try:
            employee_to_change.save_to_db()
            app.logger.info('Employee hierarchy has been updated')
            return {'message':'Employee hierarchy has been updated'},200
        except:
            app.logger.info('Something went wrong while updating information to your server')
            return {'message':'Something went wrong while updating information to your server'},400


class HierarchyDelete(Resource):
    @jwt_required
    def delete(self,username):
        app.logger.info('HierarchyDelete delete')
        claims = get_jwt_claims()
        if not claims['is_admin']:
            app.logger.info('admin previlege required')
            return {'message': 'admin previlege required'},400

        current_user = UserModel.find_by_user(get_jwt_identity())
        user = UserModel.find_by_user(username)

        if not user:
            app.logger.info('This user does not exist in our system')
            return {'message':'This user does not exist in our system'},400

        if current_user.username == HierarchyModel.find_by_hierarchy(username).username:
            app.logger.info('You are not allowed to delete yourself')
            return {'message': 'You are not allowed to delete yourself'},400

        if not current_user.businessId == HierarchyModel.find_by_hierarchy(username).business_Id:
            app.logger.info('You are not the admin for this user')
            return {'message': 'You are not the admin for this user'},400

        parent_list = [parent.json()['child_of_code'] for parent in HierarchyModel.find_all_hierarchy()]

        if not user.employeeCode in parent_list:
            hierarchyDetail = HierarchyModel.find_by_hierarchy(username)
            hierarchyDetail.delete_from_db()
            userDetail = UserModel.find_by_user(username)
            userDetail.status = 'inactive'
            userDetail.save_to_db()
            app.logger.info('User has been deleted from your hierarchy')
            return {'message':'User has been deleted from your hierarchy'},200
        else:
            app.logger.info('You cannot delete this user, please replace child first')
            return {'message':'You cannot delete this user, please replace child first'}


class HierarchyNonparent(Resource):
    @jwt_required
    def get(self):
        app.logger.info('HierarchyNonparent get')
        claims = get_jwt_claims()
        if not claims['is_admin']:
            app.logger.info('admin previlege required')
            return {'message': 'admin previlege required'},400

        parent_list = [parent.json()['child_of_code'] for parent in HierarchyModel.find_all_hierarchy()]
        total_hierarchy_employee_code_list = [total.json()['employee_code'] for total in HierarchyModel.find_all_hierarchy()]
        non_parent = list(set(total_hierarchy_employee_code_list) - set(parent_list))
        total_hierarchy = [nparent.json() for nparent in HierarchyModel.find_all_hierarchy() if nparent.json()['employee_code'] in non_parent]

        return total_hierarchy,200

class HierarchyParent(Resource):
    @jwt_required
    def get(self):
        app.logger.info('HierarchyParent get')
        claims = get_jwt_claims()
        if not claims['is_admin']:
            app.logger.info('admin previlege required')
            return {'message': 'admin previlege required'},400

        parent_list = [parent.json() for parent in HierarchyModel.find_all_hierarchy()]

        return parent_list,200
