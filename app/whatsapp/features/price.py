import re

from app.services.price_alerts import create_alert
from app.services.price_service import MarketDataUnavailable, predict_price, search_markets
from app.whatsapp.features.common import as_number, money, need_account, tidy_place
from app.whatsapp.natural import clean_place
from app.whatsapp.state import end_flow, set_state
from app.whatsapp.types import Outcome, say

MAX_MARKETS = 5

# "price of tomato", "tomato price", "price for tomato in kolar" ...
FILLER = re.compile(r"\b(?:of|for|the|today|now|rate|rates|price|prices|mandi|in)\b", re.I)


def parse_args(arg):
    """"tomato" or "tomato, Kolar, Kolar" -> (crop, district, market)"""

    arg = (arg or "").strip()

    if "," in arg:
        parts = [part.strip() for part in arg.split(",")]
        crop = parts[0]
        district = parts[1] if len(parts) > 1 else None
        market = parts[2] if len(parts) > 2 else None

        # "tomato, Kolar": the market usually has the district's name
        if district and not market:
            market = district

        return _crop(crop), tidy_place(district), tidy_place(market)

    # "tomato in Kolar" / "tomato at Kolar market"
    match = re.fullmatch(r"(.+?)\s+(?:in|at)\s+(.+)", arg, re.IGNORECASE)

    if match:
        place = tidy_place(clean_place(match.group(2)))

        if place:
            return _crop(match.group(1)), place, place

    return _crop(arg), None, None


def _crop(text):
    return " ".join(FILLER.sub(" ", text).split()).lower()


# ------------------------------------------------------------------
# Start
# ------------------------------------------------------------------

def start(ctx, arg=""):
    crop, district, market = parse_args(arg)

    if not crop:
        set_state(ctx, "price_crop")

        return say("Which crop? (for example: rice, wheat, maize, cotton, groundnut)", static=True)

    if district and market:
        return forecast(ctx, crop, district, market)

    return list_markets(ctx, crop)


def on_crop(ctx, text):
    return start(ctx, text)


# ------------------------------------------------------------------
# Markets
# ------------------------------------------------------------------

def list_markets(ctx, crop):
    def work():
        try:
            markets = search_markets(crop)[:MAX_MARKETS]
        except MarketDataUnavailable:
            end_flow(ctx)

            return [
                "📡 The government market price service is not responding right now. "
                "Please try again in a little while."
            ]

        if not markets:
            end_flow(ctx)

            return [f"I found no Karnataka markets for '{crop}'. Check the spelling, or try another crop."]

        options = [{"district": m["district"], "market": m["market"]} for m in markets]

        lines = [f"🌾 Markets for {crop.title()}:"]

        for number, market in enumerate(markets, start=1):
            price = market.get("current_price") or market.get("latest_price")
            lines.append(f"{number}. {market['market']} ({market['district']}) — {money(price)}/quintal")

        lines.append("\nReply with a number to see the price forecast.")

        set_state(ctx, "price_choose", crop=crop, options=options)

        return ["\n".join(lines)]

    return Outcome(ack=f"🔎 Looking up {crop} prices…", deferred=work)


def on_choice(ctx, text):
    options = ctx.data.get("options", [])
    number = as_number(text)

    if number is None or not 1 <= number <= len(options):
        return say(f"Please reply with a number from 1 to {len(options)}, or MENU.", static=False)

    chosen = options[number - 1]

    return forecast(ctx, ctx.data["crop"], chosen["district"], chosen["market"])


# ------------------------------------------------------------------
# Forecast
# ------------------------------------------------------------------

def forecast_text(result):
    lines = [f"📈 {result['crop'].title()} — {result['market']}, {result['district']}"]

    if result.get("current_price") is not None:
        lines.append(f"Today: {money(result['current_price'])}/quintal")
    elif result.get("latest_price") is not None:
        lines.append(f"Latest: {money(result['latest_price'])}/quintal ({result['latest_price_date']})")

    points = result.get("forecast")

    if points:
        lines.append(
            "Forecast: " + " · ".join(f"+{p['days']}d {money(p['price'])}" for p in points)
        )

        advice = result.get("best_time_to_sell") or {}

        if advice.get("message"):
            lines.append(f"⏰ {advice['message']}")

    elif result.get("predicted_price") is not None:
        lines.append(f"Expected ({result['prediction_period']}): {money(result['predicted_price'])}/quintal")

    lines.append(f"Trend: {result.get('trend', '-')}. {result.get('recommendation', '')}".strip())

    return "\n".join(lines)


def forecast(ctx, crop, district, market):
    def work():
        result = predict_price(crop, district, market)

        if "error" in result:
            end_flow(ctx)

            return [result["error"]]

        set_state(ctx, "price_done", crop=result["crop"], district=district, market=market)

        return [
            forecast_text(result)
            + "\n\nReply ALERT to get price alerts for this market, or MENU."
        ]

    return Outcome(ack=f"🔎 Checking the {crop} forecast for {market}…", deferred=work)


# ------------------------------------------------------------------
# Alerts
# ------------------------------------------------------------------

def alert_from_context(ctx):
    """"ALERT" right after a forecast: alert for that crop and market."""

    data = ctx.data

    if ctx.state != "price_done" or not data.get("crop"):
        return say(
            "To set an alert, first look up a price (for example: price maize), "
            "or send: alert maize, Mandya, Mandya",
            static=True
        )

    return create(ctx, data["crop"], data["district"], data["market"])


def create(ctx, crop, district, market):
    if not ctx.account:
        return need_account()

    create_alert(ctx.db, ctx.account["id"], crop, district, market, "best_time")

    end_flow(ctx)

    return say(
        f"🔔 Done! I will message you when it is a good time to sell {crop.title()} "
        f"at {market}. Send ALERTS to see or remove your alerts."
    )
