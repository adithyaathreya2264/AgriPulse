import os
import re

from app.whatsapp.types import say

YES_WORDS = {"1", "yes", "y", "yeah", "yep", "ok", "okay", "correct", "right", "true", "👍", "✅"}
NO_WORDS = {"2", "no", "n", "nope", "wrong", "incorrect", "not right", "false", "👎", "❌"}


def as_number(text):
    """"3", "3.", "3)" -> 3, anything else -> None"""

    match = re.fullmatch(r"\s*(\d{1,3})\s*[.)]?\s*", text or "")

    return int(match.group(1)) if match else None


def yes_no(text):
    """True / False / None (neither)."""

    value = (text or "").strip().lower().strip("!. ")

    if value in YES_WORDS:
        return True

    if value in NO_WORDS:
        return False

    return None


def tidy_place(text):
    """"kolar" / "KOLAR" -> "Kolar"; a name typed with capitals is kept as typed."""

    text = " ".join((text or "").split())

    return text.title() if text == text.lower() or text == text.upper() else text


def app_link():
    """Where farmers can register / see more (the web app)."""

    return os.getenv("FRONTEND_URL", "").rstrip("/") or "the AgriPulse app"


def need_account():
    return say(
        "To use this you need an AgriPulse account with this phone number. "
        f"Register (it takes a minute) in {app_link()} and then message me again.",
    )


def money(value):
    try:
        return f"₹{float(value):,.0f}"
    except (TypeError, ValueError):
        return "-"
