"""
The daily morning message for farmers who sent DIGEST ON: the weather for
their district and a short farming tip.

Note for real (non-sandbox) WhatsApp numbers: a business may only message
someone first with a template that WhatsApp has approved. Sandbox testers
must have written to the bot within the last 24 hours.
"""

import asyncio
import os
from datetime import datetime, timedelta

from app.db.database import get_database
from app.services.weather_service import get_weather
from app.whatsapp import twilio_io
from app.whatsapp.localize import localize
from app.whatsapp.state import update_wa_user

DEFAULT_HOUR = 7


def digest_hour():
    try:
        return int(os.getenv("DIGEST_HOUR", DEFAULT_HOUR)) % 24
    except ValueError:
        return DEFAULT_HOUR


def tip_for(weather):
    """One practical line from the weather."""

    condition = weather["condition"].lower()

    if "rain" in condition or "storm" in condition or "drizzle" in condition:
        return "Avoid spraying pesticide or fertiliser today; rain washes it off."

    if weather["temperature"] > 35:
        return "It is very hot: irrigate in the early morning or evening and mulch the soil."

    if weather["humidity"] > 85:
        return "High humidity: check leaves for fungal spots and keep air moving between plants."

    return "Good day for field work. Check your crop for early signs of pests or disease."


def digest_text(district):
    weather = get_weather(district)

    if "error" in weather:
        return None

    return (
        f"☀️ Good morning! Weather in {weather['city']}: "
        f"{weather['temperature']}°C, {weather['condition']}, humidity {weather['humidity']}%.\n"
        f"💡 {tip_for(weather)}\n\n"
        "Send MENU for prices, disease check and more. Send DIGEST OFF to stop these messages."
    )


def send_digests(db=None, today=None, sender=twilio_io.send_messages):
    """
    Send today's message to everybody who wants it (once each per day).
    Returns how many were sent.
    """

    db = db if db is not None else get_database()
    today = (today or datetime.now().date()).isoformat()

    sent = 0
    weather_cache = {}

    for user in db.whatsapp_users.find({"digest": True, "subscribed": {"$ne": False}}):
        if user.get("last_digest_date") == today or not user.get("digest_district"):
            continue

        district = user["digest_district"]

        if district not in weather_cache:
            weather_cache[district] = digest_text(district)

        text = weather_cache[district]

        if not text:
            continue

        message = localize(db, [text], user.get("lang") or "en")

        if sender(user["phone"], message):
            update_wa_user(db, user["phone"], last_digest_date=today)
            sent += 1

    return sent


def seconds_until_next_run(now=None, hour=None):
    now = now or datetime.now()
    hour = digest_hour() if hour is None else hour

    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)

    if target <= now:
        target += timedelta(days=1)

    return (target - now).total_seconds()


async def digest_loop():
    """Background task started by the FastAPI lifespan."""

    while True:
        await asyncio.sleep(seconds_until_next_run())

        try:
            sent = await asyncio.to_thread(send_digests)

            if sent:
                print("Morning digests sent:", sent)

        except asyncio.CancelledError:
            raise

        except Exception as e:
            print("Digest error:", e)
