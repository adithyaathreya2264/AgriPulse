import requests

API_KEY='7f0d4ec8c576cc741c6e16f4000e8a25'


def get_weather(city):
    url = (
        f"http://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={API_KEY}&units=metric"
    )

    response = requests.get(url)

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
        "advice": advice,
    }