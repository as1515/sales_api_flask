from flask import Flask, g
from flask_cors import CORS
from flask_restful import Api
from flask_jwt_extended import JWTManager #new
from flask_apscheduler import APScheduler
import time
import datetime
import sqlalchemy as db
import requests
import json
from waitress import serve

from blacklist import BLACKLIST
from resources.cacus import Cacus, CacusList, CacusRowCount, CacusAreaUpdate
from resources.caitem import Caitem, CaitemList, CaitemRowCount, CaitemProductCategory, CaitemProductCategoryAdd, CaitemProductCategoryDelete
from resources.opmob import Opmob,OpmobDelete, OpmobConfirmed, OpmobNotConfirmed, OpmobNotConfirmedRowCount, OpmobConfirmedRowCount
from resources.users import UserRegistration,UserLogout,UserLogin,TokenRefresh,AccessFreshToken,UpdateUser,UserStatusActive,UserStatusInactive, EmployeeCodeList,  UserDelete
#Hrmstlist
from resources.vbusiness import Vbusiness,VbusinessNonapproved, VbusinessRegular, VbusinessDelete
# from resources.zbusiness import ZbusinessList
from resources.hierarchy import Hierarchy,HierarchyDelete, HierarchyNonparent, HierarchyParent
from resources.location import LocationUpdate
from resources.logout import LoggedUserGet, LoggedUserDelete


# from resources.opcdt import OpcdtListTime
# from resources.opcrn import OpcrnListTime
# from resources.opdor import OpdorListTime
# from resources.opord import OpordListTime
# from resources.opodt import OpodtListTime
# from resources.opddt import OpddtListTime

from models.users import UserModel
from models.vbusiness import VbusinessModel
from resources.weather import WeatherCity
from models.weather import WeatherModel
import logging
#main app config
# app = factory.create_app(celery=app.celery)
app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}})

logging.getLogger('waitress')
logging.basicConfig(filename='access.log',level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s : %(message)s')



#SQL config
app.config['SQLALCHEMY_DATABASE_URI']='postgresql+psycopg2://XXXXX:XXXXX@localhost:5432/XXXXX'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.config['SQLALCHEMY_ECHO'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['SCHEDULER_API_ENABLED']=True
api = Api(app)

#JWT config
app.config['JWT_SECRET_KEY'] = 'XXXXXX'
app.config['JWT_SUPERUSER_SECRET_KEY'] = 'XXXXXX'
app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access','refresh']
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(days=7)
jwt = JWTManager(app) #not creating a /auth end point




@jwt.user_claims_loader
def add_claims_to_jwt(identity):
    if UserModel.find_by_user(identity).is_admin == 'is_admin':  # instead of hard-coding, we should read from a config file to get a list of admins instead
        return {'is_admin': True,'active':True,'is_superuser':False}
    elif UserModel.find_by_user(identity).is_admin == 'is_superuser':
        return {'is_superuser': True,'is_admin':True,'active':True}
    elif UserModel.find_by_user(identity).status == 'active':
        return {'active': True,'is_admin':False,'is_superuser':False}
    return {'is_admin': False,'is_superuser':False,'active':False}

@jwt.token_in_blacklist_loader
def check_if_token_in_blacklist(decrypted_token):
    return decrypted_token['jti'] in BLACKLIST

@app.before_request
def before_request():
   g.request_start_time = time.time()
   g.request_time = lambda: "%.5fs" % (time.time() - g.request_start_time)


#resources for super user function
api.add_resource(Vbusiness,'/validate_business')
api.add_resource(VbusinessDelete,'/delete_business/<int:business_Id>')
api.add_resource(VbusinessNonapproved,'/nonapprovedbusiness')
# api.add_resource(ZbusinessList,'/businessId')

#resources for admin function
api.add_resource(Hierarchy,'/hierarchy')
api.add_resource(HierarchyDelete,'/hierarchyDelete/<string:username>')
api.add_resource(HierarchyNonparent,'/hierarchynonparent')
api.add_resource(HierarchyParent,'/hierarchyparent')
api.add_resource(LoggedUserGet,'/loggedUserGet')
api.add_resource(LoggedUserDelete,'/loggedUserDelete/<string:username>/<int:businessId>')

#resources for location function
api.add_resource(LocationUpdate,'/location')

#resources for customer function
api.add_resource(Cacus,'/customer/<int:businessId>/<string:customerId>')
api.add_resource(CacusList,'/customers')
api.add_resource(CacusRowCount,'/customerowcount')
api.add_resource(CacusAreaUpdate,'/customerareaupdate')
# api.add_resource(CacusCelery,'/customers_sync')
 

#resources for product function
api.add_resource(Caitem,'/product/<int:businessId>/<string:productCode>')
api.add_resource(CaitemList,'/products')
api.add_resource(CaitemRowCount,'/itemrowcount')
api.add_resource(CaitemProductCategory,'/itemcategory')
api.add_resource(CaitemProductCategoryAdd,'/itemcategoryadd/<int:businessId>')
api.add_resource(CaitemProductCategoryDelete,'/itemcategorydelete/<int:businessId>/<string:approvedCategory>')
# api.add_resource(SpecialPrice,'/specialPrice')
# api.add_resource(CaitemCelery,'/products_sync')

#resources for mobile orders
api.add_resource(Opmob,'/order') #this uses request.json in order to accept lists
api.add_resource(OpmobDelete,'/orderdelete/<string:invoiceno>')
api.add_resource(OpmobConfirmed,'/orderconfirmed')
# api.add_resource(OpmobConfirmedCelery,'/orderconfirmed_sync')
api.add_resource(OpmobConfirmedRowCount,'/orderconfirmedrowcount')
api.add_resource(OpmobNotConfirmed, '/ordernotconfirmed')
api.add_resource(OpmobNotConfirmedRowCount,'/ordernotconfirmedrowcount')
# api.add_resource(OpmobDate,'/orderdate/<string:fromDate>/<string:toDate>')
# api.add_resource(OpmobCustomer,'/customerOrder/<int:zid>/<string:xcus>')

# api.add_resource(OpcdtListTime,'/opcdttime/<string:ztime>')
# api.add_resource(OpcrnListTime,'/opcrntime/<string:ztime>')
# api.add_resource(OpdorListTime,'/opdortime/<string:ztime>')
# api.add_resource(OpddtListTime,'/opddttime/<string:ztime>')
# api.add_resource(OpordListTime,'/opordtime/<string:ztime>')
# api.add_resource(OpodtListTime,'/opodttime/<string:ztime>')

#resources for user registration and login function
api.add_resource(UserRegistration,'/registration')
api.add_resource(UserLogin,'/login')
api.add_resource(UserLogout,'/logout')
api.add_resource(TokenRefresh,'/token/refresh')
api.add_resource(AccessFreshToken,'/token/fresh')
api.add_resource(UpdateUser,'/updateuser')
api.add_resource(EmployeeCodeList,'/employeeCode/<int:businessId>')
api.add_resource(VbusinessRegular,'/validate_business_regular')
api.add_resource(UserDelete, '/userdelete/<string:username>')
# api.add_resource(HrmstList,'/hr')

#user according to status
api.add_resource(UserStatusActive,'/userstatusactive')
api.add_resource(UserStatusInactive,'/userstatusinactive')

#weather data
api.add_resource(WeatherCity,'/weather/<string:city>')

from db import db
db.init_app(app)

@app.before_first_request
def create_tables():
    db.create_all()

if __name__ == '__main__':

    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()

    @scheduler.task('interval', id='do_job_1', seconds=3600, misfire_grace_time=900)
    def periodic_run_get_weather():
        app.logger.info('get weather app started')
        local_db = db.create_engine('postgresql://XXXXX:XXXXX@localhost:5432/da')
        connection = local_db.connect()
        query = "DELETE FROM weather WHERE country = 'BD'"
        try:
            connection.execute(query)
        except Exception as err:
            app.logger.info(err)

        api_key = "XXXXXX"
        location_list = ['Chittagong','Dhaka','Rajshahi','Sylhet','Mymensingh','Comilla','Barisal','Jessore','Brahmanbaria','Bogra','Rangpur','Dinajpur','Gazipur','Savar']
        country = 'BD'

        for i in location_list:
            try:
                weather = WeatherModel.find_by_country_city(i,country)
            except Exception as err:
                app.logger.info(err)
                weather = 0
            if weather:
                weather.delete_from_db()

        for i in location_list:
            url = "http://api.openweathermap.org/data/2.5/weather?q=%s,%s&APPID=%s" % (i, country, api_key)
            response = requests.get(url)
            data = json.loads(response.text)

            ztime = datetime.datetime.now()
            ztime = ztime.strftime('%m/%d/%YT%H:%M:%S')
            short_desc = data['weather'][0]['main']
            full_desc = data['weather'][0]['description']
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            pressure = data['main']['pressure']
            humidity = data['main']['humidity']
            name = data['name']
    
            query = "INSERT INTO weather (ztime,short_desc,full_desc,temp,feels_like,pressure,humidity,country,name) VALUES ('%s','%s','%s',%s,%s,%s,%s,'%s','%s')" % (ztime,short_desc,full_desc,temp,feels_like,pressure,humidity,country,name)
            connection.execute(query)
            app.logger.info('weather query connection completed')
        return {'message':'All weather data has been succesfully inserted into the database table'}

    serve(app, host='0.0.0.0',port=5000, threads=4)
    # app.run(port=5000, host='0.0.0.0', debug=True)