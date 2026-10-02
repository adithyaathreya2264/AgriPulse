import asyncio
from datetime import date, datetime, time, timedelta, timezone

from app.db.database import get_database

# Equipment can only be booked starting this many days from today
MIN_LEAD_DAYS = 2

# Statuses that block the equipment for the booked dates
BLOCKING_STATUSES = ["Confirmed", "Active"]


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def pending_expiry_iso(start_at):
    """An unpaid booking is held until its start time (local wall-clock, like all rental times)."""
    # a naive datetime is read as server-local time
    start = datetime.fromisoformat(start_at).astimezone(timezone.utc)

    return start.isoformat(timespec="seconds")


def earliest_start_date():
    return date.today() + timedelta(days=MIN_LEAD_DAYS)


def local_now_iso():
    """Rental times are local wall-clock times (no timezone)."""
    return datetime.now().isoformat(timespec="seconds")


def day_interval(start_date, end_date):
    """
    A whole-day rental as a time interval:
    start day 00:00 -> the morning after the end day.
    """
    start = datetime.combine(start_date, time.min)
    end = datetime.combine(end_date + timedelta(days=1), time.min)

    return (
        start.isoformat(timespec="seconds"),
        end.isoformat(timespec="seconds")
    )


def blocking_filter():
    """Rentals that currently block the equipment (unexpired Pending too)."""
    return {
        "$or": [
            {"status": {"$in": BLOCKING_STATUSES}},
            {"status": "Pending", "expires_at": {"$gt": now_iso()}}
        ]
    }


def overlap_filter(equipment_id, start_at, end_at, exclude_rental_id=None):
    """
    Blocking rentals of one equipment that overlap [start_at, end_at).
    Back-to-back bookings (one ends when the next starts) are allowed.
    Day and hourly rentals share this one check.
    """

    conditions = {
        "equipment_id": equipment_id,
        "start_at": {"$lt": end_at},
        "end_at": {"$gt": start_at}
    }

    if exclude_rental_id is not None:
        conditions["id"] = {"$ne": exclude_rental_id}

    return {"$and": [conditions, blocking_filter()]}


def run_lifecycle(db=None):
    """
    Automatic rental status transitions:

      Pending (unpaid, expired)        -> Expired
      Confirmed (start time reached)   -> Active
      Confirmed / Active (end passed)  -> Completed
    """

    db = db if db is not None else get_database()

    now_local = local_now_iso()

    expired = db.rentals.update_many(
        {"status": "Pending", "expires_at": {"$lte": now_iso()}},
        {"$set": {"status": "Expired"}}
    ).modified_count

    completed = db.rentals.update_many(
        {"status": {"$in": ["Confirmed", "Active"]}, "end_at": {"$lte": now_local}},
        {"$set": {"status": "Completed"}}
    ).modified_count

    activated = db.rentals.update_many(
        {"status": "Confirmed", "start_at": {"$lte": now_local}},
        {"$set": {"status": "Active"}}
    ).modified_count

    return {
        "expired": expired,
        "completed": completed,
        "activated": activated
    }


def migrate_rentals(db=None):
    """Give rentals created before hourly booking a start_at / end_at."""

    db = db if db is not None else get_database()

    for rental in db.rentals.find({"start_at": {"$exists": False}}):
        if not rental.get("start_date") or not rental.get("end_date"):
            continue

        start_at, end_at = day_interval(
            date.fromisoformat(rental["start_date"]),
            date.fromisoformat(rental["end_date"])
        )

        db.rentals.update_one(
            {"id": rental["id"]},
            {"$set": {
                "start_at": start_at,
                "end_at": end_at,
                "booking_type": "day"
            }}
        )


async def lifecycle_loop(interval_seconds=600):
    """Background task started by the FastAPI lifespan."""

    while True:
        try:
            result = await asyncio.to_thread(run_lifecycle)

            if any(result.values()):
                print("Rental lifecycle:", result)

        except asyncio.CancelledError:
            raise

        except Exception as e:
            print("Rental lifecycle error:", e)

        await asyncio.sleep(interval_seconds)
