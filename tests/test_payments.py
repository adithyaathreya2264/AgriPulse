import json
from datetime import date, timedelta

import app.db.database as database


def start_rental(client, renter, equipment_id):
    start = (date.today() + timedelta(days=1)).isoformat()
    end = (date.today() + timedelta(days=3)).isoformat()

    return client.post("/rent-equipment", headers=renter["headers"], json={
        "equipment_id": equipment_id, "start_date": start, "end_date": end
    }).json()


def create_order(client, user, rental_id):
    return client.post(
        "/create-payment-order",
        headers=user["headers"],
        json={"rental_id": rental_id}
    )


def verify(client, user, rental_id, order_id, payment_id="pay_1", signature="good"):
    return client.post("/verify-payment", headers=user["headers"], json={
        "rental_id": rental_id,
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": signature
    })


def test_full_payment_flow(client, renter, equipment_id, fake_razorpay):
    rental = start_rental(client, renter, equipment_id)

    order = create_order(client, renter, rental["rental_id"]).json()
    assert order["amount"] == 48000  # 480 rupees in paise

    fake_razorpay.update(order_id=order["order_id"], amount=48000)

    response = verify(client, renter, rental["rental_id"], order["order_id"])

    assert response.status_code == 200
    assert response.json()["status"] == "Confirmed"
    assert response.json()["payment_status"] == "Paid"


def test_order_is_reused_not_duplicated(client, renter, equipment_id, fake_razorpay):
    rental = start_rental(client, renter, equipment_id)

    first = create_order(client, renter, rental["rental_id"]).json()
    second = create_order(client, renter, rental["rental_id"]).json()

    assert first["order_id"] == second["order_id"]


def test_replayed_verify_is_idempotent(client, renter, equipment_id, fake_razorpay):
    rental = start_rental(client, renter, equipment_id)
    order = create_order(client, renter, rental["rental_id"]).json()
    fake_razorpay.update(order_id=order["order_id"], amount=48000)

    assert verify(client, renter, rental["rental_id"], order["order_id"]).status_code == 200
    again = verify(client, renter, rental["rental_id"], order["order_id"])

    assert again.status_code == 200
    assert again.json()["message"] == "Payment already verified"

    # A different payment id cannot pay an already paid rental
    other_payment = verify(
        client, renter, rental["rental_id"], order["order_id"], payment_id="pay_2"
    )
    assert other_payment.status_code == 409


def test_order_of_another_rental_rejected(client, renter, equipment_id, fake_razorpay):
    rental = start_rental(client, renter, equipment_id)
    create_order(client, renter, rental["rental_id"])

    response = verify(client, renter, rental["rental_id"], "order_from_elsewhere")

    assert response.status_code == 400
    assert "does not belong" in response.json()["detail"]


def test_bad_signature_rejected(client, renter, equipment_id, fake_razorpay):
    rental = start_rental(client, renter, equipment_id)
    order = create_order(client, renter, rental["rental_id"]).json()

    response = verify(
        client, renter, rental["rental_id"], order["order_id"], signature="forged"
    )

    assert response.status_code == 400
    doc = database.get_database().rentals.find_one({"id": rental["rental_id"]})
    assert doc["payment_status"] == "Pending"


def test_uncaptured_or_wrong_amount_rejected(client, renter, equipment_id, fake_razorpay):
    rental = start_rental(client, renter, equipment_id)
    order = create_order(client, renter, rental["rental_id"]).json()

    fake_razorpay.update(order_id=order["order_id"], amount=100, status="captured")
    assert verify(client, renter, rental["rental_id"], order["order_id"]).status_code == 400

    fake_razorpay.update(amount=48000, status="failed")
    assert verify(client, renter, rental["rental_id"], order["order_id"]).status_code == 400


def test_only_renter_can_pay(client, owner, renter, other, equipment_id, fake_razorpay):
    rental = start_rental(client, renter, equipment_id)

    assert create_order(client, other, rental["rental_id"]).status_code == 403
    assert create_order(client, owner, rental["rental_id"]).status_code == 403


def test_expired_booking_cannot_create_order(client, renter, equipment_id, fake_razorpay):
    rental = start_rental(client, renter, equipment_id)

    database.get_database().rentals.update_one(
        {"id": rental["rental_id"]},
        {"$set": {"expires_at": "2000-01-01T00:00:00+00:00"}}
    )

    assert create_order(client, renter, rental["rental_id"]).status_code == 400


def webhook(client, event, payment, signature="webhook-ok"):
    return client.post(
        "/razorpay-webhook",
        content=json.dumps(
            {"event": event, "payload": {"payment": {"entity": payment}}}
        ),
        headers={"X-Razorpay-Signature": signature}
    )


def test_webhook_bad_signature_rejected(client, fake_razorpay):
    response = webhook(client, "payment.captured", {}, signature="forged")

    assert response.status_code == 400


def test_webhook_confirms_rental_once(client, renter, equipment_id, fake_razorpay):
    rental = start_rental(client, renter, equipment_id)
    order = create_order(client, renter, rental["rental_id"]).json()

    payment = {"id": "pay_9", "order_id": order["order_id"], "amount": 48000}

    assert webhook(client, "payment.captured", payment).status_code == 200
    assert webhook(client, "payment.captured", payment).status_code == 200

    doc = database.get_database().rentals.find_one({"id": rental["rental_id"]})
    assert doc["status"] == "Confirmed"
    assert doc["payment_status"] == "Paid"
    assert doc["razorpay_payment_id"] == "pay_9"


def test_webhook_wrong_amount_ignored(client, renter, equipment_id, fake_razorpay):
    rental = start_rental(client, renter, equipment_id)
    order = create_order(client, renter, rental["rental_id"]).json()

    payment = {"id": "pay_9", "order_id": order["order_id"], "amount": 1}
    webhook(client, "payment.captured", payment)

    doc = database.get_database().rentals.find_one({"id": rental["rental_id"]})
    assert doc["payment_status"] == "Pending"
