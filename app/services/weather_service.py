import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("WEATHER_API_KEY")


def get_weather(city):
    url = (
        f"http://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={API_KEY}&units=metric"
    )

    if not API_KEY:
        return {"error": "Weather API key is not configured"}

    try:
        response = requests.get(url, timeout=15)
    except requests.RequestException:
        return {"error": "Weather service unavailable"}

    if response.status_code != 200:
        return {"error": "City not found"}

    data = response.json()

    temp = data["main"]["temp"]
    humidity = data["main"]["humidity"]
    condition = data["weather"][0]["description"]

    if "rain" in condition.lower():
        advice = "Avoid spraying pesticides today"
    elif temp > 35:
        advice = "Irrigate crops properly"
    else:
        advice = "Weather is suitable for farming activities"

    return {
        "city": city,
        "temperature": temp,
        "humidity": humidity,
        "condition": condition,
        # the untranslated group ("Rain", "Clouds"...): the app picks the weather picture from it
        "sky": data["weather"][0].get("main", ""),
        "advice": advice,
    }