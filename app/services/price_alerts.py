"""Smart price alerts: checked daily against the 4-week forecast."""

import asyncio
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from app.db.database import get_database, next_id

load_dotenv()

ALERT_KINDS = ("rise", "fall", "best_time")

# Do not notify the same alert more often than this
COOLDOWN_HOURS = 24


def now():
    return datetime.now(timezone.utc)


def create_alert(db, user_id, crop, district, market, kind="best_time",
                 threshold=5.0, whatsapp=True):
    """Create (or return the existing identical) active price alert."""

    existing = db.price_alerts.find_one({
        "user_id": user_id, "crop": crop, "district": district,
        "market": market, "kind": kind, "active": True
    })

    if existing:
        return existing

    alert = {
        "id": next_id("price_alerts"),
        "user_id": user_id,
        "crop": crop,
        "district": district,
        "market": market,
        "kind": kind,
        "threshold_percent": threshold,
        "channels": ["in_app", "whatsapp"] if whatsapp else ["in_app"],
        "active": True,
        "created_at": now().isoformat(timespec="seconds"),
        "last_triggered_at": None
    }

    db.price_alerts.insert_one(alert)

    return alert


def evaluate_alert(alert, result):
    """
    Decide whether an alert fires for a prediction result.
    Returns the message to send, or None.
    """

    forecast = result.get("forecast")
    current = result.get("current_price") or result.get("latest_price")

    if not forecast or not current:
        return None

    crop = alert["crop"]
    market = alert["market"]
    threshold = float(alert.get("threshold_percent", 5))

    if alert["kind"] == "rise":
        top = max(forecast, key=lambda point: point["price"])
        change = (top["price"] - current) / current * 100

        if change >= threshold:
            return (
                f"{crop} price at {market} may rise {change:.1f}% "
                f"to about Rs {top['price']:.0f}/quintal in {top['days']} days."
            )

    elif alert["kind"] == "fall":
        low = min(forecast, key=lambda point: point["price"])
        change = (current - low["price"]) / current * 100

        if change >= threshold:
            return (
                f"{crop} price at {market} may fall {change:.1f}% "
                f"to about Rs {low['price']:.0f}/quintal in {low['days']} days. "
                "Consider selling soon."
            )

    elif alert["kind"] == "best_time":
        advice = result.get("best_time_to_sell") or {}

        if advice.get("action") == "sell_now" or advice.get("days", 99) <= 7:
            return f"{crop} at {market}: {advice.get('message')}"

    return None


def send_whatsapp(phone, message):
    """Outbound WhatsApp through Twilio. Returns True when sent."""

    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    sender = os.getenv("TWILIO_WHATSAPP_FROM")

    if not (sid and token and sender and phone):
        return False

    digits = "".join(ch for ch in phone if ch.isdigit() or ch == "+")

    if not digits.startswith("+"):
        digits = "+91" + digits[-10:]

    try:
        from twilio.rest import Client

        Client(sid, token).messages.create(
            from_=sender if sender.startswith("whatsapp:") else f"whatsapp:{sender}",
            to=f"whatsapp:{digits}",
            body=message
        )

        return True

    except Exception as e:
        print("WhatsApp alert error:", e)
        return False


def notify(db, alert, message, whatsapp_sender=send_whatsapp):
    db.notifications.insert_one({
        "id": next_id("notifications"),
        "user_id": alert["user_id"],
        "alert_id": alert["id"],
        "message": message,
        "created_at": now().isoformat(timespec="seconds"),
        "read": False
    })

    if "whatsapp" in alert.get("channels", []):
        user = db.users.find_one({"id": alert["user_id"]})

        # Farmers who sent STOP on WhatsApp get no proactive messages
        if user:
            from app.whatsapp.state import can_send_proactive

            if can_send_proactive(db, "+91" + user["phone"]):
                whatsapp_sender(user["phone"], message)


def check_alerts(db=None, predictor=None, user_id=None, whatsapp_sender=send_whatsapp):
    """
    Run every active alert (or only one user's). Each crop+market is
    predicted once. Returns the number of notifications created.
    """

    db = db if db is not None else get_database()

    if predictor is None:
        from app.services.price_service import predict_price as predictor

    query = {"active": True}

    if user_id is not None:
        query["user_id"] = user_id

    alerts = list(db.price_alerts.find(query))

    results = {}
    fired = 0

    for alert in alerts:
        last = alert.get("last_triggered_at")

        if last and now() - datetime.fromisoformat(last) < timedelta(hours=COOLDOWN_HOURS):
            continue

        key = (alert["crop"], alert["district"], alert["market"])

        if key not in results:
            try:
                results[key] = predictor(*key)
            except Exception as e:
                print("Alert prediction error:", e)
                results[key] = {}

        message = evaluate_alert(alert, results[key])

        if message:
            notify(db, alert, message, whatsapp_sender)

            db.price_alerts.update_one(
                {"id": alert["id"]},
                {"$set": {"last_triggered_at": now().isoformat(timespec="seconds")}}
            )

            fired += 1

    return fired


async def price_alert_loop(interval_seconds=24 * 3600):
    """Background task started by the FastAPI lifespan."""

    # Let the server finish starting before the first (slow) check
    await asyncio.sleep(60)

    while True:
        try:
            fired = await asyncio.to_thread(check_alerts)

            if fired:
                print("Price alerts sent:", fired)

        except asyncio.CancelledError:
            raise

        except Exception as e:
            print("Price alert error:", e)

        await asyncio.sleep(interval_seconds)
