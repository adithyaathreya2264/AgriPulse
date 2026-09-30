import os

from dotenv import load_dotenv
from pymongo import MongoClient, ReturnDocument

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "agripulse")

_client = None


def get_client():
    """Create the MongoDB Atlas client on first use."""
    global _client

    if _client is None:
        if not MONGODB_URI:
            raise RuntimeError(
                "MONGODB_URI is missing. Add your MongoDB Atlas "
                "connection string to .env"
            )

        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)

    return _client


def get_database():
    return get_client()[MONGODB_DB]


def get_db():
    """FastAPI dependency."""
    return get_database()


def next_id(name):
    """
    Auto-increment integer id per collection.

    The frontend and API use integer ids (equipment id, rental id ...),
    so a counter collection keeps them working on MongoDB.
    """
    counter = get_database().counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )

    return counter["seq"]


def clean(doc):
    """Remove Mongo's internal _id so the document is JSON serializable."""
    if doc is None:
        return None

    doc.pop("_id", None)
    return doc


def init_indexes():
    db = get_database()

    db.users.create_index("phone", unique=True)
    db.equipment.create_index("id", unique=True)
    db.rentals.create_index("id", unique=True)
    db.rentals.create_index([("equipment_id", 1), ("start_at", 1)])
    db.equipment.create_index([("location_geo.lat", 1), ("location_geo.lng", 1)])
    db.rentals.create_index("razorpay_order_id")

    # One Razorpay payment can only ever confirm one rental
    db.rentals.create_index(
        "razorpay_payment_id",
        unique=True,
        partialFilterExpression={"razorpay_payment_id": {"$type": "string"}}
    )
    db.predictions.create_index("id", unique=True)

    db.price_history.create_index(
        [("crop", 1), ("district", 1), ("market", 1), ("date", 1)],
        unique=True
    )
    db.weather_history.create_index([("district", 1), ("date", 1)], unique=True)
    db.price_alerts.create_index("id", unique=True)
    db.price_alerts.create_index("user_id")
    db.notifications.create_index("id", unique=True)
    db.notifications.create_index("user_id")

    db.whatsapp_users.create_index("phone", unique=True)
    db.whatsapp_sessions.create_index("phone", unique=True)
    db.whatsapp_messages.create_index(
        "sid", unique=True, partialFilterExpression={"sid": {"$type": "string"}}
    )
    db.whatsapp_messages.create_index([("phone", 1), ("at", 1)])
    db.whatsapp_messages.create_index("at", expireAfterSeconds=2 * 24 * 3600)
    db.disease_feedback.create_index("id", unique=True)

    db.ui_translations.create_index([("lang", 1), ("hash", 1)], unique=True)
    db.tracker_keys.create_index("equipment_id", unique=True)
    db.tracker_keys.create_index("key_hash", unique=True)

    db.farmer_profiles.create_index("user_id", unique=True)
    db.loan_reports.create_index("id", unique=True)
    db.loan_reports.create_index("user_id")
