"""
Agmarknet price history (5+ years) with a daily MongoDB cache.

The data.gov.in API is slow, so history is downloaded at most once a day
per crop + market and stored in the `price_history` collection.
"""

from datetime import datetime, timedelta, timezone

import pandas as pd
from app.db.database import get_database
from app.services import price_service

YEARS = 5
PAGE_SIZE = 1000
MAX_RECORDS = 6000          # ~5 years of daily rows even with several varieties
CACHE_HOURS = 24


def _key(crop, district, market):
    return {
        "crop": crop.strip().lower(),
        "district": district.strip().lower(),
        "market": market.strip().lower()
    }


def _parse_records(records):
    rows = []

    for item in records:
        try:
            rows.append({
                "date": pd.to_datetime(
                    item.get("Arrival_Date"), dayfirst=True
                ).strftime("%Y-%m-%d"),
                "price": float(item.get("Modal_Price")),
                "min_price": float(item.get("Min_Price") or 0),
                "max_price": float(item.get("Max_Price") or 0),
            })
        except (ValueError, TypeError):
            continue

    return rows


def download_history(crop, district, market):
    """Download up to MAX_RECORDS of the newest records. None on API failure."""

    base = {
        "api-key": price_service.API_KEY,
        "format": "json",
        "filters[State]": "Karnataka",
        "filters[District]": district,
        "filters[Commodity]": crop,
        "filters[Market]": market,
    }

    first = price_service.call_api(
        price_service.HISTORY_API,
        {**base, "offset": 0, "limit": 1}
    )

    if not first:
        return None

    total = int(first.get("total", 0))

    if total == 0:
        return []

    start = max(total - MAX_RECORDS, 0)
    records = []

    for offset in range(start, total, PAGE_SIZE):
        page = price_service.call_api(
            price_service.HISTORY_API,
            {**base, "offset": offset, "limit": PAGE_SIZE}
        )

        if not page:
            # Partial download is still useful; only fail if nothing came back
            break

        records.extend(page.get("records", []))

    return _parse_records(records) if records else None


def _is_fresh(meta):
    if not meta:
        return False

    fetched = datetime.fromisoformat(meta["fetched_at"])

    return datetime.now(timezone.utc) - fetched < timedelta(hours=CACHE_HOURS)


def get_history(crop, district, market, years=YEARS, db=None):
    """
    Daily price history as [{"date": Timestamp, "price": float}], oldest first.
    Returns None when there is nothing (no cache and the API failed).
    """

    db = db if db is not None else get_database()
    key = _key(crop, district, market)

    meta = db.price_history_meta.find_one(key)

    if not _is_fresh(meta):
        rows = download_history(crop, district, market)

        if rows:
            known = {
                item["date"]
                for item in db.price_history.find(key, {"date": 1})
            }

            new_rows = {}

            for row in rows:
                if row["date"] not in known:
                    new_rows[row["date"]] = {**key, **row}

            if new_rows:
                db.price_history.insert_many(list(new_rows.values()))

        if rows is not None:
            db.price_history_meta.update_one(
                key,
                {"$set": {
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "records": len(rows)
                }},
                upsert=True
            )

    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=365 * years)
    ).strftime("%Y-%m-%d")

    cached = list(
        db.price_history.find({**key, "date": {"$gte": cutoff}})
        .sort("date", 1)
    )

    if not cached:
        return None

    return [
        {"date": pd.to_datetime(item["date"]), "price": item["price"]}
        for item in cached
    ]
