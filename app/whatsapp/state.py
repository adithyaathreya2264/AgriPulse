"""
Conversation memory and abuse protection, stored in MongoDB.

  whatsapp_users     one document per phone: language, opt-in, daily digest
  whatsapp_sessions  what the bot is waiting for ("which crop?"), 30 minutes
  whatsapp_messages  message ids (duplicates) and a log for rate limiting
"""

from datetime import datetime, timedelta, timezone

from pymongo.errors import DuplicateKeyError

SESSION_MINUTES = 30

# More than this many messages within the window: the bot asks to slow down
RATE_LIMIT = 30
RATE_WINDOW_MINUTES = 10


def now():
    return datetime.now(timezone.utc)


def now_iso():
    return now().isoformat(timespec="seconds")


# ------------------------------------------------------------------
# Duplicates and rate limit
# ------------------------------------------------------------------

def record_message(db, sid, phone):
    """
    Returns "ok", "duplicate" (Twilio delivered the same message twice) or
    "rate_limited" (this phone is sending too much).
    """

    if sid and db.whatsapp_messages.find_one({"sid": sid}):
        return "duplicate"

    try:
        db.whatsapp_messages.insert_one({"sid": sid, "phone": phone, "at": now()})

    except DuplicateKeyError:
        return "duplicate"

    recent = db.whatsapp_messages.count_documents({
        "phone": phone,
        "at": {"$gte": now() - timedelta(minutes=RATE_WINDOW_MINUTES)}
    })

    return "rate_limited" if recent > RATE_LIMIT else "ok"


# ------------------------------------------------------------------
# Preferences per phone
# ------------------------------------------------------------------

def get_wa_user(db, phone):
    """(preferences, first_contact)"""

    user = db.whatsapp_users.find_one({"phone": phone})

    if user:
        return user, False

    user = {
        "phone": phone,
        "lang": None,
        "subscribed": True,            # proactive messages allowed
        "digest": False,               # daily morning message
        "digest_district": None,
        "first_seen": now_iso(),
    }

    db.whatsapp_users.insert_one(dict(user))

    return user, True


def update_wa_user(db, phone, **fields):
    db.whatsapp_users.update_one({"phone": phone}, {"$set": fields}, upsert=True)


def can_send_proactive(db, phone):
    """False after the farmer sent STOP."""

    user = db.whatsapp_users.find_one({"phone": phone})

    return not user or user.get("subscribed", True)


# ------------------------------------------------------------------
# Sessions
# ------------------------------------------------------------------

def get_session(db, phone):
    doc = db.whatsapp_sessions.find_one({"phone": phone})

    if doc and doc.get("state"):
        age = now() - datetime.fromisoformat(doc["updated_at"])

        if age <= timedelta(minutes=SESSION_MINUTES):
            return {"state": doc["state"], "data": doc.get("data", {})}

    return {"state": None, "data": {}}


def set_session(db, phone, state, data=None):
    db.whatsapp_sessions.update_one(
        {"phone": phone},
        {"$set": {"state": state, "data": data or {}, "updated_at": now_iso()}},
        upsert=True
    )


def clear_session(db, phone):
    db.whatsapp_sessions.delete_one({"phone": phone})


def set_state(ctx, state, **data):
    """Remember what the bot is waiting for. Keeps the data unless replaced."""

    merged = {**ctx.data, **data}

    set_session(ctx.db, ctx.phone, state, merged)
    ctx.session = {"state": state, "data": merged}


def end_flow(ctx):
    clear_session(ctx.db, ctx.phone)
    ctx.session = {"state": None, "data": {}}
