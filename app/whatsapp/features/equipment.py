from app.services.geo import bounding_box, within_radius
from app.whatsapp.features.common import money
from app.whatsapp.state import end_flow, set_state
from app.whatsapp.types import say

RADIUS_KM = 10
MAX_RESULTS = 5


def start(ctx):
    set_state(ctx, "location")

    return say(
        "📍 Share your location so I can find equipment near you:\n"
        "tap the 📎 (attach) button → Location → Send your current location.",
        static=True
    )


def nearby(ctx, latitude, longitude):
    """Available equipment within 10 km of the shared location."""

    end_flow(ctx)

    min_lat, max_lat, min_lng, max_lng = bounding_box(latitude, longitude, RADIUS_KM)

    items = list(ctx.db.equipment.find({
        "availability": "Available",
        "location_geo.lat": {"$gte": min_lat, "$lte": max_lat},
        "location_geo.lng": {"$gte": min_lng, "$lte": max_lng},
    }))

    results = within_radius(items, latitude, longitude, RADIUS_KM)[:MAX_RESULTS]

    if not results:
        return say(
            f"I could not find equipment within {RADIUS_KM} km of you yet. "
            "Owners add their equipment in the AgriPulse app, so more will appear over time."
        )

    lines = [f"🚜 Equipment within {RADIUS_KM} km:"]

    for item in results:
        price = f"{money(item['price_per_day'])}/day"

        if item.get("price_per_hour"):
            price += f" ({money(item['price_per_hour'])}/hour)"

        live = " 🟢 live" if _is_live(item) else ""

        lines.append(
            f"\n• {item['equipment_name']} — {price} · {item['distance_km']} km{live}\n"
            f"  Owner: {item['owner_name']} · 📞 {item['contact_number']}"
        )

    lines.append("\nCall the owner to book, or book and pay in the AgriPulse app.")

    return say("\n".join(lines))


def _is_live(item):
    from app.routes.equipment_routes import add_live_flag

    return add_live_flag(dict(item))["location_live"]
