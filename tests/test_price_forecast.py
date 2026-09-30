from datetime import date, timedelta

import numpy as np
import pandas as pd

import app.db.database as database
from app.services import price_alerts, price_history_service
from app.services.price_forecast import (
    best_time_to_sell,
    forecast_prices
)


def seasonal_rows(days, noise=15, seed=0):
    """Two-year style seasonal price: yearly wave around Rs 2000."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp(date.today() - timedelta(days=days))

    rows = []

    for i in range(days):
        day = start + pd.Timedelta(days=i)
        price = 2000 + 500 * np.sin(2 * np.pi * day.dayofyear / 365.25)
        rows.append({"date": day, "price": price + rng.normal(0, noise)})

    return rows


def test_forecast_has_four_horizons_and_bands():
    forecast, metrics, features = forecast_prices(seasonal_rows(3 * 365))

    assert [point["days"] for point in forecast] == [7, 14, 21, 28]

    for point in forecast:
        assert point["low"] <= point["price"] <= point["high"]

    assert "seasonality" in features
    assert metrics["model"] == "gradient-boosting"


def test_model_beats_linear_baseline_on_seasonal_data():
    _, metrics, _ = forecast_prices(seasonal_rows(4 * 365))

    assert metrics["beats_linear_baseline"] is True
    assert metrics["mae"] < metrics["linear_baseline_mae"]


def test_forecast_tracks_the_seasonal_wave():
    rows = seasonal_rows(4 * 365, noise=5)
    forecast, _, _ = forecast_prices(rows)

    last_day = pd.Timestamp(rows[-1]["date"])
    target = last_day + pd.Timedelta(days=28)
    expected = 2000 + 500 * np.sin(2 * np.pi * target.dayofyear / 365.25)

    assert abs(forecast[-1]["price"] - expected) < 150


def test_short_history_falls_back_to_linear_trend():
    forecast, metrics, features = forecast_prices(seasonal_rows(40))

    assert metrics["model"] == "linear-trend"
    assert len(forecast) == 4
    assert features == ["price history"]


def test_weather_features_are_used_when_available():
    rows = seasonal_rows(3 * 365)
    index = pd.date_range(rows[0]["date"], rows[-1]["date"], freq="D")
    weather = pd.DataFrame(
        {"rain": np.random.default_rng(1).random(len(index)) * 10,
         "temp": 25 + np.random.default_rng(2).random(len(index))},
        index=index
    )

    _, _, features = forecast_prices(rows, weather)

    assert "rainfall and temperature" in features


def test_best_time_to_sell():
    rising = [
        {"days": 7, "price": 2050}, {"days": 14, "price": 2200},
        {"days": 21, "price": 2100}, {"days": 28, "price": 2000},
    ]
    falling = [{"days": d, "price": 1900 - d} for d in (7, 14, 21, 28)]

    assert best_time_to_sell(rising, 2000)["days"] == 14
    assert best_time_to_sell(falling, 2000)["action"] == "sell_now"


# ----------------------------------------------------------------
# History cache
# ----------------------------------------------------------------

def test_history_is_downloaded_once_and_cached(monkeypatch):
    calls = {"count": 0}

    def fake_download(crop, district, market):
        calls["count"] += 1
        return [
            {"date": "2026-01-01", "price": 1000.0, "min_price": 900.0, "max_price": 1100.0},
            {"date": "2026-01-02", "price": 1010.0, "min_price": 900.0, "max_price": 1100.0},
        ]

    monkeypatch.setattr(price_history_service, "download_history", fake_download)

    first = price_history_service.get_history("Tomato", "Kolar", "Kolar")
    second = price_history_service.get_history("Tomato", "Kolar", "Kolar")

    assert calls["count"] == 1          # second call served from the cache
    assert len(first) == len(second) == 2
    assert first[0]["price"] == 1000.0


def test_history_falls_back_to_cache_when_api_fails(monkeypatch):
    db = database.get_database()
    db.price_history.insert_one({
        "crop": "tomato", "district": "kolar", "market": "kolar",
        "date": date.today().isoformat(), "price": 1234.0
    })

    monkeypatch.setattr(
        price_history_service, "download_history", lambda *args: None
    )

    history = price_history_service.get_history("Tomato", "Kolar", "Kolar")

    assert history[0]["price"] == 1234.0


# ----------------------------------------------------------------
# Alerts
# ----------------------------------------------------------------

RESULT = {
    "current_price": 2000,
    "forecast": [
        {"days": 7, "price": 2050}, {"days": 14, "price": 2250},
        {"days": 21, "price": 2100}, {"days": 28, "price": 1800},
    ],
    "best_time_to_sell": {"action": "wait", "days": 14, "message": "Wait 14 days."},
}


def alert(kind, threshold=5):
    return {"crop": "Tomato", "market": "Kolar", "kind": kind,
            "threshold_percent": threshold}


def test_alert_rules():
    assert "rise 12.5%" in price_alerts.evaluate_alert(alert("rise", 10), RESULT)
    assert price_alerts.evaluate_alert(alert("rise", 20), RESULT) is None
    assert "fall 10.0%" in price_alerts.evaluate_alert(alert("fall", 5), RESULT)
    assert price_alerts.evaluate_alert(alert("best_time"), RESULT) is None
    assert price_alerts.evaluate_alert(alert("rise"), {}) is None


def test_check_alerts_notifies_once_and_respects_cooldown(client, renter):
    calls = {"predict": 0, "whatsapp": []}

    def predictor(crop, district, market):
        calls["predict"] += 1
        return RESULT

    create = client.post("/alerts", headers=renter["headers"], json={
        "crop": "Tomato", "district": "Kolar", "market": "Kolar",
        "kind": "rise", "threshold_percent": 10
    })
    assert create.status_code == 200

    db = database.get_database()

    fired = price_alerts.check_alerts(
        db, predictor=predictor,
        whatsapp_sender=lambda phone, message: calls["whatsapp"].append(phone)
    )

    assert fired == 1
    assert calls["whatsapp"] == ["9000000002"]

    # Second run within 24 h: cooldown, nothing new
    assert price_alerts.check_alerts(db, predictor=predictor) == 0

    notifications = client.get("/notifications", headers=renter["headers"]).json()
    assert len(notifications) == 1
    assert "may rise" in notifications[0]["message"]


def test_alerts_are_private_to_their_user(client, renter, other):
    created = client.post("/alerts", headers=renter["headers"], json={
        "crop": "Onion", "district": "Kolar", "market": "Kolar"
    }).json()

    assert client.get("/alerts", headers=other["headers"]).json() == []
    assert client.delete(
        f"/alerts/{created['id']}", headers=other["headers"]
    ).status_code == 404
    assert client.delete(
        f"/alerts/{created['id']}", headers=renter["headers"]
    ).status_code == 200


def test_alerts_require_login(client):
    assert client.get("/alerts").status_code == 401
    assert client.post("/alerts", json={}).status_code == 401
