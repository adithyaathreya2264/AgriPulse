"""
Phone + OTP login (fake OTP, see app/services/auth_service.py) and the
first-time onboarding profile.

  POST /auth/send-otp    phone                  -> "OTP sent" (nothing is sent)
  POST /auth/verify-otp  phone + otp            -> token + profile
                         (creates the account the first time)
  GET  /auth/me                                 -> profile
  PUT  /auth/profile     onboarding questions   -> saves them (also for edits)
  GET  /auth/regions                            -> states and district hints
"""

import json
import os
import unicodedata
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.db.database import get_db, next_id
from app.services.auth_service import (
    FAKE_OTP,
    compute_age,
    create_token,
    fake_auth_enabled,
    get_current_user,
    normalize_phone,
    require_fake_auth,
    user_code
)
from app.services.translation_service import SUPPORTED_LANGUAGES

router = APIRouter()

MIN_AGE = 18
MAX_AGE = 110

_DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

with open(os.path.join(_DATA, "india_states.json"), encoding="utf-8") as f:
    STATES = json.load(f)

with open(os.path.join(_DATA, "karnataka_districts.json"), encoding="utf-8") as f:
    KARNATAKA_DISTRICTS = sorted({name.title() for name in json.load(f)})


def is_valid_name(name):
    """
    Letters of any Indian script (including vowel signs), spaces and . ' -
    Digits and symbols are rejected.
    """

    letters = 0

    for char in name:
        category = unicodedata.category(char)

        if char.isalpha():
            letters += 1

        elif category in ("Mn", "Mc") or char in " .'-":
            continue

        else:
            return False

    return letters >= 2 and name[0].isalpha()


# ============================================================
# REQUEST BODIES
# ============================================================

class SendOtpRequest(BaseModel):
    phone: str


class VerifyOtpRequest(BaseModel):
    phone: str
    otp: str


class ProfileRequest(BaseModel):
    name: str
    dob: date
    state: str
    district: str = Field(min_length=2, max_length=60)
    village: str | None = Field(default=None, max_length=60)
    language: str = "en"

    # owner: lists equipment for rent; renter: only rents / uses the app
    role: Literal["owner", "renter"] = "renter"

    @field_validator("name")
    @classmethod
    def check_name(cls, value):
        value = " ".join(value.split())

        if len(value) > 80 or not is_valid_name(value):
            raise ValueError("Enter your full name (letters only)")

        return value

    @field_validator("dob")
    @classmethod
    def check_dob(cls, value):
        if value >= date.today():
            raise ValueError("Date of birth must be in the past")

        age = compute_age(value)

        if age < MIN_AGE:
            raise ValueError(f"You must be at least {MIN_AGE} years old")

        if age > MAX_AGE:
            raise ValueError("Please check the date of birth")

        return value

    @field_validator("state")
    @classmethod
    def check_state(cls, value):
        if value not in STATES:
            raise ValueError("Choose a state from the list")

        return value

    @field_validator("district", "village")
    @classmethod
    def clean_place(cls, value):
        return " ".join(value.split()) if value else value

    @field_validator("language")
    @classmethod
    def check_language(cls, value):
        if value not in SUPPORTED_LANGUAGES:
            raise ValueError("Unsupported language")

        return value


# ============================================================
# HELPERS
# ============================================================

def public_user(user):
    """What the app may see about a user (never internal fields)."""

    dob = user.get("dob")

    return {
        "id": user["id"],
        "user_code": user.get("user_code") or user_code(user["phone"]),
        "phone": user["phone"],
        "name": user.get("name", ""),
        "role": user.get("role", "renter"),
        "onboarded": bool(user.get("onboarded")),
        "dob": dob,
        "age": compute_age(date.fromisoformat(dob)) if dob else None,
        "state": user.get("state"),
        "district": user.get("district"),
        "village": user.get("village"),
        "language": user.get("language", "en"),
    }


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ============================================================
# LOGIN
# ============================================================

@router.post("/auth/send-otp")
def send_otp(request: SendOtpRequest):
    require_fake_auth()

    phone = normalize_phone(request.phone)

    if not phone:
        raise HTTPException(
            status_code=422,
            detail="Enter a 10 digit mobile number"
        )

    # Demo: nothing is sent. The response says which OTP to type.
    return {
        "message": "OTP sent",
        "phone": phone,
        "demo": True,
        "demo_otp": FAKE_OTP,
    }


@router.post("/auth/verify-otp")
def verify_otp(request: VerifyOtpRequest, db=Depends(get_db)):
    require_fake_auth()

    phone = normalize_phone(request.phone)

    if not phone:
        raise HTTPException(
            status_code=422,
            detail="Enter a 10 digit mobile number"
        )

    if request.otp.strip() != FAKE_OTP:
        raise HTTPException(status_code=401, detail="Wrong OTP")

    user = db.users.find_one({"phone": phone})
    created = user is None

    if created:
        user = {
            "id": next_id("users"),
            "phone": phone,
            "user_code": user_code(phone),
            "name": "",
            "role": "renter",
            "onboarded": False,
            "created_at": now_iso(),
        }

        db.users.insert_one(user)

    db.users.update_one(
        {"id": user["id"]},
        {"$set": {"last_login_at": now_iso(), "user_code": user_code(phone)}}
    )

    user = db.users.find_one({"id": user["id"]})

    return {
        "token": create_token(user),
        "user": public_user(user),
        "is_new_user": created,
        "onboarding_required": not user.get("onboarded"),
    }


# ============================================================
# PROFILE / ONBOARDING
# ============================================================

@router.get("/auth/me")
def me(user=Depends(get_current_user)):
    return public_user(user)


@router.put("/auth/profile")
def save_profile(
    request: ProfileRequest,
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    """The onboarding questions. Also used to edit the profile later."""

    db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "name": request.name,
            "dob": request.dob.isoformat(),
            "state": request.state,
            "district": request.district,
            "village": request.village or None,
            "language": request.language,
            "role": request.role,
            "onboarded": True,
            "profile_updated_at": now_iso(),
        }}
    )

    return public_user(db.users.find_one({"id": user["id"]}))


@router.get("/auth/regions")
def regions():
    """States for the dropdown and district suggestions (Karnataka)."""

    return {
        "states": STATES,
        "districts": {"Karnataka": KARNATAKA_DISTRICTS},
        "fake_auth": fake_auth_enabled(),
    }
