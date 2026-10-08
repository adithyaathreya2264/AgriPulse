"""Features that need an AgriPulse account: alerts, bookings, daily digest."""

import re

from app.whatsapp.features.common import as_number, need_account
from app.whatsapp.state import end_flow, set_state, update_wa_user
from app.whatsapp.types import say

DIGEST_HOUR = 7


# ------------------------------------------------------------------
# Price alerts
# ------------------------------------------------------------------

KIND_TEXT = {
    "best_time": "best time to sell",
    "rise": "price rises",
    "fall": "price falls",
}


def _alerts(ctx):
    return list(
        ctx.db.price_alerts.find({"user_id": ctx.account["id"], "active": True}).sort("id", -1)
    )


def alerts_list(ctx):
    if not ctx.account:
        return need_account()

    alerts = _alerts(ctx)

    if not alerts:
        return say(
            "You have no price alerts. Look up a price (for example: price maize) "
            "and reply ALERT to get one."
        )

    lines = ["🔔 Your price alerts:"]

    for number, alert in enumerate(alerts, start=1):
        lines.append(
            f"{number}. {alert['crop'].title()} at {alert['market']} — "
            f"{KIND_TEXT.get(alert['kind'], alert['kind'])}"
        )

    lines.append("\nTo remove one, send: stop alert 1")

    return say("\n".join(lines))


def alert_remove(ctx, arg):
    if not ctx.account:
        return need_account()

    number = as_number(arg)
    alerts = _alerts(ctx)

    if number is None or not 1 <= number <= len(alerts):
        return say("Send ALERTS to see the numbers, then: stop alert 1")

    alert = alerts[number - 1]

    ctx.db.price_alerts.update_one({"id": alert["id"]}, {"$set": {"active": False}})

    return say(f"Removed the alert for {alert['crop'].title()} at {alert['market']}.")


# ------------------------------------------------------------------
# Bookings
# ------------------------------------------------------------------

STATUS_ICON = {
    "Pending": "⏳", "Confirmed": "✅", "Active": "🟢",
    "Completed": "🏁", "Expired": "⌛", "Refund Required": "⚠️",
}


def bookings(ctx):
    if not ctx.account:
        return need_account()

    user_id = ctx.account["id"]

    rentals = list(
        ctx.db.rentals.find({"$or": [{"renter_id": user_id}, {"owner_id": user_id}]})
        .sort("id", -1)
        .limit(5)
    )

    if not rentals:
        return say("You have no bookings yet. Send EQUIPMENT to find equipment near you.")

    lines = ["📅 Your latest bookings:"]

    for rental in rentals:
        equipment = ctx.db.equipment.find_one({"id": rental["equipment_id"]}) or {}
        role = "you rent out" if rental.get("owner_id") == user_id else "you rent"
        start, end = rental["start_at"][:16].replace("T", " "), rental["end_at"][:16].replace("T", " ")

        lines.append(
            f"\n{STATUS_ICON.get(rental['status'], '•')} #{rental['id']} "
            f"{equipment.get('equipment_name', 'Equipment')} ({role})\n"
            f"  {start} → {end}\n"
            f"  ₹{rental['total_amount']:,.0f} · {rental['status']}"
            + (" · paid" if rental.get("payment_status") == "Paid" else "")
        )

    return say("\n".join(lines))


# ------------------------------------------------------------------
# Daily digest
# ------------------------------------------------------------------

def digest(ctx, arg=""):
    arg = (arg or "").strip().lower()

    if arg in ("off", "stop", "no"):
        update_wa_user(ctx.db, ctx.phone, digest=False)
        end_flow(ctx)

        return say("Okay, no more morning messages. Send DIGEST ON to turn them back on.")

    district = ctx.district

    if not district:
        set_state(ctx, "digest_district")

        return say("Which district should the morning weather be for? (for example: Mysuru)", static=True)

    return _enable_digest(ctx, district)


def on_digest_district(ctx, text):
    district = " ".join(re.sub(r"[^\w\s.-]", "", text, flags=re.UNICODE).split())

    if len(district) < 2:
        return say("Please send the name of your district.", static=True)

    return _enable_digest(ctx, district.title())


def _enable_digest(ctx, district):
    update_wa_user(ctx.db, ctx.phone, digest=True, digest_district=district, subscribed=True)
    end_flow(ctx)

    return say(
        f"☀️ Done! Every morning at {DIGEST_HOUR}:00 I will send the weather and a farming tip "
        f"for {district}. Send DIGEST OFF to stop."
    )
