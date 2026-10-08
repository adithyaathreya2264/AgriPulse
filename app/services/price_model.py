"""
Price forecasts from the trained model in ml/ (no price API is called).

The model file holds everything needed: a HistGradientBoosting model, the last 60 weeks of
prices of every crop x district series, and the typical price of each month. Prices inside are
natural logs of Rs per quintal, one value per week.

How the model is used (these scales were read from the model's own decision thresholds and
checked by predicting the bundled history; the training script itself is not part of ml/):

  * the model predicts the CHANGE of the log price from now to a target week
  * lag1 is always 0 (the current price); lag2 .. lag13, mean4, mean13 and the state-wide series are
    all given relative to the current price
  * the week of the year of the origin and of the target are given as sin / cos
  * season_delta is left neutral (0): its exact definition is not stored with the model
"""

import json
import math
import os
from datetime import timedelta
from pathlib import Path

import numpy as np

from app.services.lazy_import import lazy

pd = lazy("pandas")

ROOT = Path(__file__).resolve().parents[2]

MODEL_FILE = "price_forecast_model.pkl"
METRICS_FILE = "price_forecast_metrics.json"

STATE = "__state__"
STATE_DISTRICT = "Karnataka"
STATE_MARKET = "State average"

# 1..4 weeks ahead = the 7, 14, 21 and 28 day points of the forecast chart
HORIZON_WEEKS = (1, 2, 3, 4)

# the price band is this many typical (mean absolute) errors of the crop on each side
BAND_ERRORS = 1.5

# a series whose last price is older than this (before the end of the data) is not offered
MAX_SERIES_AGE_WEEKS = 26

STORAGE_COST_PER_WEEK = 0.005      # 0.5% of the price per week of waiting
TREND_BAND = 0.03                  # +-3% in four weeks counts as "stable"

# what farmers type -> the crop name inside the model
ALIASES = {
    "rice": "rice", "paddy": "paddy", "dhan": "paddy",
    "wheat": "wheat", "gehu": "wheat",
    "maize": "maize", "corn": "maize",
    "cotton": "cotton",
    "groundnut": "groundnut", "peanut": "groundnut", "ground nut": "groundnut",
    "bajra": "bajra", "pearl millet": "bajra", "cumbu": "bajra",
    "jowar": "jowar", "sorghum": "jowar",
    "bengal gram": "bengal_gram", "bengal_gram": "bengal_gram", "gram": "bengal_gram", "chana": "bengal_gram",
    "ragi": "ragi", "finger millet": "ragi",
    "soyabean": "soyabean", "soybean": "soyabean", "soya": "soyabean",
    "arhar": "arhar", "tur": "arhar", "toor": "arhar", "red gram": "arhar",
    "jaggery": "jaggery", "gur": "jaggery",
}


class PriceModelUnavailable(RuntimeError):
    """The model file is missing or cannot be read."""


_bundle = None
_metrics = None


# ---------------------------------------------------------------- loading

def artifact_dir():
    """ml/artifacts, or the folder named in PRICE_MODEL_DIR."""

    override = os.getenv("PRICE_MODEL_DIR")

    candidates = [Path(override)] if override else [ROOT / "ml" / "artifacts"]

    for folder in candidates:
        if (folder / MODEL_FILE).exists():
            return folder

    raise PriceModelUnavailable("The price forecast model is not available")


def bundle():
    global _bundle

    if _bundle is None:
        import joblib

        try:
            _bundle = joblib.load(artifact_dir() / MODEL_FILE)
        except PriceModelUnavailable:
            raise
        except Exception as error:
            print("Price model could not be read:", error)
            raise PriceModelUnavailable("The price forecast model could not be read") from error

    return _bundle


def metrics():
    global _metrics

    if _metrics is None:
        try:
            _metrics = json.loads((artifact_dir() / METRICS_FILE).read_text(encoding="utf-8"))
        except Exception:
            _metrics = {}

    return _metrics


# ---------------------------------------------------------------- helpers

def resolve_crop(name):
    """The crop's name inside the model, or None."""

    key = " ".join(str(name or "").lower().replace("(", " ").replace(")", " ").split())

    if key in ALIASES:
        return ALIASES[key]

    return ALIASES.get(key.replace("_", " "))


def supported_crops():
    """The crops that have a trained forecast."""

    return list(bundle()["shipped_crops"])


def _series(code, district):
    """The weekly log prices of one crop and district (a pandas Series), or None."""

    frame = bundle()["recent_series"]

    wanted = STATE if str(district).strip().lower() in ("karnataka", "state", STATE) else None

    for column in frame.columns:
        if column[0] != code:
            continue

        if wanted and column[1] == wanted:
            return column, frame[column]

        if not wanted and column[1].lower() == str(district).strip().lower():
            return column, frame[column]

    return None, None


def _last_known(series):
    """Position of the latest week that has a price, or None."""

    known = np.flatnonzero(series.notna().values)

    return int(known[-1]) if len(known) else None


def _money(value):
    return round(float(value), 2)


def _crop_error(code):
    """The model's typical error for the crop (log units) and its pooled fallback."""

    info = metrics()

    return (info.get("test_per_crop", {}).get(code) or info.get("test_pooled") or {}).get("mae", 0.13)


# ---------------------------------------------------------------- markets

def markets_for(crop):
    """The Karnataka districts that have a recent price series for the crop."""

    code = resolve_crop(crop)

    if code is None:
        return []

    data = bundle()
    frame = data["recent_series"]
    shipped = code in data["shipped_crops"]
    result = []

    for column in frame.columns:
        if column[0] != code:
            continue

        series = frame[column]
        last = _last_known(series)

        if last is None or last < len(series) - 1 - MAX_SERIES_AGE_WEEKS:
            continue

        week = series.index[last]
        is_state = column[1] == STATE

        result.append({
            "district": STATE_DISTRICT if is_state else column[1],
            "market": STATE_MARKET if is_state else column[1],
            "current_price_available": False,
            "latest_price": _money(math.exp(series.iloc[last])),
            "latest_price_date": week.strftime("%d/%m/%Y"),
            "forecast_available": shipped,
            "_week": week,
        })

    # newest data first, the state average ahead of the districts
    result.sort(key=lambda item: (-item["_week"].value, item["district"] != STATE_DISTRICT, item["district"]))

    for item in result:
        del item["_week"]

    return result


# ---------------------------------------------------------------- forecast

def _features(series, state, last, week_origin, week_target, code, is_state):
    """The model's inputs for one series at one origin week and one target week."""

    cur = series.iloc[last]
    values = series.values

    def back(array, steps):
        index = last - steps
        return array[index] - cur if (array is not None and index >= 0) else np.nan

    def mean(array, count):
        window = array[max(last - count + 1, 0): last + 1]
        return np.nanmean(window) - cur if np.isfinite(window).any() else np.nan

    state_values = state.values if state is not None else None

    origin = week_origin.dayofyear / 365.25
    target = week_target.dayofyear / 365.25

    return {
        "lag1": 0.0,
        "lag2": back(values, 1),
        "lag4": back(values, 3),
        "lag8": back(values, 7),
        "lag13": back(values, 12),
        "mean4": mean(values, 4),
        "mean13": mean(values, 13),
        "state_now": back(state_values, 0),
        "state_lag4": back(state_values, 3),
        "state_lag13": back(state_values, 12),
        "season_delta": 0.0,
        "origin_sin": math.sin(2 * math.pi * origin),
        "origin_cos": math.cos(2 * math.pi * origin),
        "target_sin": math.sin(2 * math.pi * target),
        "target_cos": math.cos(2 * math.pi * target),
        "is_state": int(is_state),
        "crop_code": bundle()["crop_codes"][code],
    }


def forecast(code, district):
    """
    Returns (latest price, latest week, forecast points) for a crop with a trained model.
    Each point is {days, date, price, low, high}.
    """

    data = bundle()
    column, series = _series(code, district)

    if series is None:
        return None

    last = _last_known(series)

    if last is None:
        return None

    state_column, state = _series(code, STATE_DISTRICT)
    origin = series.index[last]
    is_state = column[1] == STATE

    rows = []

    for weeks in HORIZON_WEEKS:
        rows.append(_features(series, state, last, origin, origin + timedelta(weeks=weeks), code, is_state))

    frame = pd.DataFrame(rows)[data["features"]]
    changes = data["model"].predict(frame)

    current = float(series.iloc[last])
    band = BAND_ERRORS * _crop_error(code)
    points = []

    for weeks, change in zip(HORIZON_WEEKS, changes):
        points.append({
            "days": weeks * 7,
            "date": (origin + timedelta(weeks=weeks)).strftime("%Y-%m-%d"),
            "price": _money(math.exp(current + change)),
            "low": _money(math.exp(current + change - band)),
            "high": _money(math.exp(current + change + band)),
        })

    return math.exp(current), origin, points


def latest(code, district):
    """(latest price, week) of a series, or None. Used for crops without a trained forecast."""

    column, series = _series(code, district)

    if series is None:
        return None

    last = _last_known(series)

    if last is None:
        return None

    return math.exp(series.iloc[last]), series.index[last], []


def seasonal_outlook(code, district):
    """For crops without a trained forecast: the typical price of the next three months."""

    data = bundle()
    column, series = _series(code, district)

    if column is None:
        return []

    months = data["outlook"].get(column, {})

    if not months or series is None:
        return []

    last = _last_known(series)
    start = series.index[last if last is not None else -1]
    result = []

    for step in range(1, 4):
        month = (start.month - 1 + step) % 12 + 1
        info = months.get(month)

        if info:
            result.append({
                "month": month,
                "typical": _money(info["median"]),
                "low": _money(info["p25"]),
                "high": _money(info["p75"]),
            })

    return result


def best_time_to_sell(points, current_price):
    """Highest expected price after subtracting a small waiting cost."""

    best = {"days": 0, "price": current_price, "net": current_price}

    for point in points:
        weeks = point["days"] / 7
        net = point["price"] - current_price * STORAGE_COST_PER_WEEK * weeks

        if net > best["net"]:
            best = {"days": point["days"], "price": point["price"], "net": net}

    if best["days"] == 0:
        return {
            "action": "sell_now",
            "days": 0,
            "expected_price": round(float(current_price), 2),
            "message": "Prices are expected to fall or stay flat. Sell now."
        }

    gain = (best["price"] - current_price) / current_price * 100

    return {
        "action": "wait",
        "days": best["days"],
        "expected_price": round(float(best["price"]), 2),
        "message": (
            f"Best expected price in about {best['days']} days "
            f"(around Rs {best['price']:.0f}, {gain:+.1f}% vs now)."
        )
    }


def model_info(code, current_price):
    """The 'how good is this model' numbers shown under the chart."""

    info = metrics()
    crop = info.get("test_per_crop", {}).get(code, {})
    error = _crop_error(code)

    return {
        "model": "gradient-boosting (weekly)",
        # the typical error, in Rs, at today's price
        "mae": round(current_price * (math.exp(error) - 1), 2),
        "beats_baseline": bool(crop.get("passes", False)),
        "direction_accuracy": crop.get("direction_accuracy"),
        "data_end": bundle().get("data_end"),
    }
