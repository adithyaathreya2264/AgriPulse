from datetime import date, timedelta

import app.db.database as database
from app.services.rental_lifecycle import run_lifecycle


def day(offset):
    return (date.today() + timedelta(days=offset)).isoformat()


def rent(client, user, equipment_id, start, end):
    return client.post("/rent-equipment", headers=user["headers"], json={
        "equipment_id": equipment_id,
        "start_date": start,
        "end_date": end
    })


def test_price_calculation_includes_both_days(client, renter, equipment_id):
    response = rent(client, renter, equipment_id, day(1), day(3))

    assert response.status_code == 200
    data = response.json()
    assert data["rental_days"] == 3
    assert data["total_amount"] == 480
    assert data["status"] == "Pending"


def test_overlapping_dates_rejected(client, renter, other, equipment_id):
    assert rent(client, renter, equipment_id, day(1), day(3)).status_code == 200

    response = rent(client, other, equipment_id, day(3), day(5))

    assert response.status_code == 400
    assert "already booked" in response.json()["detail"]


def test_different_dates_allowed(client, renter, other, equipment_id):
    assert rent(client, renter, equipment_id, day(1), day(3)).status_code == 200
    assert rent(client, other, equipment_id, day(10), day(12)).status_code == 200


def test_invalid_dates_rejected(client, renter, equipment_id):
    assert rent(client, renter, equipment_id, day(3), day(1)).status_code == 400
    assert rent(client, renter, equipment_id, day(-2), day(1)).status_code == 400


def test_cannot_rent_own_equipment(client, owner, equipment_id):
    assert rent(client, owner, equipment_id, day(1), day(2)).status_code == 400


def test_unpaid_booking_expires_and_frees_dates(
    client, renter, other, equipment_id
):
    first = rent(client, renter, equipment_id, day(1), day(3)).json()

    # Simulate the 15 minute payment window running out
    database.get_database().rentals.update_one(
        {"id": first["rental_id"]},
        {"$set": {"expires_at": "2000-01-01T00:00:00+00:00"}}
    )

    assert rent(client, other, equipment_id, day(1), day(3)).status_code == 200


def test_rental_visible_only_to_participants(
    client, owner, renter, other, equipment_id
):
    rental = rent(client, renter, equipment_id, day(1), day(2)).json()
    url = f"/rentals/{rental['rental_id']}"

    assert client.get(url, headers=renter["headers"]).status_code == 200
    assert client.get(url, headers=owner["headers"]).status_code == 200
    assert client.get(url, headers=other["headers"]).status_code == 403
    assert client.get("/rentals/9999", headers=renter["headers"]).status_code == 404


def test_lifecycle_transitions():
    db = database.get_database()

    def add(rental_id, status, start, end, **extra):
        db.rentals.insert_one({
            "id": rental_id, "equipment_id": 1, "status": status,
            "start_at": start + "T00:00:00", "end_at": end + "T00:00:00", **extra
        })

    add(1, "Pending", day(1), day(2), expires_at="2000-01-01T00:00:00+00:00")
    add(2, "Confirmed", day(-1), day(2))
    add(3, "Active", day(-5), day(-1))
    add(4, "Confirmed", day(5), day(6))

    result = run_lifecycle()

    status = {r["id"]: r["status"] for r in db.rentals.find()}
    assert status == {1: "Expired", 2: "Active", 3: "Completed", 4: "Confirmed"}
    assert result == {"expired": 1, "completed": 1, "activated": 1}
