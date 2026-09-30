from datetime import date, datetime, timedelta

import pytest

import app.db.database as database
from app.services.geo import bounding_box, haversine_km, within_radius
from app.services.rental_lifecycle import migrate_rentals, run_lifecycle

MYSURU = (12.2958, 76.6394)


def offset_point(lat, lng, km_north=0.0, km_east=0.0):
    """A point roughly km_north / km_east away."""
    return lat + km_north / 111.0, lng + km_east / 108.6


def add_equipment(client, owner, name, lat=None, lng=None, per_hour=None, **extra):
    body = {
        "equipment_name": name, "price_per_day": 800, "location": "Mysuru",
        "contact_number": "9000000001", "category": "Tractor", **extra
    }

    if lat is not None:
        body.update(latitude=lat, longitude=lng)

    if per_hour:
        body["price_per_hour"] = per_hour

    response = client.post("/equipment", headers=owner["headers"], json=body)
    assert response.status_code == 200, response.text

    return response.json()["id"]


# ----------------------------------------------------------------
# geo helpers
# ----------------------------------------------------------------

def test_haversine_known_distance():
    # Bengaluru -> Mysuru is about 126 km as the crow flies
    assert haversine_km(12.9716, 77.5946, 12.2958, 76.6394) == pytest.approx(126, abs=4)
    assert haversine_km(1, 1, 1, 1) == 0


def test_bounding_box_contains_circle():
    min_lat, max_lat, min_lng, max_lng = bounding_box(*MYSURU, 10)

    assert min_lat < MYSURU[0] < max_lat
    assert min_lng < MYSURU[1] < max_lng
    assert 19 < (max_lat - min_lat) * 111 < 21


# ----------------------------------------------------------------
# nearby search
# ----------------------------------------------------------------

def test_radius_search_returns_only_nearby_sorted(client, owner):
    add_equipment(client, owner, "Near 3km", *offset_point(*MYSURU, km_north=3))
    add_equipment(client, owner, "Near 8km", *offset_point(*MYSURU, km_east=8))
    add_equipment(client, owner, "Far 15km", *offset_point(*MYSURU, km_north=15))
    add_equipment(client, owner, "No GPS")

    result = client.get(
        "/equipment", params={"lat": MYSURU[0], "lng": MYSURU[1]}
    ).json()

    assert [item["equipment_name"] for item in result] == ["Near 3km", "Near 8km"]
    assert result[0]["distance_km"] == pytest.approx(3, abs=0.2)
    assert result[1]["distance_km"] == pytest.approx(8, abs=0.3)

    wider = client.get(
        "/equipment",
        params={"lat": MYSURU[0], "lng": MYSURU[1], "radius_km": 20}
    ).json()

    assert len(wider) == 3


def test_search_without_location_returns_everything(client, owner):
    add_equipment(client, owner, "A", *MYSURU)
    add_equipment(client, owner, "B")

    assert len(client.get("/equipment").json()) == 2


def test_lat_without_lng_is_rejected(client):
    assert client.get("/equipment", params={"lat": 12}).status_code == 400


def test_owner_can_update_gps_location(client, owner, renter):
    equipment_id = add_equipment(client, owner, "Tractor", *MYSURU)
    far = offset_point(*MYSURU, km_north=50)

    url = f"/equipment/{equipment_id}/location"

    body = {"latitude": far[0], "longitude": far[1]}

    assert client.patch(url, json=body, headers=renter["headers"]).status_code == 403
    assert client.patch(url, json=body, headers=owner["headers"]).status_code == 200

    nearby = client.get(
        "/equipment", params={"lat": MYSURU[0], "lng": MYSURU[1]}
    ).json()

    assert nearby == []

    item = client.get(f"/equipment/{equipment_id}").json()
    assert item["location_geo"]["lat"] == pytest.approx(far[0])
    assert item["location_updated_at"]


def test_other_owner_cannot_move_my_equipment(client, owner):
    from tests.conftest import register

    equipment_id = add_equipment(client, owner, "Tractor", *MYSURU)
    intruder = register(client, "Another Owner", "9000000009", "owner")

    response = client.patch(
        f"/equipment/{equipment_id}/location",
        json={"latitude": 1, "longitude": 1},
        headers=intruder["headers"]
    )

    assert response.status_code == 403


# ----------------------------------------------------------------
# availability
# ----------------------------------------------------------------

def test_owner_availability_toggle_blocks_rentals(client, owner, renter):
    equipment_id = add_equipment(client, owner, "Tractor")
    day_after = (date.today() + timedelta(days=2)).isoformat()

    rent = {
        "equipment_id": equipment_id,
        "start_date": day_after, "end_date": day_after
    }

    off = client.patch(
        f"/equipment/{equipment_id}/availability",
        json={"availability": "Unavailable"}, headers=owner["headers"]
    )
    assert off.status_code == 200

    assert client.post("/rent-equipment", json=rent, headers=renter["headers"]).status_code == 400

    client.patch(
        f"/equipment/{equipment_id}/availability",
        json={"availability": "Available"}, headers=owner["headers"]
    )

    assert client.post("/rent-equipment", json=rent, headers=renter["headers"]).status_code == 200


def test_availability_value_is_validated(client, owner):
    equipment_id = add_equipment(client, owner, "Tractor")

    response = client.patch(
        f"/equipment/{equipment_id}/availability",
        json={"availability": "Whenever"}, headers=owner["headers"]
    )

    assert response.status_code == 422


# ----------------------------------------------------------------
# hourly booking
# ----------------------------------------------------------------

def tomorrow_at(hour, minute=0):
    day = date.today() + timedelta(days=1)
    return datetime(day.year, day.month, day.day, hour, minute)


def rent_hours(client, user, equipment_id, start, end):
    return client.post("/rent-equipment", headers=user["headers"], json={
        "equipment_id": equipment_id,
        "booking_type": "hour",
        "start_at": start.isoformat(),
        "end_at": end.isoformat()
    })


def test_hourly_price_rounds_up_to_whole_hours(client, owner, renter):
    equipment_id = add_equipment(client, owner, "Drone", per_hour=250)

    exact = rent_hours(client, renter, equipment_id, tomorrow_at(9), tomorrow_at(12)).json()
    assert exact["hours"] == 3
    assert exact["total_amount"] == 750
    assert exact["booking_type"] == "hour"

    partial = rent_hours(
        client, renter, equipment_id, tomorrow_at(14), tomorrow_at(15, 10)
    ).json()
    assert partial["hours"] == 2
    assert partial["total_amount"] == 500


def test_hourly_needs_an_hourly_rate(client, owner, renter):
    equipment_id = add_equipment(client, owner, "Plough")  # no per-hour price

    response = rent_hours(client, renter, equipment_id, tomorrow_at(9), tomorrow_at(11))

    assert response.status_code == 400
    assert "by the hour" in response.json()["detail"]


def test_hourly_validation(client, owner, renter):
    equipment_id = add_equipment(client, owner, "Drone", per_hour=250)

    # End before start
    assert rent_hours(client, renter, equipment_id, tomorrow_at(12), tomorrow_at(9)).status_code == 400

    # In the past
    past = datetime.now() - timedelta(hours=3)
    assert rent_hours(client, renter, equipment_id, past, past + timedelta(hours=1)).status_code == 400

    # Longer than a day: use day booking
    long_end = tomorrow_at(9) + timedelta(hours=30)
    assert rent_hours(client, renter, equipment_id, tomorrow_at(9), long_end).status_code == 400


def test_hourly_overlap_matrix(client, owner, renter, other):
    equipment_id = add_equipment(client, owner, "Drone", per_hour=250)

    assert rent_hours(client, renter, equipment_id, tomorrow_at(10), tomorrow_at(12)).status_code == 200

    # Overlapping partly, fully inside, and fully around: all rejected
    assert rent_hours(client, other, equipment_id, tomorrow_at(11), tomorrow_at(13)).status_code == 400
    assert rent_hours(client, other, equipment_id, tomorrow_at(10, 30), tomorrow_at(11)).status_code == 400
    assert rent_hours(client, other, equipment_id, tomorrow_at(9), tomorrow_at(14)).status_code == 400

    # Back-to-back slots are fine
    assert rent_hours(client, other, equipment_id, tomorrow_at(12), tomorrow_at(14)).status_code == 200
    assert rent_hours(client, other, equipment_id, tomorrow_at(8), tomorrow_at(10)).status_code == 200


def test_hourly_and_day_bookings_block_each_other(client, owner, renter, other):
    equipment_id = add_equipment(client, owner, "Drone", per_hour=250)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    assert rent_hours(client, renter, equipment_id, tomorrow_at(10), tomorrow_at(12)).status_code == 200

    # A whole-day booking of the same day clashes with the hourly one
    whole_day = client.post("/rent-equipment", headers=other["headers"], json={
        "equipment_id": equipment_id, "start_date": tomorrow, "end_date": tomorrow
    })
    assert whole_day.status_code == 400

    # ... and the day after is free
    day_after = (date.today() + timedelta(days=2)).isoformat()
    free = client.post("/rent-equipment", headers=other["headers"], json={
        "equipment_id": equipment_id, "start_date": day_after, "end_date": day_after
    })
    assert free.status_code == 200

    # An hourly slot inside a booked whole day is rejected
    assert rent_hours(
        client, renter, equipment_id,
        tomorrow_at(15) + timedelta(days=1), tomorrow_at(16) + timedelta(days=1)
    ).status_code == 400


def test_bookings_calendar_lists_blocked_slots(client, owner, renter):
    equipment_id = add_equipment(client, owner, "Drone", per_hour=250)

    rent_hours(client, renter, equipment_id, tomorrow_at(10), tomorrow_at(12))

    bookings = client.get(f"/equipment/{equipment_id}/bookings").json()

    assert len(bookings) == 1
    assert bookings[0]["booking_type"] == "hour"
    assert bookings[0]["start_at"] == tomorrow_at(10).isoformat(timespec="seconds")
    assert "renter_name" not in bookings[0]          # no personal details

    assert client.get("/equipment/999/bookings").status_code == 404


def test_lifecycle_uses_hourly_times():
    db = database.get_database()
    now = datetime.now()

    def add(rental_id, status, start, end):
        db.rentals.insert_one({
            "id": rental_id, "equipment_id": 1, "status": status,
            "start_at": start.isoformat(timespec="seconds"),
            "end_at": end.isoformat(timespec="seconds")
        })

    add(1, "Confirmed", now - timedelta(hours=1), now + timedelta(hours=1))
    add(2, "Active", now - timedelta(hours=3), now - timedelta(minutes=5))
    add(3, "Confirmed", now + timedelta(hours=2), now + timedelta(hours=4))

    run_lifecycle()

    status = {r["id"]: r["status"] for r in db.rentals.find()}
    assert status == {1: "Active", 2: "Completed", 3: "Confirmed"}


def test_old_day_rentals_are_migrated():
    db = database.get_database()

    db.rentals.insert_one({
        "id": 1, "equipment_id": 1, "status": "Confirmed",
        "start_date": "2030-01-01", "end_date": "2030-01-03"
    })

    migrate_rentals()

    rental = db.rentals.find_one({"id": 1})
    assert rental["start_at"] == "2030-01-01T00:00:00"
    assert rental["end_at"] == "2030-01-04T00:00:00"
    assert rental["booking_type"] == "day"


# ----------------------------------------------------------------
# UPI hint
# ----------------------------------------------------------------

def test_payment_order_asks_for_upi(client, owner, renter, fake_razorpay, monkeypatch):
    equipment_id = add_equipment(client, owner, "Tractor")
    day_after = (date.today() + timedelta(days=2)).isoformat()

    rental = client.post("/rent-equipment", headers=renter["headers"], json={
        "equipment_id": equipment_id, "start_date": day_after, "end_date": day_after
    }).json()

    order = client.post(
        "/create-payment-order", headers=renter["headers"],
        json={"rental_id": rental["rental_id"]}
    ).json()

    assert order["upi_preferred"] is True
    assert order["upi_only"] is False

    monkeypatch.setenv("RAZORPAY_UPI_ONLY", "true")
    again = client.post(
        "/create-payment-order", headers=renter["headers"],
        json={"rental_id": rental["rental_id"]}
    ).json()

    assert again["upi_only"] is True


def test_within_radius_helper_ignores_items_without_gps():
    items = [
        {"name": "a", "location_geo": {"lat": 12.3, "lng": 76.64}},
        {"name": "b", "location_geo": None},
        {"name": "c"},
    ]

    result = within_radius(items, *MYSURU, 10)

    assert [item["name"] for item in result] == ["a"]
