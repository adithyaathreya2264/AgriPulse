import os
import json
import subprocess
from urllib.parse import urlencode

from app.services.lazy_import import lazy

pd = lazy("pandas")
import numpy as np
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("AGMARKNET_API_KEY")

# curl.exe on Windows, plain curl on Linux (Render / Docker)
CURL = "curl.exe" if os.name == "nt" else "curl"


CURRENT_API = (
    "https://api.data.gov.in/resource/"
    "9ef84268-d588-465a-a308-a864a43d0070"
)

HISTORY_API = (
    "https://api.data.gov.in/resource/"
    "35985678-0d79-46b4-9ed6-6f13308a1d24"
)


# =========================================================
# API CALL
# =========================================================

class MarketDataUnavailable(RuntimeError):
    """The government price service did not answer (network / service down)."""


def _hide_key(text):
    """Logs must never contain the API key."""
    return text.replace(API_KEY, "<api-key>") if API_KEY else text


def call_api(url, params):

    query = urlencode(params)

    full_url = f"{url}?{query}"

    print("\n========== MARKET API ==========")
    print("URL:", _hide_key(full_url))

    try:

        result = subprocess.run(
            [
                CURL,
                "-sS",
                "--max-time",
                "60",
                full_url
            ],
            capture_output=True,
            text=True,
            timeout=70
        )

    except subprocess.TimeoutExpired:

        print("API request timed out")
        return None

    if result.returncode != 0:

        print("Curl error:", _hide_key(result.stderr.strip()))
        return None

    print("Return code:", result.returncode)
    print("Response length:", len(result.stdout))

    try:

        data = json.loads(result.stdout)

    except json.JSONDecodeError:

        print("Invalid JSON response")
        print(_hide_key(result.stdout[:500]))

        return None

    print("API status:", data.get("status"))
    print("Total:", data.get("total"))
    print("Records:", len(data.get("records", [])))

    return data


# =========================================================
# CURRENT MARKET PRICE
# =========================================================

def get_current_price(crop, district, market):

    if not crop or not district or not market:
        return None

    crop = crop.strip()
    district = district.strip()
    market = market.strip()

    params = {
        "api-key": API_KEY,
        "format": "json",
        "offset": 0,
        "limit": 100,

        "filters[state.keyword]": "Karnataka",
        "filters[commodity]": crop,
        "filters[district]": district,
        "filters[market]": market
    }

    data = call_api(
        CURRENT_API,
        params
    )

    if not data:
        return None

    records = data.get(
        "records",
        []
    )

    if not records:
        return None

    # Find exact crop + district + market
    matching_records = []

    for item in records:

        item_crop = str(
            item.get("commodity", "")
        ).strip().lower()

        item_district = str(
            item.get("district", "")
        ).strip().lower()

        item_market = str(
            item.get("market", "")
        ).strip().lower()

        if (
            item_crop == crop.lower()
            and item_district == district.lower()
            and item_market == market.lower()
        ):

            matching_records.append(item)

    if not matching_records:
        return None

    prices = []

    for item in matching_records:

        try:

            price = float(
                item.get("modal_price")
            )

            prices.append(price)

        except (
            ValueError,
            TypeError
        ):

            continue

    if not prices:
        return None

    min_prices = []
    max_prices = []

    for item in matching_records:

        try:
            min_prices.append(
                float(item.get("min_price"))
            )
        except (
            ValueError,
            TypeError
        ):
            pass

        try:
            max_prices.append(
                float(item.get("max_price"))
            )
        except (
            ValueError,
            TypeError
        ):
            pass

    return {
        "market": matching_records[0].get("market"),
        "date": matching_records[0].get("arrival_date"),

        "min_price": (
            min(min_prices)
            if min_prices
            else None
        ),

        "max_price": (
            max(max_prices)
            if max_prices
            else None
        ),

        "current_price": round(
            sum(prices) / len(prices),
            2
        )
    }


# =========================================================
# LATEST HISTORICAL PRICE
# =========================================================

def get_historical_data(
    crop,
    district,
    market
):

    if not crop or not district or not market:
        return None

    crop = crop.strip()
    district = district.strip()
    market = market.strip()

    # First request only gets total number of records
    first_params = {

        "api-key": API_KEY,
        "format": "json",
        "offset": 0,
        "limit": 1,

        "filters[State]": "Karnataka",
        "filters[District]": district,
        "filters[Commodity]": crop,
        "filters[Market]": market
    }

    first_data = call_api(
        HISTORY_API,
        first_params
    )

    if not first_data:
        return None

    total = int(
        first_data.get(
            "total",
            0
        )
    )

    if total == 0:
        return None

    # Get the latest 100 records
    offset = max(
        total - 100,
        0
    )

    params = {

        "api-key": API_KEY,
        "format": "json",

        "offset": offset,
        "limit": 100,

        "filters[State]": "Karnataka",
        "filters[District]": district,
        "filters[Commodity]": crop,
        "filters[Market]": market
    }

    data = call_api(
        HISTORY_API,
        params
    )

    if not data:
        return None

    records = data.get(
        "records",
        []
    )

    if not records:
        return None

    rows = []

    for item in records:

        try:

            date = pd.to_datetime(
                item.get("Arrival_Date"),
                dayfirst=True
            )

            price = float(
                item.get("Modal_Price")
            )

            rows.append({
                "date": date,
                "price": price
            })

        except (
            ValueError,
            TypeError,
            KeyError
        ):

            continue

    return rows


# =========================================================
# LATEST AVAILABLE PRICE ONLY
# =========================================================

def get_latest_historical_price(
    crop,
    district,
    market
):

    history = get_historical_data(
        crop,
        district,
        market
    )

    if not history:
        return None

    df = pd.DataFrame(history)

    if df.empty:
        return None

    df = df.sort_values(
        "date"
    )

    latest = df.iloc[-1]

    return {
        "latest_price": round(
            float(latest["price"]),
            2
        ),

        "latest_price_date": (
            latest["date"].strftime(
                "%d/%m/%Y"
            )
        )
    }


# =========================================================
# SEARCH MARKETS
#
# Current API:
#   Shows markets with today's price
#
# Historical API:
#   Shows latest available markets
#
# Only a few API requests are made.
# =========================================================

def search_markets(crop):

    if not crop:
        return []

    crop = crop.strip()

    current_markets = []
    historical_markets = []

    # Used to prevent duplicate markets
    seen = set()

    # =====================================================
    # 1. CURRENT MARKETS
    # =====================================================

    current_params = {

        "api-key": API_KEY,
        "format": "json",

        "offset": 0,
        "limit": 100,

        "filters[state.keyword]": "Karnataka"
    }

    current_data = call_api(
        CURRENT_API,
        current_params
    )

    if current_data:

        records = current_data.get(
            "records",
            []
        )

        for item in records:

            commodity = str(
                item.get("commodity", "")
            ).strip().lower()

            if commodity != crop.lower():
                continue

            district = item.get(
                "district"
            )

            market = item.get(
                "market"
            )

            if not district or not market:
                continue

            key = (
                district.strip().lower(),
                market.strip().lower()
            )

            if key in seen:
                continue

            seen.add(key)

            current_markets.append({

                "district": district,

                "market": market,

                "current_price_available": True,

                "current_price": item.get(
                    "modal_price"
                ),

                "date": item.get(
                    "arrival_date"
                )
            })

    # =====================================================
    # 2. FIND TOTAL HISTORICAL RECORDS
    # =====================================================

    first_params = {

        "api-key": API_KEY,
        "format": "json",

        "offset": 0,
        "limit": 1,

        "filters[State]": "Karnataka",
        "filters[Commodity]": crop
    }

    first_data = call_api(
        HISTORY_API,
        first_params
    )

    # Both services silent: the price service is down, not "no markets"
    if current_data is None and first_data is None:
        raise MarketDataUnavailable(
            "The government market price service is not responding"
        )

    if first_data:

        total = int(
            first_data.get(
                "total",
                0
            )
        )

        print(
            "Historical total:",
            total
        )

        if total > 0:

            # =================================================
            # Get only the last 100 records.
            # This avoids scanning 100,000+ records.
            # =================================================

            offset = max(
                total - 100,
                0
            )

            history_params = {

                "api-key": API_KEY,
                "format": "json",

                "offset": offset,
                "limit": 100,

                "filters[State]": "Karnataka",
                "filters[Commodity]": crop
            }

            history_data = call_api(
                HISTORY_API,
                history_params
            )

            if history_data:

                records = history_data.get(
                    "records",
                    []
                )

                for item in records:

                    district = item.get(
                        "District"
                    )

                    market = item.get(
                        "Market"
                    )

                    if not district or not market:
                        continue

                    key = (
                        district.strip().lower(),
                        market.strip().lower()
                    )

                    # Current market already shown above
                    if key in seen:
                        continue

                    seen.add(key)

                    historical_markets.append({

                        "district": district,

                        "market": market,

                        "current_price_available": False,

                        "latest_price": item.get(
                            "Modal_Price"
                        ),

                        "latest_price_date": item.get(
                            "Arrival_Date"
                        )
                    })

    # =====================================================
    # 3. CURRENT MARKETS FIRST
    #    HISTORICAL MARKETS SECOND
    # =====================================================

    return (
        current_markets
        +
        historical_markets
    )


# =========================================================
# PRICE PREDICTION
# =========================================================

def predict_price(
    crop: str,
    district: str = None,
    market: str = None
):

    # -----------------------------------------------------
    # Validate input
    # -----------------------------------------------------

    if not crop:
        return {
            "error": "Crop name is required"
        }

    crop = crop.strip()

    if not district or not market:

        try:
            markets = search_markets(
                crop
            )
        except MarketDataUnavailable as e:
            return {
                "crop": crop,
                "error": str(e) + ". Please try again later."
            }

        if not markets:

            return {
                "crop": crop,
                "error": (
                    "No Karnataka markets found "
                    "for this crop"
                )
            }

        return {
            "crop": crop,
            "markets": markets
        }

    district = district.strip()
    market = market.strip()

    # -----------------------------------------------------
    # Get today's current price
    # -----------------------------------------------------

    current = get_current_price(
        crop,
        district,
        market
    )

    # -----------------------------------------------------
    # Get historical data
    # -----------------------------------------------------

    # 5+ years of history, cached in MongoDB (refreshed daily)
    from app.services.price_history_service import get_history

    try:
        history = get_history(crop, district, market)
    except Exception as e:
        print("Price history error:", e)
        history = get_historical_data(crop, district, market)

    # -----------------------------------------------------
    # If no historical data
    # -----------------------------------------------------

    if not history:

        if current:

            return {

                "crop": crop,
                "district": district,
                "market": market,

                "current_price_available": True,

                "current_price": current[
                    "current_price"
                ],

                "date": current[
                    "date"
                ],

                "min_price": current[
                    "min_price"
                ],

                "max_price": current[
                    "max_price"
                ],

                "latest_price": None,

                "latest_price_date": None,

                "price_message": (
                    "Today's current market "
                    "price is available."
                ),

                "predicted_price": None,

                "prediction_period": (
                    "Next 7 days"
                ),

                "unit": "₹ per quintal",

                "historical_records": 0,

                "trend": (
                    "Insufficient historical data"
                ),

                "recommendation": (
                    "Not enough historical data "
                    "for prediction."
                )
            }

        return {
            "crop": crop,
            "district": district,
            "market": market,

            "error": (
                "No market price data found "
                "for this crop and market."
            )
        }

    # -----------------------------------------------------
    # Prepare historical data
    # -----------------------------------------------------

    df = pd.DataFrame(
        history
    )

    df = df.sort_values(
        "date"
    )

    # Average prices on same date
    df = (
        df.groupby("date")["price"]
        .mean()
        .reset_index()
    )

    # -----------------------------------------------------
    # Latest historical price
    # -----------------------------------------------------

    latest_row = df.iloc[-1]

    latest_price = round(
        float(latest_row["price"]),
        2
    )

    latest_price_date = (
        latest_row["date"].strftime(
            "%d/%m/%Y"
        )
    )

    # -----------------------------------------------------
    # Current price available?
    # -----------------------------------------------------

    if current:

        current_price_available = True

        current_price = current[
            "current_price"
        ]

        current_date = current[
            "date"
        ]

        min_price = current[
            "min_price"
        ]

        max_price = current[
            "max_price"
        ]

        price_message = (
            "Today's current market "
            "price is available."
        )

    else:

        current_price_available = False

        current_price = None

        current_date = None

        min_price = None

        max_price = None

        price_message = (
            "Today's current market price "
            "is not available. Showing the "
            "latest available historical price "
            f"of ₹{latest_price} per quintal "
            f"from {latest_price_date}."
        )

    # -----------------------------------------------------
    # Need at least 5 historical records
    # -----------------------------------------------------

    if len(df) < 5:

        return {

            "crop": crop,
            "district": district,
            "market": market,

            "current_price_available":
                current_price_available,

            "current_price":
                current_price,

            "date":
                current_date,

            "min_price":
                min_price,

            "max_price":
                max_price,

            "latest_price":
                latest_price,

            "latest_price_date":
                latest_price_date,

            "price_message":
                price_message,

            "predicted_price":
                None,

            "prediction_period":
                "Next 7 days",

            "unit":
                "₹ per quintal",

            "historical_records":
                len(df),

            "trend":
                "Insufficient historical data",

            "recommendation":
                "Not enough historical data "
                "for prediction."
        }

    # -----------------------------------------------------
    # Forecast the next 4 weeks
    # -----------------------------------------------------

    from app.services.price_forecast import (
        best_time_to_sell,
        forecast_prices
    )
    from app.services.weather_history_service import get_weather_history

    weather = None

    try:
        weather = get_weather_history(
            district,
            df["date"].min(),
            df["date"].max()
        )
    except Exception as e:
        print("Weather history error:", e)

    forecast, model_metrics, features_used = forecast_prices(
        df[["date", "price"]].to_dict("records"),
        weather
    )

    comparison_price = (
        current_price
        if current_price is not None
        else latest_price
    )

    predicted_price = forecast[-1]["price"]

    difference = predicted_price - comparison_price

    # -----------------------------------------------------
    # Trend
    # -----------------------------------------------------

    if difference > comparison_price * 0.03:

        trend = "Rising"

        recommendation = (
            "Prices may increase. "
            "Consider waiting before selling."
        )

    elif difference < -comparison_price * 0.03:

        trend = "Falling"

        recommendation = (
            "Prices may decrease. "
            "Consider selling soon."
        )

    else:

        trend = "Stable"

        recommendation = (
            "Prices appear relatively stable. "
            "Sell according to market conditions."
        )

    sell_advice = best_time_to_sell(forecast, comparison_price)

    # -----------------------------------------------------
    # Final response
    # -----------------------------------------------------

    return {

        "crop": crop,

        "district": district,

        "market": market,

        "current_price_available":
            current_price_available,

        "current_price":
            current_price,

        "date":
            current_date,

        "min_price":
            min_price,

        "max_price":
            max_price,

        "latest_price":
            latest_price,

        "latest_price_date":
            latest_price_date,

        "price_message":
            price_message,

        "predicted_price":
            predicted_price,

        "prediction_period":
            "Next 4 weeks",

        "unit":
            "₹ per quintal",

        "historical_records":
            len(df),

        "trend":
            trend,

        "recommendation":
            recommendation,

        "forecast":
            forecast,

        "best_time_to_sell":
            sell_advice,

        "model_metrics":
            model_metrics,

        "features_used":
            features_used
    }
