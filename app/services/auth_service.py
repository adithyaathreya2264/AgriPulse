"""
Authentication.

FAKE PHONE + OTP LOGIN (demo only)
----------------------------------
The farmer types a 10 digit phone number and the OTP. No SMS is sent: the
OTP is the constant FAKE_OTP, so ANYONE who knows a phone number can log in
as that number. That is acceptable for a demo and unacceptable for real use.

  - FAKE_AUTH=false in .env switches the fake login off (the endpoints then
    answer 501 until a real SMS OTP provider is connected).
  - The server prints a warning at startup while fake login is on.

The "user code" is the first 2 + last 2 digits of the phone number. Many
phones share a code (only 10,000 exist), so it is a friendly id to show,
not a key: accounts are always looked up by the full phone number.

Sessions are JWTs (unchanged).
"""

import os
import re
from datetime import date, datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.database import get_db

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
TOKEN_HOURS = 24

FAKE_OTP = "123456"

bearer_scheme = HTTPBearer(auto_error=False)


# ============================================================
# FAKE OTP SETTINGS
# ============================================================

def fake_auth_enabled():
    return os.getenv("FAKE_AUTH", "true").strip().lower() != "false"


def require_fake_auth():
    if not fake_auth_enabled():
        raise HTTPException(
            status_code=501,
            detail="Phone login is not configured: connect a real SMS OTP provider"
        )


# ============================================================
# PHONE NUMBERS
# ============================================================

def normalize_phone(raw):
    """
    "98765 43210", "+91-98765-43210", "09876543210" -> "9876543210".
    Returns None unless the result is exactly 10 digits.
    """

    digits = re.sub(r"\D", "", str(raw or ""))

    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]

    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    return digits if len(digits) == 10 else None


def user_code(phone):
    """First 2 + last 2 digits of the phone number."""
    return phone[:2] + phone[-2:]


def compute_age(dob, today=None):
    today = today or date.today()

    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


# ============================================================
# TOKENS
# ============================================================

def _secret():
    if not JWT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="JWT_SECRET is not configured on the server"
        )

    return JWT_SECRET


def create_token(user):
    payload = {
        "sub": str(user["id"]),
        "role": user["role"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    }

    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_db)
):
    """FastAPI dependency: the logged in user, or 401."""

    if credentials is None:
        raise HTTPException(status_code=401, detail="Login required")

    try:
        payload = jwt.decode(
            credentials.credentials,
            _secret(),
            algorithms=[JWT_ALGORITHM]
        )
        user_id = int(payload["sub"])

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user = db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})

    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")

    return user


def require_owner(user=Depends(get_current_user)):
    if user["role"] != "owner":
        raise HTTPException(
            status_code=403,
            detail="Only equipment owners can do this"
        )

    return user
