from datetime import datetime, timedelta, timezone

import app.db.database as database
import app.routes.equipment_routes as equipment_routes
from tests.conftest import register

MYSURU = (12.2958, 76.6394)


def add_equipment(client, owner, **extra):
    response = client.post("/equipment", headers=owner["headers"], json={
        "equipment_name": "Tractor", "price_per_day": 800, "location": "Mysuru",
        "contact_number": "9000000001", "category": "Tractor", **extra
    })

    return response.json()["id"]


def create_key(client, owner, equipment_id):
    response = client.post(f"/equipment/{equipment_id}/tracker-key", headers=owner["headers"])
    assert response.status_code == 200, response.text

    return response.json()["tracker_key"]


def report(client, key, lat=MYSURU[0], lng=MYSURU[1], **extra):
    return client.post(
        "/tracker/update",
        json={"latitude": lat, "longitude": lng, **extra},
        headers={"X-Tracker-Key": key}
    )


def equipment(client, equipment_id):
    return client.get(f"/equipment/{equipment_id}").json()


# ---------------------------------------------------------------- phone tracking

def test_phone_location_is_stored_with_accuracy_and_source(client, owner):
    equipment_id = add_equipment(client, owner)

    response = client.patch(
        f"/equipment/{equipment_id}/location",
        json={"latitude": 12.3, "longitude": 76.6, "accuracy_m": 8.5},
        headers=owner["headers"]
    )

    assert response.status_code == 200

    item = equipment(client, equipment_id)
    assert item["location_geo"] == {"lat": 12.3, "lng": 76.6}
    assert item["location_accuracy_m"] == 8.5
    assert item["location_source"] == "phone"
    assert item["location_live"] is True


def test_location_is_not_live_when_it_is_old(client, owner):
    equipment_id = add_equipment(client, owner, latitude=12.3, longitude=76.6)

    old = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(timespec="seconds")
    database.get_database().equipment.update_one(
        {"id": equipment_id}, {"$set": {"location_updated_at": old}}
    )

    assert equipment(client, equipment_id)["location_live"] is False


def test_equipment_without_gps_is_not_live(client, owner):
    equipment_id = add_equipment(client, owner)

    assert equipment(client, equipment_id)["location_live"] is False


def test_live_flag_is_in_the_nearby_search(client, owner):
    add_equipment(client, owner, latitude=MYSURU[0], longitude=MYSURU[1])

    result = client.get("/equipment", params={"lat": MYSURU[0], "lng": MYSURU[1]}).json()

    assert result[0]["location_live"] is True


def test_invalid_coordinates_are_rejected(client, owner):
    equipment_id = add_equipment(client, owner)

    for body in ({"latitude": 95, "longitude": 10}, {"latitude": 10, "longitude": 190}):
        response = client.patch(
            f"/equipment/{equipment_id}/location", json=body, headers=owner["headers"]
        )
        assert response.status_code == 422


# ---------------------------------------------------------------- tracker device

def test_tracker_key_lets_a_device_report_without_login(client, owner):
    equipment_id = add_equipment(client, owner)
    key = create_key(client, owner, equipment_id)

    assert key.startswith("trk_")

    response = report(client, key, 13.0, 77.0, accuracy_m=4)

    assert response.status_code == 200

    item = equipment(client, equipment_id)
    assert item["location_geo"] == {"lat": 13.0, "lng": 77.0}
    assert item["location_source"] == "tracker"
    assert item["location_live"] is True


def test_tracker_key_is_stored_hashed_and_shown_once(client, owner):
    equipment_id = add_equipment(client, owner)
    key = create_key(client, owner, equipment_id)

    stored = database.get_database().tracker_keys.find_one({"equipment_id": equipment_id})

    assert key not in str(stored)
    assert stored["key_hash"] == equipment_routes.hash_tracker_key(key)


def test_wrong_missing_or_revoked_key_is_rejected(client, owner):
    equipment_id = add_equipment(client, owner)
    key = create_key(client, owner, equipment_id)

    assert report(client, "trk_wrong").status_code == 401
    assert client.post("/tracker/update", json={"latitude": 1, "longitude": 1}).status_code == 401

    revoked = client.delete(f"/equipment/{equipment_id}/tracker-key", headers=owner["headers"])
    assert revoked.status_code == 200
    assert report(client, key).status_code == 401


def test_new_key_replaces_the_old_one(client, owner):
    equipment_id = add_equipment(client, owner)
    old = create_key(client, owner, equipment_id)
    new = create_key(client, owner, equipment_id)

    assert old != new
    assert report(client, old).status_code == 401
    assert report(client, new).status_code == 200


def test_tracker_can_only_move_its_own_equipment(client, owner):
    first = add_equipment(client, owner)
    second = add_equipment(client, owner, latitude=1.0, longitude=1.0)
    key = create_key(client, owner, first)

    report(client, key, 13.0, 77.0)

    assert equipment(client, first)["location_geo"]["lat"] == 13.0
    assert equipment(client, second)["location_geo"]["lat"] == 1.0


def test_tracker_reports_are_rate_limited(client, owner, monkeypatch):
    equipment_id = add_equipment(client, owner)
    key = create_key(client, owner, equipment_id)

    assert report(client, key).status_code == 200
    assert report(client, key).status_code == 429

    # After the interval it works again
    monkeypatch.setattr(equipment_routes, "TRACKER_MIN_INTERVAL_SECONDS", 0)
    assert report(client, key).status_code == 200


def test_only_the_owner_can_manage_tracker_keys(client, owner, renter):
    equipment_id = add_equipment(client, owner)
    intruder = register(client, "Other Owner", "9000000077", "owner")

    url = f"/equipment/{equipment_id}/tracker-key"

    assert client.post(url, headers=renter["headers"]).status_code == 403
    assert client.post(url, headers=intruder["headers"]).status_code == 403
    assert client.post(url).status_code == 401
    assert client.delete(url, headers=intruder["headers"]).status_code == 403


def test_tracker_rejects_bad_coordinates(client, owner):
    equipment_id = add_equipment(client, owner)
    key = create_key(client, owner, equipment_id)

    assert report(client, key, lat=120, lng=10).status_code == 422
