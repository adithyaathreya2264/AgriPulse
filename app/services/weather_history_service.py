"""
Historical daily weather (rain + temperature) from Open-Meteo (free, no key),
cached per district in MongoDB.
"""

import json
import os
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import requests

from app.db.database import get_database

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

_DISTRICTS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "karnataka_districts.json"
)

with open(_DISTRICTS_FILE, encoding="utf-8") as f:
    DISTRICTS = json.load(f)


def district_coordinates(district):
    """(lat, lon) for a Karnataka district name, or None."""
    return tuple(DISTRICTS[district.strip().lower()]) \
        if district and district.strip().lower() in DISTRICTS else None


def _download(lat, lon, start, end):
    response = requests.get(
        ARCHIVE_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": "temperature_2m_mean,precipitation_sum",
            "timezone": "Asia/Kolkata",
        },
        timeout=30
    )
    response.raise_for_status()

    daily = response.json()["daily"]

    return [
        {"date": day, "temp": temp, "rain": rain}
        for day, temp, rain in zip(
            daily["time"],
            daily["temperature_2m_mean"],
            daily["precipitation_sum"]
        )
        if temp is not None and rain is not None
    ]


def get_weather_history(district, start, end, db=None):
    """
    DataFrame indexed by date with columns `temp` and `rain`,
    or None when the district is unknown or the API fails without a cache.
    """

    coordinates = district_coordinates(district)

    if not coordinates:
        return None

    db = db if db is not None else get_database()
    key = {"district": district.strip().lower()}

    meta = db.weather_history_meta.find_one(key)
    today = date.today()

    # Refresh when we have never fetched, or the cache is older than a day
    stale = True

    if meta:
        fetched = datetime.fromisoformat(meta["fetched_at"])
        stale = datetime.now(timezone.utc) - fetched > timedelta(hours=24)

        # A longer range than we downloaded before needs a new download
        if pd.Timestamp(start).date().isoformat() < meta.get("start", "0000-00-00"):
            stale = True

    if stale:
        try:
            # Open-Meteo archive lags a few days behind today
            rows = _download(
                *coordinates,
                pd.Timestamp(start).date(),
                min(pd.Timestamp(end).date(), today - timedelta(days=3))
            )

            if rows:
                known = {
                    item["date"]
                    for item in db.weather_history.find(key, {"date": 1})
                }

                new_rows = [
                    {**key, **row}
                    for row in rows
                    if row["date"] not in known
                ]

                if new_rows:
                    db.weather_history.insert_many(new_rows)

            db.weather_history_meta.update_one(
                key,
                {"$set": {
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "start": min(
                        pd.Timestamp(start).date().isoformat(),
                        (meta or {}).get("start", "9999-99-99")
                    )
                }},
                upsert=True
            )

        except Exception as e:
            print("Weather history error:", e)

    cached = list(db.weather_history.find(key).sort("date", 1))

    if not cached:
        return None

    frame = pd.DataFrame(cached)[["date", "temp", "rain"]]
    frame["date"] = pd.to_datetime(frame["date"])

    return frame.set_index("date")
