import os

import mongomock
import pytest

# The tests must never call a live service (or spend quota): blank every
# external key BEFORE the app loads .env (load_dotenv does not override
# variables that already exist).
for name in (
    "SARVAM_API_KEY", "GEMINI_API_KEY", "WEATHER_API_KEY", "AGMARKNET_API_KEY",
    "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN", "MONGODB_URI",
):
    os.environ[name] = ""

# The Gemini client refuses to be created without a key. A fake one is fine:
# every test that reaches Gemini replaces it, and a stray call just fails.
os.environ["GEMINI_API_KEY"] = "test-key-not-real"

# Must be set before the app is imported
os.environ["JWT_SECRET"] = "test-secret-key-that-is-at-least-32-bytes-long"
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "whsec"

import app.db.database as database  # noqa: E402

database._client = mongomock.MongoClient()

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
import app.routes.equipment_routes as equipment_routes  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_database():
    """Empty in-memory database for every test (Atlas is never touched)."""
    client = database.get_client()

    for name in client.list_database_names():
        client.drop_database(name)

    database.init_indexes()

    yield


@pytest.fixture
def client():
    return TestClient(app)


def register(client, name, phone, role):
    """Log in with the fake OTP and finish onboarding (what a new user does)."""

    login = client.post("/auth/verify-otp", json={"phone": phone, "otp": "123456"})
    assert login.status_code == 200, login.text

    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    profile = client.put("/auth/profile", headers=headers, json={
        "name": name,
        "dob": "1990-05-15",
        "state": "Karnataka",
        "district": "Kolar",
        "language": "en",
        "role": role,
    })
    assert profile.status_code == 200, profile.text

    return {"headers": headers, "user": profile.json()}


@pytest.fixture
def owner(client):
    return register(client, "Ramu Owner", "9000000001", "owner")


@pytest.fixture
def renter(client):
    return register(client, "Shiv Renter", "9000000002", "renter")


@pytest.fixture
def other(client):
    return register(client, "Other Person", "9000000003", "renter")


@pytest.fixture
def equipment_id(client, owner):
    response = client.post("/equipment", headers=owner["headers"], json={
        "equipment_name": "Tractor",
        "price_per_day": 160,
        "location": "Mysuru",
        "contact_number": "9000000001",
        "category": "Tractor"
    })

    assert response.status_code == 200, response.text

    return response.json()["id"]


@pytest.fixture
def fake_razorpay(monkeypatch):
    """Replace the Razorpay network calls with a controllable fake."""

    state = {"status": "captured", "amount": None, "order_id": None}

    monkeypatch.setattr(
        equipment_routes,
        "create_payment_order",
        lambda amount, rental_id: {"id": f"order_{rental_id}"}
    )

    def fake_verify(order_id, payment_id, signature):
        if signature != "good":
            raise ValueError("bad signature")

    monkeypatch.setattr(equipment_routes, "verify_payment", fake_verify)

    def fake_fetch(payment_id):
        return {
            "id": payment_id,
            "status": state["status"],
            "order_id": state["order_id"],
            "amount": state["amount"]
        }

    monkeypatch.setattr(equipment_routes, "fetch_payment", fake_fetch)

    def fake_webhook(body, signature):
        if signature != "webhook-ok":
            raise ValueError("bad signature")

    monkeypatch.setattr(equipment_routes, "verify_webhook", fake_webhook)

    return state
