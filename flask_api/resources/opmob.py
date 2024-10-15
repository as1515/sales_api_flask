from flask import request
from flask_restful import Resource
from flask import current_app as app
from marshmallow import ValidationError
from sqlalchemy import func, not_
import datetime
import ast
from flask_jwt_extended import (jwt_required,fresh_jwt_required,get_jwt_claims,get_jwt_identity)
import datetime

from db import db
from .increment import increment, clean

from models.cacus import CacusModel
from models.caitem import CaitemModel
from models.users import UserModel
from models.opmob import OpmobModel
from models.vbusiness import VbusinessModel
from models.hierarchy import HierarchyModel
from schemas.opmob import opmobSchemas
from models.opspprc import OpspprcModel
from resources.mail import (send_mail,dict2htmltable)
import uuid
# from app.tasks import *
# from app.tasks import receive_from_client_db


class Opmob(Resource):
    @jwt_required
    def post(self):
        username = UserModel.find_by_user(get_jwt_identity())
        app.logger.info(f'Opmob post by {username.username} email is {username.email}')
        claims = get_jwt_claims()
        if not claims['active']:
            app.logger.info('Error # 25 in Order Resource, You have not been activated by the admin')
            return {'message': 'Error # 25 in Order Resource, You have not been activated by the admin'},400

        # username = UserModel.find_by_user(get_jwt_identity())
        approved_zid_list = VbusinessModel.find_all_business_list()
        app.logger.info(username.username)
        if username.businessId not in approved_zid_list:
            app.logger.info('Error # 182 in Customer Resource, You have not been authorized to use this business')
            return {'message': 'Error # 182 in Customer Resource, You have not been authorized to use this business'},400

        json_data = request.get_json()
        
        if not json_data:
            app.logger.info('No input data provided')
            return {'message': 'No input data provided'},400

        try:
            data = opmobSchemas.load(json_data).data
        except ValidationError as err:
            app.logger.info(err.messages)
            return err.messages,400
        
        try:
            child_list = HierarchyModel.find_by_child_of_code_single_user(username.employeeCode)
            child_list = [hier.json()['employee_code'] for hier in child_list]
        except Exception as e:
            app.logger.info(e)

        if len(child_list) == 0:
            final_list = [username.employeeCode]
        else:
            try:
                full_list = HierarchyModel.find_all_hierarchy()
                full_list = [{'child':hier.json()['employee_code'],'parent':hier.json()['child_of_code']} for hier in full_list]
            except Exception as e:
                app.logger.info(e)

            final_list = [username.employeeCode]
            for i in final_list:
                for j in full_list:
                    if i == j['parent']:
                        final_list.append(j['child'])


        for d in data:
            cacusSp = CacusModel.find_by_customerId(d['zid'],d['xcus']).json()
            
            sp_list = [cacusSp['cus_salesman'],cacusSp['cus_salesman1'],cacusSp['cus_salesman2'],cacusSp['cus_salesman3']]

            if len(set(sp_list).intersection(set(final_list))) == 0:
                app.logger.info('You are not allowed to place an order for this customer')
                return {'message':'You are not allowed to place an order for this customer'},400
            

        ztime = datetime.datetime.now()
        xdate = datetime.datetime.now().date()

        mainList = []
        for d in data:
            xroword = 1
            time_data = datetime.datetime.now().strftime("%d%S%f")
            for i in (d['order']):
                #update all static values
                i['xcus'] = d['xcus']

                try:
                    i['xlat'] = d['xlat']
                except:
                    i['xlat'] = 0

                try:
                    i['xlong'] = d['xlong']
                except:
                    i['xlong'] = 0

                approved_zid_list = VbusinessModel.find_all_business_list()

                if d['zid'] not in approved_zid_list:
                    app.logger.info('Error # 182 in Customer Resource, You have not been authorized to use this business')
                    return {'message': 'Error # 182 in Customer Resource, You have not been authorized to use this business'},400

                i['zid'] = d['zid']
                i['ztime'] = self.myconverter(ztime)
                i['zutime'] = self.myconverter(ztime)
                i['xdate'] = self.myconverter2(xdate)
                i['username'] = username.username
                i['xterminal'] = username.terminal
                i['xroword'] = xroword
                xroword = xroword + 1
                uuid_sl = str(uuid.uuid1())
                xsl = uuid_sl
                i['xsl'] = xsl
                invoicesl = time_data
                i['invoicesl'] = invoicesl
                i['invoiceno'] = str(username.terminal) + str(invoicesl)
                # i['xemp'] = [item['xemp'] for item in busIdempCodeList if item.get('zid','') == i['zid']][0]
                i['xemp'] = username.employeeCode
                i['xcusname'] = CacusModel.query.filter_by(zid=i['zid']).filter_by(xcus=i['xcus']).first().xorg
                i['xcusadd'] = CacusModel.query.filter_by(zid=i['zid']).filter_by(xcus=i['xcus']).first().xadd1

                i['xdesc'] = CaitemModel.query.filter_by(zid=i['zid']).filter_by(xitem=i['xitem']).first().xdesc

                xstdprice = CaitemModel.query.filter_by(zid=i['zid']).filter_by(xitem=i['xitem']).first().xstdprice
                xpricecat = CaitemModel.query.filter_by(zid=i['zid']).filter_by(xitem=i['xitem']).first().xpricecat


                try:
                    xqtycat = OpspprcModel.query.filter_by(zid=i['zid']).filter_by(xpricecat=xpricecat).first().xqty
                except Exception as e:
                    app.logger.info(e)
                    xqtycat = 0

                try:
                    xdisc = OpspprcModel.query.filter_by(zid=i['zid']).filter_by(xpricecat=xpricecat).first().xdisc
                except Exception as e:
                    app.logger.info(e)
                    xdisc = 0
                
                
                if i['xqty']>= xqtycat:
                    i['xprice'] = xstdprice - xdisc
                else:
                    i['xprice'] = xstdprice


                i['xlinetotal'] = i['xprice'] * i['xqty']
                i['xstatusord'] = "New"
                i['xordernum'] = ""
                mainList.append(i)

        #########################################
        
        confirmDetail = []

        # Loop through each order in mainList
        for orders in mainList:
            # Safely extract order details
            try:
                orderDetail = OpmobModel(
                    zid=orders.get('zid'),
                    ztime=orders.get('ztime'),
                    zutime=orders.get('zutime'),
                    invoiceno=orders.get('invoiceno'),
                    invoicesl=orders.get('invoicesl'),
                    username=orders.get('username'),
                    xemp=orders.get('xemp'),
                    xcus=orders.get('xcus'),
                    xcusname=orders.get('xcusname'),
                    xcusadd=orders.get('xcusadd'),
                    xitem=orders.get('xitem'),
                    xdesc=orders.get('xdesc'),
                    xqty=orders.get('xqty'),
                    xprice=orders.get('xprice'),
                    xstatusord=orders.get('xstatusord'),
                    xordernum=orders.get('xordernum'),
                    xroword=orders.get('xroword'),
                    xterminal=orders.get('xterminal'),
                    xdate=orders.get('xdate'),
                    xsl=orders.get('xsl'),
                    xlat=orders.get('xlat'),
                    xlong=orders.get('xlong'),
                    xlinetotal=orders.get('xlinetotal'),
                    xtra1=None,
                    xtra2=None,
                    xtra3=None,
                    xtra4=None,
                    xtra5=None
                )

                # Attempt to save to the database
                orderDetail.save_to_db()
                app.logger.info(f'Saved to DB by {orderDetail.username} for invoice no {orderDetail.invoiceno}')
                
                # Retrieve confirmed details
                internalDetail = OpmobModel.find_by_invoiceno(orderDetail.invoiceno)
                confirmDetail.extend([x.json() for x in internalDetail])
                
            except Exception as e:
                app.logger.error(f'Error processing order {orders}: {e}')  # Log the error with more context
                return {"message": "An error occurred inserting the customer"}, 400

        # Construct HTML body dictionary
        html_body_dict = {
            'customer': [i['customerName'] for i in confirmDetail],
            'invoice': [i['invoice_no'] for i in confirmDetail]
        }
        # print (html_body_dict)
        # dict2htmltable(html_body_dict)
        # send_mail(username.email)  # Safely access username and email
        # print ("send email successfully")

        try:
            dict2htmltable(html_body_dict)
            send_mail(username.email)  # Safely access username and email
            app.logger.info(f'sent email to {username.email} successfully')  # Log the email error with context
            return mainList, 200

        except Exception as e:
            app.logger.error(f'Error sending email: {e}')  # Log the email error with context
            return {"message": "Gmail has some problem. Check if Gmail is online or the user's Gmail is correct or XXXXXhmbr Gmail has enough space"}, 400

    def myconverter(self,o):
        if isinstance(o, datetime.datetime):
            return o.__str__()

    def myconverter2(self,o):
        if isinstance(o, datetime.date):
            return o.__str__()

class OpmobDelete(Resource):
    @jwt_required
    def delete(self,invoiceno):
        app.logger.info('OpmobDelete delete')
        claims = get_jwt_claims()
        if not claims['active']:
            app.logger.info('Error # 25 in Order Resource, You have not been activated by the admin')
            return {'message': 'Error # 25 in Order Resource, You have not been activated by the admin'},400

        username = UserModel.find_by_user(get_jwt_identity())

        try:
            child_list = HierarchyModel.find_by_child_of_code_single_user(username.employeeCode)
            child_list = [hier.json()['employee_code'] for hier in child_list]
        except Exception as e:
            app.logger.info(e)

        if len(child_list) == 0:
            final_list = [username.employeeCode]
        else:
            try:
                full_list = HierarchyModel.find_all_hierarchy()
                full_list = [{'child':hier.json()['employee_code'],'parent':hier.json()['child_of_code']} for hier in full_list]
            except Exception as e:
                app.logger.info(e)

            final_list = [username.employeeCode]
            for i in final_list:
                for j in full_list:
                    if i == j['parent']:
                        final_list.append(j['child'])

        terminal_list = UserModel.find_by_user_list(final_list)
        terminal_list = [term.json()['terminal'] for term in terminal_list]

        if OpmobModel.find_by_invoiceno(invoiceno)[0].xterminal not in terminal_list:
            app.logger.info('You are not allowed to delete this order')
            return {'message':'You are not allowed to delete this order'},400

        orderNum =[ordernum.xordernum for ordernum in OpmobModel.find_by_invoiceno(invoiceno)]

        if '' not in orderNum:
            app.logger.info('You cannot delete this Order as it has already been confirmed')
            return {'message':'You cannot delete this Order as it has already been confirmed'},400

        orderDetail = OpmobModel.find_by_invoiceno(invoiceno)
        for orders in orderDetail:
            orders.delete_from_db()
            
        ####################################
        # delete_key_value_pair_list = [('invoiceno', invoiceno)]
        ####################################
        # delete_from_client_db_with_custom_key_by_celery.delay(OpmobModel.__tablename__, delete_key_value_pair_list)
        app.logger.info('Your order has been deleted')
        return {'message':'Your order has been deleted'},200


class OpmobConfirmed(Resource):
    @jwt_required
    def get(self):
        username = UserModel.find_by_user(get_jwt_identity())
        app.logger.info(f'Opmobconfirmed get by {username.username}')
        claims = get_jwt_claims()
        if not claims['active']:
            app.logger.info('Error # 25 in Order Resource, You have not been activated by the admin')
            return {'message': 'Error # 25 in Order Resource, You have not been activated by the admin'},400

        # username = UserModel.find_by_user(get_jwt_identity())
        ztime = datetime.datetime.now().date()
        ztime_31 = ztime - datetime.timedelta(3)

        try:
            child_list = HierarchyModel.find_by_child_of_code_single_user(username.employeeCode)
            child_list = [hier.json()['employee_code'] for hier in child_list]
        except Exception as e:
            app.logger.info(e)

        if len(child_list) == 0:
            final_list = [username.employeeCode]
        else:
            try:
                full_list = HierarchyModel.find_all_hierarchy()
                full_list = [{'child':hier.json()['employee_code'],'parent':hier.json()['child_of_code']} for hier in full_list]
            except Exception as e:
                app.logger.info(e)

            final_list = [username.employeeCode]
            for i in final_list:
                for j in full_list:
                    if i == j['parent']:
                        final_list.append(j['child'])

        terminal_list = UserModel.find_by_user_list(final_list)
        terminal_list = [term.json()['terminal'] for term in terminal_list]


        try:
            confirmedOrders = OpmobModel.find_confirmed(terminal_list,ztime_31)
        except Exception as e:
            app.logger.info(e)
            return {f'message':'No orders created under your name {username.username}'},400

        reOrders = []
        invoice_no = ''

        for orders in confirmedOrders:
            if invoice_no != orders.json()['invoice_no']:
                newOrderDict = {}

                newOrderDict['businessId'] = orders.json()['businessId']
                newOrderDict['invoice_no'] = orders.json()['invoice_no']
                newOrderDict['customerCode'] = orders.json()['customerCode']
                newOrderDict['customerName'] = orders.json()['customerName']
                newOrderDict['orderDate'] = orders.json()['orderDate']
                newOrderDict['employeeCode'] = orders.json()['employeeCode']

                products = []
                for ordersProduct in OpmobModel.find_by_invoiceno(orders.json()['invoice_no']):
                    invoice_product = {
                                        'productCode':ordersProduct.json()['productCode'],
                                        'productName':ordersProduct.json()['productName'],
                                        'orderQty':ordersProduct.json()['orderQty'],
                                        'orderPrice':ordersProduct.json()['orderPrice'],
                                        'orderLineTotal':ordersProduct.json()['orderLineTotal'],
                                        'orderTotal':ordersProduct.json()['orderTotal']
                                    }
                    products.append(invoice_product)
                newOrderDict['products'] = products

                invoice_no = orders.json()['invoice_no']
                reOrders.append(newOrderDict)
            else:
                continue

        return reOrders,200

# class OpmobConfirmedCelery(Resource):
#     @jwt_required
#     def get(self):
#         claims = get_jwt_claims()
#         print(claims)
#         if not claims['active']:
#             return {'message': 'Error # 171 in Customer Resource, You have not been activated by the admin'},400

#         try:
#             #i think we need to import this
#             receive_from_client_db(OpmobModel.__tablename__, OpmobModel.__table__.c.keys())
#         except Exception as e:
#             print(e)

#         return 'customer data synced'

class OpmobConfirmedRowCount(Resource):
    @jwt_required
    def get(self):
        app.logger.info('OpmobConfirmedRowCount get')
        claims = get_jwt_claims()
        if not claims['active']:
            app.logger.info('Error # 25 in Order Resource, You have not been activated by the admin')
            return {'message': 'Error # 25 in Order Resource, You have not been activated by the admin'},400

        username = UserModel.find_by_user(get_jwt_identity())
        ztime = datetime.datetime.now().date()
        ztime_31 = ztime - datetime.timedelta(3)

        try:
            child_list = HierarchyModel.find_by_child_of_code_single_user(username.employeeCode)
            child_list = [hier.json()['employee_code'] for hier in child_list]
        except Exception as e:
            app.logger.info(e)

        if len(child_list) == 0:
            final_list = [username.employeeCode]
        else:
            try:
                full_list = HierarchyModel.find_all_hierarchy()
                full_list = [{'child':hier.json()['employee_code'],'parent':hier.json()['child_of_code']} for hier in full_list]
            except Exception as e:
                app.logger.info(e)

            final_list = [username.employeeCode]
            for i in final_list:
                for j in full_list:
                    if i == j['parent']:
                        final_list.append(j['child'])

        terminal_list = UserModel.find_by_user_list(final_list)
        terminal_list = [term.json()['terminal'] for term in terminal_list]

        try:
            
            confirmedOrders = OpmobModel.find_confirmed(terminal_list,ztime_31)
        except Exception as e:
            app.logger.info(e)
            return {'message':'No orders created under your name'},400

        invoice_no = ''
        count = 0
        for orders in confirmedOrders:
            if invoice_no != orders.json()['invoice_no']:
                count += 1
                invoice_no = orders.json()['invoice_no']
            else:
                continue
        
        return {'Number_of_confirmedOrders':count},200


class OpmobNotConfirmed(Resource):
    @jwt_required
    def get(self):
        username = UserModel.find_by_user(get_jwt_identity())
        app.logger.info(f'OpmobNotConfirmed get by {username.username}')
        claims = get_jwt_claims()
        if not claims['active']:
            app.logger.info('Error # 25 in Order Resource, You have not been activated by the admin')
            return {'message': 'Error # 25 in Order Resource, You have not been activated by the admin'},400

        # username = UserModel.find_by_user(get_jwt_identity())
        ztime = datetime.datetime.now().date()
        ztime_31 = ztime - datetime.timedelta(3)

        try:
            child_list = HierarchyModel.find_by_child_of_code_single_user(username.employeeCode)
            child_list = [hier.json()['employee_code'] for hier in child_list]
        except Exception as e:
            app.logger.info(e)

        if len(child_list) == 0:
            final_list = [username.employeeCode]
        else:
            try:
                full_list = HierarchyModel.find_all_hierarchy()
                full_list = [{'child':hier.json()['employee_code'],'parent':hier.json()['child_of_code']} for hier in full_list]
            except Exception as e:
                app.logger.info(e)

            final_list = [username.employeeCode]
            for i in final_list:
                for j in full_list:
                    if i == j['parent']:
                        final_list.append(j['child'])

        terminal_list = UserModel.find_by_user_list(final_list)
        terminal_list = [term.json()['terminal'] for term in terminal_list]

        try:
            notConfirmedOrders = OpmobModel.find_not_confirmed(terminal_list,ztime_31)
        except Exception as e:
            app.logger.info(e)
            return {'message':'No orders created under your name'},400

        reOrders = []
        invoice_no = ''

        for orders in notConfirmedOrders:
            if invoice_no != orders.json()['invoice_no']:
                newOrderDict = {}

                newOrderDict['businessId'] = orders.json()['businessId']
                newOrderDict['invoice_no'] = orders.json()['invoice_no']
                newOrderDict['customerCode'] = orders.json()['customerCode']
                newOrderDict['customerName'] = orders.json()['customerName']
                newOrderDict['orderDate'] = orders.json()['orderDate']
                newOrderDict['employeeCode'] = orders.json()['employeeCode']

                products = []
                orderTotal = 0
                for ordersProduct in OpmobModel.find_by_invoiceno(orders.json()['invoice_no']):
                    orderTotal += ordersProduct.json()['orderLineTotal']
                    invoice_product = {
                                        'productCode':ordersProduct.json()['productCode'],
                                        'productName':ordersProduct.json()['productName'],
                                        'orderQty':ordersProduct.json()['orderQty'],
                                        'orderPrice':ordersProduct.json()['orderPrice'],
                                        'orderLineTotal':ordersProduct.json()['orderLineTotal']
                                    }
                    products.append(invoice_product)
                newOrderDict['orderTotal'] = orderTotal
                newOrderDict['products'] = products

                invoice_no = orders.json()['invoice_no']
                reOrders.append(newOrderDict)
            else:
                continue

        return reOrders,200



class OpmobNotConfirmedRowCount(Resource):
    @jwt_required
    def get(self):
        app.logger.info('OpmobNotConfirmedRowCount get')
        claims = get_jwt_claims()
        if not claims['active']:
            app.logger.info('Error # 25 in Order Resource, You have not been activated by the admin')
            return {'message': 'Error # 25 in Order Resource, You have not been activated by the admin'},400

        username = UserModel.find_by_user(get_jwt_identity())
        ztime = datetime.datetime.now().date()
        ztime_31 = ztime - datetime.timedelta(3)

        try:
            child_list = HierarchyModel.find_by_child_of_code_single_user(username.employeeCode)
            child_list = [hier.json()['employee_code'] for hier in child_list]
        except Exception as e:
            app.logger.info(e)

        if len(child_list) == 0:
            final_list = [username.employeeCode]
        else:
            try:
                full_list = HierarchyModel.find_all_hierarchy()
                full_list = [{'child':hier.json()['employee_code'],'parent':hier.json()['child_of_code']} for hier in full_list]
            except Exception as e:
                app.logger.info(e)

            final_list = [username.employeeCode]
            for i in final_list:
                for j in full_list:
                    if i == j['parent']:
                        final_list.append(j['child'])

        terminal_list = UserModel.find_by_user_list(final_list)
        terminal_list = [term.json()['terminal'] for term in terminal_list]

        try:
            notConfirmedOrders = OpmobModel.find_not_confirmed(terminal_list,ztime_31)
        except Exception as e:
            app.logger.info(e)
            return {'message':'No orders created under your name'},400

        invoice_no = ''
        count = 0
        for orders in notConfirmedOrders:
            if invoice_no != orders.json()['invoice_no']:
                count += 1
                invoice_no = orders.json()['invoice_no']
            else:
                continue

        return {'Number_of_confirmedOrders':count},200


