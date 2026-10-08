import app.db.database as database
from app.services import price_alerts

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
