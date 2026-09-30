from app.services.weather_service import get_weather
from app.whatsapp.features.common import tidy_place
from app.whatsapp.natural import clean_place
from app.whatsapp.state import end_flow, set_state
from app.whatsapp.types import say


def weather_text(city):
    result = get_weather(city)

    if "error" in result:
        return result["error"]

    return (
        f"🌦 Weather in {result['city']}\n"
        f"Temperature: {result['temperature']}°C\n"
        f"Humidity: {result['humidity']}%\n"
        f"Condition: {result['condition']}\n"
        f"Advice: {result['advice']}"
    )


def start(ctx, city=""):
    """`weather <city>`; without a city the farmer's district is used."""

    city = tidy_place(clean_place(city)) or ctx.district

    if not city:
        set_state(ctx, "weather_city")

        return say("Which city or district? (for example: Mysuru)", static=True)

    end_flow(ctx)

    return say(weather_text(city))


def on_city(ctx, text):
    return start(ctx, text)
