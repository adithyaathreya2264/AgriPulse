from app.services.weather_service import get_weather
def execute(city):
    return get_weather(city)