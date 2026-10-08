"""
Market prices and price forecasts.

Everything comes from the trained model in ml/ (see price_model.py). No price API is called,
so the price page keeps working when data.gov.in is slow or unreachable.
"""

from datetime import date

from app.services import price_model
from app.services.price_model import PriceModelUnavailable

# Older name used by the routes and the WhatsApp bot: "the price source is not available"
MarketDataUnavailable = PriceModelUnavailable

# After this many days past the end of the model's data, say that the prices are old
STALE_AFTER_DAYS = 90


def _supported():
    """The crops that have a forecast, so the page can suggest them next to an error."""
    try:
        return [name.replace("_", " ") for name in price_model.supported_crops()]
    except PriceModelUnavailable:
        return []


# =========================================================
# MARKETS
# =========================================================

def search_markets(crop):
    """The Karnataka districts that have price data for the crop (newest data first)."""

    if not crop or not crop.strip():
        return []

    return price_model.markets_for(crop.strip())


# =========================================================
# PRICE PREDICTION
# =========================================================

def _old_data_note(week):
    age = (date.today() - week.date()).days

    if age <= STALE_AFTER_DAYS:
        return ""

    return f" Note: the model's price data ends on {week.strftime('%d/%m/%Y')}, so these prices are old."


def predict_price(crop: str, district: str = None, market: str = None):

    if not crop:
        return {"error": "Crop name is required"}

    crop = crop.strip()

    # Only a crop: list the markets to pick from
    if not district or not market:
        try:
            markets = search_markets(crop)
        except MarketDataUnavailable as e:
            return {"crop": crop, "error": str(e) + ". Please try again later."}

        if not markets:
            return {
                "crop": crop,
                "error": "No Karnataka markets found for this crop",
                "supported_crops": _supported()
            }

        return {"crop": crop, "markets": markets}

    district = district.strip()
    market = market.strip()

    try:
        code = price_model.resolve_crop(crop)

        if code is None:
            return {
                "crop": crop,
                "district": district,
                "market": market,
                "error": "No market price data found for this crop and market.",
                "supported_crops": _supported()
            }

        shipped = code in price_model.supported_crops()

        found = price_model.forecast(code, district) if shipped else price_model.latest(code, district)
    except MarketDataUnavailable as e:
        return {"crop": crop, "error": str(e) + ". Please try again later."}

    if found is None:
        return {
            "crop": crop,
            "district": district,
            "market": market,
            "error": "No market price data found for this crop and market."
        }

    latest_price, week, points = found
    latest_price = round(float(latest_price), 2)
    latest_date = week.strftime("%d/%m/%Y")

    base = {
        "crop": crop,
        "district": district,
        "market": market,

        # weekly model data, not today's mandi board
        "current_price_available": False,
        "current_price": None,
        "date": None,
        "min_price": None,
        "max_price": None,

        "latest_price": latest_price,
        "latest_price_date": latest_date,
        "price_message": (
            f"Weekly average price of the week of {latest_date}, from the AgriPulse price model data."
            + _old_data_note(week)
        ),

        "unit": "₹ per quintal",
    }

    # ----------------------------------------------------- no trained forecast for this crop
    if not shipped:
        return {
            **base,
            "predicted_price": None,
            "prediction_period": "Next 4 weeks",
            "historical_records": 0,
            "trend": "No forecast for this crop",
            "recommendation": (
                "A price forecast is not available for this crop yet. "
                "The typical prices of the coming months are shown instead."
            ),
            "seasonal_outlook": price_model.seasonal_outlook(code, district),
        }

    # ----------------------------------------------------- forecast
    predicted_price = points[-1]["price"]
    difference = predicted_price - latest_price

    if difference > latest_price * price_model.TREND_BAND:
        trend = "Rising"
        recommendation = "Prices may increase. Consider waiting before selling."

    elif difference < -latest_price * price_model.TREND_BAND:
        trend = "Falling"
        recommendation = "Prices may decrease. Consider selling soon."

    else:
        trend = "Stable"
        recommendation = "Prices appear relatively stable. Sell according to market conditions."

    return {
        **base,
        "predicted_price": predicted_price,
        "prediction_period": "Next 4 weeks",
        "historical_records": 60,
        "trend": trend,
        "recommendation": recommendation,
        "forecast": points,
        "best_time_to_sell": price_model.best_time_to_sell(points, latest_price),
        "model_metrics": price_model.model_info(code, latest_price),
        "features_used": [
            "recent weekly prices",
            "state-wide trend",
            "time of year",
        ],
    }
