from flask import  request, g, current_app as app
from flask_restful import Resource
from flask_jwt_extended import (create_access_token,create_refresh_token,jwt_required,
                                fresh_jwt_required,jwt_refresh_token_required,get_jwt_claims,
                                get_jwt_identity,get_raw_jwt)
from sqlalchemy import func
from marshmallow import ValidationError
import re

from db import db
import datetime
from blacklist import BLACKLIST
from .increment import increment
from models.users import UserModel
from models.logged import LoggedModel
from models.hrmst import HrmstModel
from models.hierarchy import HierarchyModel
from models.vbusiness import VbusinessModel
from schemas.users import userRegSchema,userLogSchema,userFreshSchema,updateUserSchema
# from app.tasks import add, receive_from_client_db

#think about sending out emails when user registers
#very important to add a ztime to api user model because we need to know when a user registers

#celery change
class UserRegistration(Resource):
    def post(self):
        app.logger.info('UserRegistration post')
        json_data = request.get_json()
        
        if not json_data:
            app.logger.info('Error # 27 User Resources, No input data provided')
            return {'message': 'Error # 27 User Resources, No input data provided'},400

        try:
            data = userRegSchema.load(json_data).data
        except ValidationError as err:
            app.logger.info(err.messages)
            return err.messages,400


        if data['is_admin'] != '':
            if UserModel.verify_secret_key(data['is_admin']) == 'is_superuser':
                pass
            elif UserModel.verify_secret_key(data['is_admin']) == 'is_admin':
                pass
            else:
                app.logger.info('Please provide the correct encryption key')
                return {'message':'Please provide the correct encryption key'},400
        


        if UserModel.find_by_user(data['username']):
            app.logger.info('Response # 35 User Resources, User {} already exists'. format(data['username']))
            return {'message':'Response # 35 User Resources, User {} already exists'. format(data['username'])},400

        if not UserModel.verify_secret_key(data['is_admin']) == 'is_superuser':

            approved_zid_list = VbusinessModel.find_all_business_list()

            approved_zid_length = len(approved_zid_list)

            if approved_zid_length == 0:
                app.logger.info('Error # 44 in User Resources, Super user has not registered any business for you to use')
                return {'message':'Error # 44 in User Resources, Super user has not registered any business for you to use'},400

            if (data['businessId'] != 0 and data['employeeCode'] != "" and approved_zid_length > 0):

                if data['businessId'] not in approved_zid_list:
                    app.logger.info('Error # 56 User Resources, This business is not authorized in your system please talk to your IT administrator')
                    return {'message':'Error # 56 User Resources, This business is not authorized in your system please talk to your IT administrator'},400

                if UserModel.find_by_busIdempCode(data['username'],data['businessId'],data['employeeCode']):
                    app.logger.info('Error # 59 User Resources, This Business ID and Employee Code already exists talk to your adminstrator to Provide you with a new businessId')
                    return {'message': 'Error # 59 User Resources, This Business ID and Employee Code already exists talk to your adminstrator to Provide you with a new businessId'},400

                if not HrmstModel.find_by_EmployeeDetail(data['businessId'],data['employeeCode']):
                    app.logger.info('Error # 62 User Resources, Your Employee Code for Business ID provided does not exist in our system or does not match!')
                    return {'message':'Error # 62 User Resources, Your Employee Code for Business ID provided does not exist in our system or does not match!'},400

            terminalMax = str(db.session.query(func.max(UserModel.terminal)).first())
            terminalMax = re.sub('[(",)]','',terminalMax)
            terminalMax = terminalMax.replace("'","")

            if terminalMax == 'Super':
                terminalId = 'T0001'
            else:
                terminalId = str(terminalMax)
                terminalId = increment(terminalId)

            employee_name = HrmstModel.find_by_EmployeeDetail(data['businessId'],data['employeeCode']).xname
        else:
            data['username'] = 'Superuser'
            employee_name = 'Superuser'
            data['businessId'] = 1
            data['employeeCode'] = 'Super'
            terminalId = 'Super'

        new_user = UserModel(
                            username = data['username'],
                            password = UserModel.generate_hash(data['password']),
                            employee_name = employee_name,
                            email = data['email'],
                            mobile = data['mobile'],
                            businessId = data['businessId'],
                            employeeCode = data['employeeCode'],
                            terminal = terminalId,
                            is_admin = UserModel.verify_secret_key(data['is_admin']),
                            status = UserModel.verify_active_user(data['is_admin'])
                            )
        try:
            new_user.save_to_db()
            if UserModel.verify_secret_key(data['is_admin']) == 'is_admin':
                adminHierarchyDetail = HierarchyModel(
                                                    username=data['username'],
                                                    business_Id=data['businessId'],
                                                    employee_code = data['employeeCode'],
                                                    employee_name = employee_name,
                                                    child_of_code = 'Super',
                                                    child_of_name = 'Superuser'
                                                    )
                adminHierarchyDetail.save_to_db()

            access_token = create_access_token(identity = data['username'])
            refresh_token = create_refresh_token(identity = data['username'])
            current_user = UserModel.find_by_user(data['username'])

            return {
                    'message': 'Response # 148 User Resources, User {} was created'.format(data['username']),
                    'access_token':access_token,
                    'refresh_token':refresh_token,
                    'businessId': current_user.businessId,
                    'employeeCode':current_user.employeeCode,
                    'userRole': current_user.is_admin
                    },200
        except Exception as err:
            app.logger.info('Error # 155 User Resources, Issues with saving to database')
            return {'message':'Error # 155 User Resources, Issues with saving to database'},400


class UserLogin(Resource):
    def post(self):
        app.logger.info('Userlogin Post')
        json_data = request.get_json()

        if not json_data:
            app.logger.info('No input data provided')
            return {'message': 'No input data provided'},400

        try:
            data = userLogSchema.load(json_data).data
        except ValidationError as err:
            app.logger.info(err.messages)
            return err.messages,400

        try:
            current_user = UserModel.find_by_user(data['username'])
        except KeyError:
            app.logger.info('Sorry no username has been provided')
            return {'message':'Sorry no username has been provided'},400

        if not current_user:
            app.logger.info('User {} doesn\'t exist'.format(data['username']))
            return {'message': 'User {} doesn\'t exist'.format(data['username'])},400

        if current_user.status == 'inactive':
            app.logger.info('Your account has not been activated by the admin, please talk to your manager')
            return {'message': 'Your account has not been activated by the admin, please talk to your manager'},400

        try:
            logged_user = LoggedModel.find_by_user_businessid(current_user.username, current_user.businessId)
        except Exception as err:
            app.logger.info(err)
        
        if logged_user:    
            if current_user.username == logged_user.username:
                app.logger.info('You are already logged in, only one session allowed per user')
                return {'message':'You are already logged in, only one session allowed per user'}, 400 

        if UserModel.verify_hash(data['password'],current_user.password):
            access_token = create_access_token(identity = data['username'])
            refresh_token = create_refresh_token(identity = data['username'])
            
            login_user = LoggedModel(
                    ztime = datetime.datetime.now(),
                    zutime = datetime.datetime.now(),
                    username = current_user.username,
                    businessId = current_user.businessId,
                    access_token = access_token,
                    refresh_token = refresh_token,
                    status = 'Logged In'
            )

            try:
                login_user.save_to_db()
            except Exception as err:
                app.logger.info('Error # 171 could not save to logged user')
                return {'message':'Error # 171 could not save to logged user'}

            return {
                    'message': 'Logged in as {}'.format(current_user.username),
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'businessId': current_user.businessId,
                    'employeeCode' : current_user.employeeCode,
                    'userRole': current_user.is_admin,
                    'employee_name':current_user.employee_name
                    },200
        else:
            app.logger.info('Wrong credentials')
            return {'message': 'Wrong credentials'},400

class TokenRefresh(Resource):
    @jwt_refresh_token_required
    def post(self):
        app.logger.info('TokenRefresh post')
        current_user = get_jwt_identity()
        access_token = create_access_token(identity = current_user)
        app.logger.info('refresh token accessed')
        return {'access_token':access_token},200

class AccessFreshToken(Resource):
    @jwt_required
    def post(self):
        app.logger.info('AccessFreshToken post')
        json_data = request.get_json()

        if not json_data:
            app.logger.info('No input data provided')
            return {'message': 'No input data provided'},400

        try:
            data = userFreshSchema.load(json_data).data
        except ValidationError as err:
            app.logger.info(err.messages)
            return err.messages,400

        current_user = UserModel.find_by_user(get_jwt_identity())
        app.logger.info(current_user)
        if UserModel.verify_hash(data['password'],current_user.password):
            access_token = create_access_token(identity = current_user.username, fresh = True)
            return {'access_token':access_token},200
        else:
            app.logger.info('The Password you entered is incorrect')
            return {'message':'The Password you entered is incorrect'},400

class UserLogout(Resource):
    @jwt_required
    def post(self):
        app.logger.info('Userlogout post')
        current_user = UserModel.find_by_user(get_jwt_identity())
        logged_user = LoggedModel.find_by_user_businessid(current_user.username, current_user.businessId)
        logged_user.delete_from_db()

        jti = get_raw_jwt()['jti']
        try:
            BLACKLIST.add(jti)
            app.logger.info('You have been Successfully Logged Out')
            return {'message':'You have been Successfully Logged Out'},200
        except Exception as e:
            app.logger.info(e)
            return {'message':'Sorry Something went wrong with our server'},400

#celery change
class UpdateUser(Resource):
    @fresh_jwt_required
    def put(self):
        app.logger.info('Updateuser Put')
        json_data = request.get_json()

        if not json_data:
            app.logger.info('No input data provided update user')
            return {'message': 'No input data provided'},400

        try:
            data = updateUserSchema.load(json_data).data
        except ValidationError as err:
            app.logger.info(err.messages)
            return err.messages,400

        current_user = UserModel.find_by_user(get_jwt_identity())

        if current_user:
            current_user.password=UserModel.generate_hash(data['password'])
            current_user.email=data['email']
            current_user.mobile=data['mobile']

        try:
            current_user.save_to_db()
            app.logger.info('Your Information was Successfully Updated')
            return {'message':'Your Information was Successfully Updated'},200
        except Exception as e:
            app.logger.info(e)
            return {"message":"An error update the customer"},400

class UserStatusActive(Resource):
    @jwt_required
    def get(self):
        app.logger.info('UserstatusActive get')
        claims = get_jwt_claims()
        if not claims['is_admin']:
            app.logger.info('admin previlege required')
            return {'message': 'admin previlege required'},400

        current_user = UserModel.find_by_user(get_jwt_identity())
        zid = current_user.businessId
        dataActive = [statusL.json() for statusL in UserModel.find_by_status(zid,'active')]
        dataHierarchy = [hierarchy.json() for hierarchy in HierarchyModel.find_all_hierarchy()]

        for i in dataActive:
            i['child_of_code'] = ''
            i['child_of_name'] = ''
            for j in dataHierarchy:
                if i['employeeCode'] == j['employee_code']:
                    i['child_of_code'] = j['child_of_code']
                    i['child_of_name'] = j['child_of_name']
        return dataActive,200

class UserStatusInactive(Resource):
    @jwt_required
    def get(self):
        app.logger.info('UserStatusInactive get')
        claims = get_jwt_claims()
        if not claims['is_admin']:
            app.logger.info('admin previlege required')
            return {'message': 'admin previlege required'},400

        current_user = UserModel.find_by_user(get_jwt_identity())
        data = [statusL.json() for statusL in UserModel.find_by_status(current_user.businessId,'inactive')]
        return data,200

class EmployeeCodeList(Resource):
    def get(self, businessId):
        app.logger.info('EmployeeCodeList get')
        businessIdList = VbusinessModel.find_all_business_list()

        if businessId not in businessIdList:
            app.logger.info('This business has not been Validated by the super user for you to use')
            return {'message':'This business has not been Validated by the super user for you to use'},400

        data = [empCode.json() for empCode in HrmstModel.find_by_zid(businessId)]
        return data,200


# class HrmstList(Resource):
#     @jwt_required
#     def get(self):
#         claims = get_jwt_claims()
#         print(claims)
#         if not claims['active']:
#             return {'message': 'Error # 171 in Customer Resource, You have not been activated by the admin'},400

#         try:
#             #i think we need to import this
#             receive_from_client_db(HrmstModel.__tablename__, HrmstModel.__table__.c.keys())
#         except Exception as e:
#             print(e)

#         return 'Hr data synced'

#celery change
class UserDelete(Resource):
    @jwt_required
    def delete(self, username):
        app.logger.info('UserDelete delete')
        claims = get_jwt_claims()
        if not claims['is_admin']:
            app.logger.info('admin previlege required')
            return {'message': 'admin previlege required'},400

        if not UserModel.find_by_user(username):
            app.logger.info('This user does not exist in our system')
            return {'message':'This user does not exist in our system'},400

        parent_list = [parent.json()['child_of_code'] for parent in HierarchyModel.find_all_hierarchy()]

        if not username in parent_list:
            userDetail = UserModel.find_by_user(username)
            userDetail.delete_from_db()
            app.logger.info('User has been deleted from our system')
            return {'message':'User has been deleted from our system'},200
        app.logger.info('User still has children please assign children to other parent and then delete this user')
        return {'message':'User still has children please assign children to other parent and then delete this user'},400
