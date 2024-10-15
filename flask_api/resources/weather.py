from flask import request, current_app as app
from flask_restful import Resource
from flask_jwt_extended import (jwt_required, fresh_jwt_required,jwt_refresh_token_required,
                                get_jwt_claims,get_jwt_identity)
from models.weather import WeatherModel



class WeatherCity(Resource):
    @jwt_required
    def get(self,city):
        app.logger.info('Weathercity get')
        claims = get_jwt_claims()
        if not claims['active']:
            app.logger.info('Error # 25 in Location Resource, You have not been activated by the admin')
            return {'message': 'Error # 25 in Location Resource, You have not been activated by the admin'}
        
        if not city:
            app.logger.info('You have not set location in location settings please do that now to get the weather')
            return {'message': 'You have not set location in location settings please do that now to get the weather'}
        try:
            weathercity = WeatherModel.find_by_country_city(city,'BD')
        except Exception as err:
            app.logger.info(err)
            weathercity = WeatherModel.find_by_country_city('Dhaka','BD')

        return weathercity.json()
