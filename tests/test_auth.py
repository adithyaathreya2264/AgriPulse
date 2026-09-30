from datetime import date

import pytest

import app.db.database as database
from app.services.auth_service import compute_age, normalize_phone, user_code
from tests.conftest import register

PROFILE = {
    "name": "Ramu Gowda",
    "dob": "1990-05-15",
    "state": "Karnataka",
    "district": "Mandya",
    "village": "Maddur",
    "language": "kn",
    "role": "owner",
}


def login(client, phone="9876543210", otp="123456"):
    return client.post("/auth/verify-otp", json={"phone": phone, "otp": otp})


def auth(response):
    return {"Authorization": f"Bearer {response.json()['token']}"}


# ---------------------------------------------------------------- phone numbers and codes

@pytest.mark.parametrize("raw,expected", [
    ("9876543210", "9876543210"),
    ("98765 43210", "9876543210"),
    ("+91-98765-43210", "9876543210"),
    ("919876543210", "9876543210"),
    ("09876543210", "9876543210"),
    ("(987) 654 3210", "9876543210"),
    ("987654321", None),                  # 9 digits
    ("98765432101", None),                # 11 digits
    ("abcdefghij", None),
    ("", None),
    (None, None),
])
def test_phone_normalisation(raw, expected):
    assert normalize_phone(raw) == expected


def test_user_code_is_first_two_plus_last_two_digits():
    assert user_code("9876543210") == "9810"
    assert user_code("1234567890") == "1290"
    assert user_code("0000000000") == "0000"


# ---------------------------------------------------------------- send OTP

def test_send_otp_tells_the_demo_user_which_code_to_type(client):
    response = client.post("/auth/send-otp", json={"phone": "98765 43210"})

    assert response.status_code == 200
    body = response.json()
    assert body["phone"] == "9876543210"
    assert body["demo"] is True
    assert body["demo_otp"] == "123456"


@pytest.mark.parametrize("phone", ["12345", "98765432101", "not a number", ""])
def test_send_otp_rejects_bad_numbers(client, phone):
    assert client.post("/auth/send-otp", json={"phone": phone}).status_code == 422


# ---------------------------------------------------------------- verify OTP

def test_wrong_otp_is_rejected(client):
    for otp in ("000000", "12345", "1234567", "", "abcdef"):
        assert login(client, otp=otp).status_code == 401

    # ... and no account was created by the failed attempts
    assert database.get_database().users.count_documents({}) == 0


def test_first_login_creates_an_account_that_needs_onboarding(client):
    response = login(client)

    assert response.status_code == 200
    body = response.json()

    assert body["is_new_user"] is True
    assert body["onboarding_required"] is True
    assert body["token"]

    user = body["user"]
    assert user["phone"] == "9876543210"
    assert user["user_code"] == "9810"
    assert user["onboarded"] is False
    assert user["name"] == ""
    assert "password_hash" not in user


def test_phone_formatting_does_not_create_a_second_account(client):
    first = login(client, "9876543210").json()
    second = login(client, "+91 98765-43210").json()

    assert first["user"]["id"] == second["user"]["id"]
    assert database.get_database().users.count_documents({}) == 1


def test_wrong_phone_format_is_rejected_on_verify(client):
    assert login(client, phone="12345").status_code == 422


# ---------------------------------------------------------------- onboarding

def test_onboarding_saves_the_profile(client):
    headers = auth(login(client))

    response = client.put("/auth/profile", json=PROFILE, headers=headers)

    assert response.status_code == 200
    user = response.json()

    assert user["name"] == "Ramu Gowda"
    assert user["dob"] == "1990-05-15"
    assert user["state"] == "Karnataka"
    assert user["district"] == "Mandya"
    assert user["village"] == "Maddur"
    assert user["language"] == "kn"
    assert user["role"] == "owner"
    assert user["onboarded"] is True
    assert user["age"] == compute_age(date(1990, 5, 15))


def test_returning_user_gets_the_saved_profile_back(client):
    """The data is stored in MongoDB and comes back on the next login."""

    first = login(client)
    client.put("/auth/profile", json=PROFILE, headers=auth(first))

    again = login(client).json()

    assert again["is_new_user"] is False
    assert again["onboarding_required"] is False
    assert again["user"]["id"] == first.json()["user"]["id"]

    user = again["user"]
    assert (user["name"], user["state"], user["district"]) == ("Ramu Gowda", "Karnataka", "Mandya")
    assert user["language"] == "kn" and user["role"] == "owner"

    # It really is in the database, not just in the session
    stored = database.get_database().users.find_one({"phone": "9876543210"})
    assert stored["name"] == "Ramu Gowda"
    assert stored["dob"] == "1990-05-15"
    assert stored["onboarded"] is True


def test_me_returns_the_profile(client):
    headers = auth(login(client))
    client.put("/auth/profile", json=PROFILE, headers=headers)

    me = client.get("/auth/me", headers=headers).json()

    assert me["name"] == "Ramu Gowda"
    assert me["user_code"] == "9810"
    assert "password_hash" not in me and "_id" not in me


def test_age_is_worked_out_from_the_date_of_birth():
    today = date(2026, 9, 30)

    assert compute_age(date(2000, 9, 30), today) == 26          # birthday today
    assert compute_age(date(2000, 10, 1), today) == 25          # birthday tomorrow
    assert compute_age(date(2000, 9, 29), today) == 26
    assert compute_age(date(1990, 1, 1), today) == 36


def test_age_in_the_profile_follows_the_birthday(client):
    headers = auth(login(client))
    today = date.today()

    tomorrow_birthday = date(today.year - 30, today.month, today.day)

    # Born exactly 30 years ago today: already 30
    body = {**PROFILE, "dob": tomorrow_birthday.isoformat()}
    assert client.put("/auth/profile", json=body, headers=headers).json()["age"] == 30


def test_profile_can_be_edited_later(client):
    headers = auth(login(client))
    client.put("/auth/profile", json=PROFILE, headers=headers)

    changed = {**PROFILE, "district": "Hassan", "role": "renter", "language": "hi"}
    user = client.put("/auth/profile", json=changed, headers=headers).json()

    assert (user["district"], user["role"], user["language"]) == ("Hassan", "renter", "hi")
    assert login(client).json()["user"]["district"] == "Hassan"


@pytest.mark.parametrize("change", [
    {"name": ""},
    {"name": "R"},
    {"name": "Ramu123"},
    {"name": "<script>alert(1)</script>"},
    {"dob": "2999-01-01"},                        # future
    {"dob": date.today().isoformat()},            # born today
    {"dob": f"{date.today().year - 10}-01-01"},   # too young
    {"dob": "1800-01-01"},                        # too old
    {"dob": "not-a-date"},
    {"state": "Atlantis"},
    {"state": ""},
    {"district": ""},
    {"district": "x"},
    {"language": "klingon"},
    {"role": "admin"},
])
def test_onboarding_rejects_bad_answers(client, change):
    headers = auth(login(client))

    response = client.put("/auth/profile", json={**PROFILE, **change}, headers=headers)

    assert response.status_code == 422
    assert client.get("/auth/me", headers=headers).json()["onboarded"] is False


def test_names_in_indian_scripts_are_accepted(client):
    headers = auth(login(client))

    for name in ("राम कुमार", "ರಾಮು ಗೌಡ", "రామయ్య", "Ramu K. Gowda", "O'Neil-Rao"):
        response = client.put("/auth/profile", json={**PROFILE, "name": name}, headers=headers)
        assert response.status_code == 200, name
        assert response.json()["name"] == name


def test_extra_spaces_in_answers_are_cleaned(client):
    headers = auth(login(client))

    user = client.put("/auth/profile", headers=headers, json={
        **PROFILE, "name": "  Ramu    Gowda ", "district": "  Mandya  "
    }).json()

    assert user["name"] == "Ramu Gowda"
    assert user["district"] == "Mandya"


def test_village_is_optional(client):
    headers = auth(login(client))
    body = {key: value for key, value in PROFILE.items() if key != "village"}

    assert client.put("/auth/profile", json=body, headers=headers).json()["village"] is None


# ---------------------------------------------------------------- the 4 digit id

def test_users_with_the_same_code_stay_separate_accounts(client):
    """
    9876543210 and 9811111110 both give code 9810. The code is a friendly
    id, not a key: they must NOT end up in one account.
    """

    a = login(client, "9876543210").json()["user"]
    b = login(client, "9811111110").json()["user"]

    assert a["user_code"] == b["user_code"] == "9810"
    assert a["id"] != b["id"]
    assert a["phone"] != b["phone"]

    client.put("/auth/profile", json=PROFILE, headers=auth(login(client, "9876543210")))

    other = login(client, "9811111110").json()
    assert other["onboarding_required"] is True              # untouched by the first user's data
    assert other["user"]["name"] == ""


# ---------------------------------------------------------------- existing accounts

def test_an_old_password_account_can_log_in_with_otp_and_keeps_its_id(client):
    database.get_database().users.insert_one({
        "id": 42, "name": "Old User", "phone": "9000000042",
        "role": "owner", "password_hash": "salt$hash",
    })

    body = login(client, "9000000042").json()

    assert body["user"]["id"] == 42
    assert body["user"]["role"] == "owner"
    assert body["is_new_user"] is False
    assert body["onboarding_required"] is True               # asked the new questions once
    assert "password_hash" not in body["user"]


# ---------------------------------------------------------------- sessions

def test_protected_routes_need_login(client):
    assert client.post("/rent-equipment", json={}).status_code == 401
    assert client.get("/rentals/1").status_code == 401
    assert client.get("/rentals").status_code == 401
    assert client.post("/verify-payment", json={}).status_code == 401
    assert client.get("/auth/me").status_code == 401
    assert client.put("/auth/profile", json=PROFILE).status_code == 401


def test_bad_token_rejected(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-token"})

    assert response.status_code == 401


def test_only_owner_can_add_equipment(client):
    renter = register(client, "Shiv Renter", "9000000002", "renter")

    response = client.post("/equipment", headers=renter["headers"], json={
        "equipment_name": "Plough", "price_per_day": 100,
        "location": "X", "contact_number": "1"
    })

    assert response.status_code == 403


def test_becoming_an_owner_in_the_profile_allows_listing_equipment(client):
    headers = auth(login(client))
    client.put("/auth/profile", json={**PROFILE, "role": "renter"}, headers=headers)

    listing = {"equipment_name": "Plough", "price_per_day": 100, "location": "X", "contact_number": "1"}

    assert client.post("/equipment", json=listing, headers=headers).status_code == 403

    client.put("/auth/profile", json={**PROFILE, "role": "owner"}, headers=headers)

    assert client.post("/equipment", json=listing, headers=headers).status_code == 200


# ---------------------------------------------------------------- old endpoints and the off switch

def test_password_endpoints_are_gone(client):
    assert client.post("/auth/register", json={}).status_code in (404, 405)
    assert client.post("/auth/login", json={}).status_code in (404, 405)


def test_fake_login_can_be_switched_off(client, monkeypatch):
    monkeypatch.setenv("FAKE_AUTH", "false")

    assert client.post("/auth/send-otp", json={"phone": "9876543210"}).status_code == 501
    assert login(client).status_code == 501
    assert client.get("/auth/regions").json()["fake_auth"] is False


def test_regions_for_the_onboarding_form(client):
    body = client.get("/auth/regions").json()

    assert "Karnataka" in body["states"] and "Tamil Nadu" in body["states"]
    assert len(body["states"]) == 36
    assert "Mysuru" in body["districts"]["Karnataka"]
    assert body["fake_auth"] is True
