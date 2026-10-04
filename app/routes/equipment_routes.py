import hashlib
import json
import math
import os
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field, model_validator
from pymongo.errors import DuplicateKeyError

from app.db.database import get_db, next_id, clean
from app.services.auth_service import get_current_user, require_owner
from app.services.payment_services import (
    RAZORPAY_KEY_ID,
    PaymentConfigError,
    create_payment_order,
    fetch_payment,
    get_client,
    verify_payment,
    verify_webhook
)
from app.services.geo import bounding_box, within_radius
from app.services.rental_lifecycle import (
    blocking_filter,
    day_interval,
    now_iso,
    overlap_filter,
    pending_expiry_iso,
    earliest_start_date,
    MIN_LEAD_DAYS
)

DEFAULT_RADIUS_KM = 10

LEAD_TIME_MESSAGE = f"Bookings must start at least {MIN_LEAD_DAYS} days from today"
MAX_RADIUS_KM = 200

# An hourly booking longer than this should be booked by the day
MAX_HOURLY_BOOKING_HOURS = 24

router = APIRouter()


# ============================================================
# REQUEST BODIES
# ============================================================

class EquipmentRequest(BaseModel):
    equipment_name: str = Field(min_length=1)
    price_per_day: float = Field(gt=0)
    price_per_hour: float | None = Field(default=None, gt=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location: str = Field(min_length=1)
    contact_number: str = Field(min_length=1)
    owner_name: str | None = None
    category: str = "Other"
    description: str = ""
    image_url: str = ""


class LocationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0, le=100000)


class AvailabilityRequest(BaseModel):
    availability: Literal["Available", "Unavailable"]


class RentalRequest(BaseModel):
    equipment_id: int
    booking_type: Literal["day", "hour"] = "day"

    # Whole-day booking
    start_date: date | None = None
    end_date: date | None = None

    # Hourly booking (local wall-clock time)
    start_at: datetime | None = None
    end_at: datetime | None = None

    renter_name: str | None = None
    renter_phone: str | None = None

    @model_validator(mode="after")
    def check_fields(self):
        if self.booking_type == "day":
            if not self.start_date or not self.end_date:
                raise ValueError("start_date and end_date are required")
        else:
            if not self.start_at or not self.end_at:
                raise ValueError("start_at and end_at are required")

        return self


class PaymentOrderRequest(BaseModel):
    rental_id: int


class VerifyPaymentRequest(BaseModel):
    rental_id: int
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ============================================================
# HELPERS
# ============================================================

def paise(amount):
    return int(round(amount * 100))


# A position newer than this is shown as "live"
LIVE_MINUTES = 5

# A tracker device may report at most this often
TRACKER_MIN_INTERVAL_SECONDS = 5


def add_live_flag(item):
    """`location_live`: the equipment reported its GPS position recently."""

    updated = item.get("location_updated_at")
    live = False

    if updated:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(updated)
        live = age <= timedelta(minutes=LIVE_MINUTES)

    item["location_live"] = live

    return item


def hash_tracker_key(key):
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def store_location(db, equipment_id, latitude, longitude, accuracy_m, source):
    db.equipment.update_one(
        {"id": equipment_id},
        {"$set": {
            "location_geo": {"lat": latitude, "lng": longitude},
            "location_updated_at": now_iso(),
            "location_accuracy_m": accuracy_m,
            "location_source": source
        }}
    )


def get_rental_for_user(db, rental_id, user):
    """The rental, only for its renter or the equipment owner."""

    rental = db.rentals.find_one({"id": rental_id})

    if not rental:
        raise HTTPException(status_code=404, detail="Rental not found")

    if user["id"] not in (rental.get("renter_id"), rental.get("owner_id")):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this rental"
        )

    return rental


def confirm_payment(db, rental, order_id, payment_id):
    """
    Mark a rental as paid. Safe to call repeatedly (verify-payment and
    the webhook can both arrive): the update only matches once.

    Returns "confirmed", "already" or "conflict".
    """

    if rental.get("payment_status") == "Paid":
        return "already"

    # A payment that arrives after the booking expired is only accepted
    # if nobody else has booked the dates in the meantime.
    if rental["status"] == "Expired":
        conflict = db.rentals.find_one(
            overlap_filter(
                rental["equipment_id"],
                rental["start_at"],
                rental["end_at"],
                exclude_rental_id=rental["id"]
            )
        )

        if conflict:
            db.rentals.update_one(
                {"id": rental["id"], "payment_status": {"$ne": "Paid"}},
                {"$set": {
                    "status": "Refund Required",
                    "payment_status": "Paid",
                    "razorpay_payment_id": payment_id
                }}
            )
            return "conflict"

    try:
        result = db.rentals.update_one(
            {
                "id": rental["id"],
                "razorpay_order_id": order_id,
                "payment_status": {"$ne": "Paid"},
                "status": {"$in": ["Pending", "Expired"]}
            },
            {
                "$set": {
                    "payment_status": "Paid",
                    "status": "Confirmed",
                    "razorpay_payment_id": payment_id,
                    "paid_at": now_iso()
                },
                "$unset": {"expires_at": ""}
            }
        )
    except DuplicateKeyError:
        # This Razorpay payment is already attached to another rental
        return "conflict"

    return "confirmed" if result.modified_count == 1 else "already"


# ============================================================
# ADD EQUIPMENT (owners only)
# ============================================================

@router.post("/equipment")
def add_equipment(
    request: EquipmentRequest,
    user=Depends(require_owner),
    db=Depends(get_db)
):
    equipment = {
        "id": next_id("equipment"),
        "equipment_name": request.equipment_name,
        "category": request.category,
        "description": request.description,
        "owner_id": user["id"],
        "owner_name": request.owner_name or user["name"],
        "contact_number": request.contact_number,
        "location": request.location,
        "price_per_day": request.price_per_day,
        "price_per_hour": request.price_per_hour,
        "image_url": request.image_url,
        "availability": "Available",
        "location_geo": None,
        "location_updated_at": None
    }

    if request.latitude is not None and request.longitude is not None:
        equipment["location_geo"] = {
            "lat": request.latitude,
            "lng": request.longitude
        }
        equipment["location_updated_at"] = now_iso()

    db.equipment.insert_one(equipment)

    return {
        "message": "Equipment added successfully",
        "id": equipment["id"]
    }


# ============================================================
# GET ALL EQUIPMENT
# ============================================================

@router.get("/equipment")
def get_equipment(
    search: str = Query(
        None,
        description="Search equipment name, category, owner or location"
    ),
    category: str = Query(
        None,
        description="Filter by equipment category"
    ),
    location: str = Query(
        None,
        description="Filter by location"
    ),
    availability: str = Query(
        None,
        description="Filter by availability"
    ),
    lat: float = Query(
        None, ge=-90, le=90,
        description="Your latitude (enables the nearby search)"
    ),
    lng: float = Query(
        None, ge=-180, le=180,
        description="Your longitude (enables the nearby search)"
    ),
    radius_km: float = Query(
        DEFAULT_RADIUS_KM, gt=0, le=MAX_RADIUS_KM,
        description="Search radius in km (default 10)"
    ),
    db=Depends(get_db)
):
    if (lat is None) != (lng is None):
        raise HTTPException(
            status_code=400,
            detail="Send both lat and lng for a nearby search"
        )

    def contains(text):
        return {"$regex": re.escape(text), "$options": "i"}

    query = {}

    # Search
    if search:
        query["$or"] = [
            {"equipment_name": contains(search)},
            {"category": contains(search)},
            {"owner_name": contains(search)},
            {"location": contains(search)}
        ]

    # Category filter
    if category:
        query["category"] = {
            "$regex": f"^{re.escape(category)}$",
            "$options": "i"
        }

    # Location filter
    if location:
        query["location"] = contains(location)

    # Availability filter
    if availability:
        query["availability"] = {
            "$regex": f"^{re.escape(availability)}$",
            "$options": "i"
        }

    # Nearby search: cheap bounding box in the database, exact distance after
    if lat is not None:
        min_lat, max_lat, min_lng, max_lng = bounding_box(lat, lng, radius_km)

        query["location_geo.lat"] = {"$gte": min_lat, "$lte": max_lat}
        query["location_geo.lng"] = {"$gte": min_lng, "$lte": max_lng}

        items = [add_live_flag(clean(item)) for item in db.equipment.find(query)]

        return within_radius(items, lat, lng, radius_km)

    return [
        add_live_flag(clean(item))
        for item in db.equipment.find(query).sort("id", -1)
    ]


# ============================================================
# OWNER: UPDATE LIVE LOCATION / AVAILABILITY
# ============================================================

def get_own_equipment(db, equipment_id, user):
    equipment = db.equipment.find_one({"id": equipment_id})

    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    if equipment.get("owner_id") != user["id"]:
        raise HTTPException(
            status_code=403,
            detail="Only the owner can change this equipment"
        )

    return equipment


@router.patch("/equipment/{equipment_id}/location")
def update_equipment_location(
    equipment_id: int,
    request: LocationRequest,
    user=Depends(require_owner),
    db=Depends(get_db)
):
    """
    GPS tracking from the owner's phone: the app sends the phone's position
    while the owner shares it (see also the tracker key for GPS devices).
    """

    get_own_equipment(db, equipment_id, user)

    store_location(
        db, equipment_id, request.latitude, request.longitude,
        request.accuracy_m, "phone"
    )

    return {"message": "Location updated", "id": equipment_id}


@router.post("/equipment/{equipment_id}/tracker-key")
def create_tracker_key(
    equipment_id: int,
    user=Depends(require_owner),
    db=Depends(get_db)
):
    """
    Key for a GPS tracker fitted to the equipment (GSM / ESP32 / OBD tracker).
    The device posts its position to /tracker/update with this key, so it
    keeps reporting with the phone off. Shown ONCE; a new key replaces the
    old one.
    """

    get_own_equipment(db, equipment_id, user)

    key = "trk_" + secrets.token_urlsafe(32)

    db.tracker_keys.update_one(
        {"equipment_id": equipment_id},
        {"$set": {
            "equipment_id": equipment_id,
            "key_hash": hash_tracker_key(key),
            "created_at": now_iso(),
            "last_used_at": None
        }},
        upsert=True
    )

    return {
        "tracker_key": key,
        "equipment_id": equipment_id,
        "endpoint": "/tracker/update",
        "note": "Save this key now. It is not shown again."
    }


@router.delete("/equipment/{equipment_id}/tracker-key")
def delete_tracker_key(
    equipment_id: int,
    user=Depends(require_owner),
    db=Depends(get_db)
):
    get_own_equipment(db, equipment_id, user)

    db.tracker_keys.delete_one({"equipment_id": equipment_id})

    return {"message": "Tracker key revoked"}


@router.post("/tracker/update")
def tracker_update(
    request: LocationRequest,
    x_tracker_key: str = Header(default=""),
    db=Depends(get_db)
):
    """
    Position report from a GPS tracker device. Authenticated by the
    tracker key (header X-Tracker-Key), no login needed.
    """

    record = (
        db.tracker_keys.find_one({"key_hash": hash_tracker_key(x_tracker_key)})
        if x_tracker_key else None
    )

    if not record:
        raise HTTPException(status_code=401, detail="Invalid tracker key")

    last = record.get("last_used_at")

    if last and (
        datetime.now(timezone.utc) - datetime.fromisoformat(last)
    ).total_seconds() < TRACKER_MIN_INTERVAL_SECONDS:
        raise HTTPException(
            status_code=429,
            detail=f"Report at most once every {TRACKER_MIN_INTERVAL_SECONDS} seconds"
        )

    db.tracker_keys.update_one(
        {"_id": record["_id"]}, {"$set": {"last_used_at": now_iso()}}
    )

    store_location(
        db, record["equipment_id"], request.latitude, request.longitude,
        request.accuracy_m, "tracker"
    )

    return {"message": "Location updated"}


@router.patch("/equipment/{equipment_id}/availability")
def update_equipment_availability(
    equipment_id: int,
    request: AvailabilityRequest,
    user=Depends(require_owner),
    db=Depends(get_db)
):
    get_own_equipment(db, equipment_id, user)

    db.equipment.update_one(
        {"id": equipment_id},
        {"$set": {"availability": request.availability}}
    )

    return {"message": "Availability updated", "availability": request.availability}


@router.delete("/equipment/{equipment_id}")
def delete_equipment(
    equipment_id: int,
    user=Depends(require_owner),
    db=Depends(get_db)
):
    get_own_equipment(db, equipment_id, user)

    # Paid / running bookings and unexpired held bookings must not lose their machine
    if db.rentals.find_one({"equipment_id": equipment_id, **blocking_filter()}):
        raise HTTPException(
            status_code=400,
            detail="This equipment has active bookings and cannot be deleted"
        )

    db.equipment.delete_one({"id": equipment_id})
    db.tracker_keys.delete_many({"equipment_id": equipment_id})

    return {"message": "Equipment deleted"}


@router.get("/equipment/{equipment_id}/bookings")
def get_equipment_bookings(
    equipment_id: int,
    db=Depends(get_db)
):
    """Booked time slots (for the availability calendar). No renter details."""

    if not db.equipment.find_one({"id": equipment_id}):
        raise HTTPException(status_code=404, detail="Equipment not found")

    rentals = db.rentals.find({
        "$and": [
            {"equipment_id": equipment_id, "end_at": {"$gt": datetime.now().isoformat(timespec="seconds")}},
            blocking_filter()
        ]
    }).sort("start_at", 1)

    return [
        {
            "start_at": rental["start_at"],
            "end_at": rental["end_at"],
            "booking_type": rental.get("booking_type", "day"),
            "status": rental["status"]
        }
        for rental in rentals
    ]


# ============================================================
# GET SINGLE EQUIPMENT
# ============================================================

@router.get("/equipment/{equipment_id}")
def get_equipment_details(
    equipment_id: int,
    db=Depends(get_db)
):
    equipment = db.equipment.find_one({"id": equipment_id})

    if not equipment:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found"
        )

    return add_live_flag(clean(equipment))


# ============================================================
# RENT EQUIPMENT
# ============================================================

@router.post("/rent-equipment")
def rent_equipment(
    request: RentalRequest,
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    # --------------------------------------------------------
    # Find equipment
    # --------------------------------------------------------

    equipment = db.equipment.find_one({"id": request.equipment_id})

    if not equipment:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found"
        )

    if equipment["availability"] != "Available":
        raise HTTPException(
            status_code=400,
            detail="Equipment is not currently available"
        )

    if equipment.get("owner_id") == user["id"]:
        raise HTTPException(
            status_code=400,
            detail="You cannot rent your own equipment"
        )

    # --------------------------------------------------------
    # Work out the booked interval and the price
    # --------------------------------------------------------

    hours = None
    rental_days = None

    if request.booking_type == "day":
        start_date = request.start_date
        end_date = request.end_date

        if end_date < start_date:
            raise HTTPException(
                status_code=400,
                detail="End date cannot be before start date"
            )

        if start_date < date.today():
            raise HTTPException(
                status_code=400,
                detail="Start date cannot be in the past"
            )

        if start_date < earliest_start_date():
            raise HTTPException(
                status_code=400,
                detail=LEAD_TIME_MESSAGE
            )

        start_at, end_at = day_interval(start_date, end_date)

        rental_days = (end_date - start_date).days + 1
        total_amount = rental_days * equipment["price_per_day"]

    else:
        if not equipment.get("price_per_hour"):
            raise HTTPException(
                status_code=400,
                detail="This equipment cannot be rented by the hour"
            )

        start = request.start_at.replace(tzinfo=None, second=0, microsecond=0)
        end = request.end_at.replace(tzinfo=None, second=0, microsecond=0)

        if end <= start:
            raise HTTPException(
                status_code=400,
                detail="End time must be after start time"
            )

        if start < datetime.now() - timedelta(minutes=5):
            raise HTTPException(
                status_code=400,
                detail="Start time cannot be in the past"
            )

        if start.date() < earliest_start_date():
            raise HTTPException(
                status_code=400,
                detail=LEAD_TIME_MESSAGE
            )

        hours = math.ceil((end - start).total_seconds() / 3600)

        if hours > MAX_HOURLY_BOOKING_HOURS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Hourly bookings can be at most {MAX_HOURLY_BOOKING_HOURS} "
                    "hours. Please book by the day."
                )
            )

        start_at = start.isoformat(timespec="seconds")
        end_at = end.isoformat(timespec="seconds")

        total_amount = hours * equipment["price_per_hour"]

    # --------------------------------------------------------
    # Check for conflicting rental (day and hourly share this check).
    # Unpaid bookings only block the time until they expire.
    # --------------------------------------------------------

    if db.rentals.find_one(
        overlap_filter(request.equipment_id, start_at, end_at)
    ):
        raise HTTPException(
            status_code=400,
            detail="Equipment is already booked for the selected time"
        )

    # --------------------------------------------------------
    # Create rental
    #
    # Equipment is NOT marked as permanently rented: an owner can
    # receive bookings for different times.
    # --------------------------------------------------------

    rental = {
        "id": next_id("rentals"),
        "equipment_id": request.equipment_id,
        "owner_id": equipment.get("owner_id"),
        "renter_id": user["id"],
        "renter_name": request.renter_name or user["name"],
        "renter_phone": request.renter_phone or user["phone"],
        "booking_type": request.booking_type,
        "start_at": start_at,
        "end_at": end_at,
        "start_date": start_at[:10],
        "end_date": (
            (datetime.fromisoformat(end_at) - timedelta(seconds=1)).date().isoformat()
        ),
        "hours": hours,
        "total_amount": total_amount,
        "status": "Pending",
        "payment_status": "Pending",
        "expires_at": pending_expiry_iso(start_at),
        "razorpay_order_id": None
    }

    db.rentals.insert_one(rental)

    return {
        "message": "Rental request created successfully",
        "rental_id": rental["id"],
        "equipment_id": equipment["id"],
        "equipment_name": equipment["equipment_name"],
        "booking_type": request.booking_type,
        "start_date": rental["start_date"],
        "end_date": rental["end_date"],
        "start_at": start_at,
        "end_at": end_at,
        "rental_days": rental_days,
        "hours": hours,
        "price_per_day": equipment["price_per_day"],
        "price_per_hour": equipment.get("price_per_hour"),
        "total_amount": total_amount,
        "status": rental["status"],
        "payment_status": rental["payment_status"],
        "expires_at": rental["expires_at"]
    }


# ============================================================
# MY RENTALS (as renter or as equipment owner)
# ============================================================

@router.get("/rentals")
def get_my_rentals(
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    rentals = db.rentals.find({
        "$or": [
            {"renter_id": user["id"]},
            {"owner_id": user["id"]}
        ]
    }).sort("id", -1)

    return [clean(rental) for rental in rentals]


# ============================================================
# GET RENTAL DETAILS
# ============================================================

@router.get("/rentals/{rental_id}")
def get_rental(
    rental_id: int,
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    return clean(get_rental_for_user(db, rental_id, user))


# ============================================================
# CREATE RAZORPAY PAYMENT ORDER
# ============================================================

@router.post("/create-payment-order")
def create_rental_payment_order(
    request: PaymentOrderRequest,
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    rental = get_rental_for_user(db, request.rental_id, user)

    if rental.get("renter_id") != user["id"]:
        raise HTTPException(
            status_code=403,
            detail="Only the renter can pay for this rental"
        )

    if rental["payment_status"] == "Paid":
        raise HTTPException(
            status_code=400,
            detail="Rental has already been paid"
        )

    if rental["status"] != "Pending" or rental.get("expires_at", "") <= now_iso():
        raise HTTPException(
            status_code=400,
            detail="This booking has expired. Please create a new rental."
        )

    if not rental.get("total_amount") or rental["total_amount"] <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid rental amount"
        )

    # Reuse the open order instead of creating a new one every click
    order_id = rental.get("razorpay_order_id")

    if not order_id:
        try:
            order = create_payment_order(
                rental["total_amount"],
                rental["id"]
            )

        except PaymentConfigError as e:
            raise HTTPException(status_code=503, detail=str(e))

        except Exception as e:
            print("Razorpay order creation error:", e)

            raise HTTPException(
                status_code=502,
                detail="Unable to create payment order"
            )

        order_id = order["id"]

        db.rentals.update_one(
            {"id": rental["id"]},
            {"$set": {"razorpay_order_id": order_id}}
        )

    return {
        "message": "Payment order created successfully",
        "rental_id": rental["id"],
        "order_id": order_id,
        "amount": paise(rental["total_amount"]),
        "currency": "INR",
        "key_id": RAZORPAY_KEY_ID,
        "upi_preferred": True,
        "upi_only": os.getenv("RAZORPAY_UPI_ONLY", "false").lower() == "true"
    }


# ============================================================
# VERIFY RAZORPAY PAYMENT
# ============================================================

@router.post("/verify-payment")
def verify_rental_payment(
    request: VerifyPaymentRequest,
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    rental = get_rental_for_user(db, request.rental_id, user)

    # Already confirmed with this same payment (double click / retry)
    if (
        rental["payment_status"] == "Paid"
        and rental.get("razorpay_payment_id") == request.razorpay_payment_id
    ):
        return {
            "message": "Payment already verified",
            "rental_id": rental["id"],
            "payment_status": rental["payment_status"],
            "status": rental["status"]
        }

    if rental["payment_status"] == "Paid":
        raise HTTPException(
            status_code=409,
            detail="Rental has already been paid"
        )

    # The order must be the one created for THIS rental
    if (
        not rental.get("razorpay_order_id")
        or rental["razorpay_order_id"] != request.razorpay_order_id
    ):
        raise HTTPException(
            status_code=400,
            detail="Payment order does not belong to this rental"
        )

    try:
        # 1. Signature: the response really came from Razorpay
        verify_payment(
            request.razorpay_order_id,
            request.razorpay_payment_id,
            request.razorpay_signature
        )

        # 2. Ask Razorpay directly for the payment state
        payment = fetch_payment(request.razorpay_payment_id)

        # Orders may be set to authorize only: capture it now
        if payment.get("status") == "authorized":
            payment = get_client().payment.capture(
                request.razorpay_payment_id,
                paise(rental["total_amount"])
            )

    except PaymentConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))

    except Exception as e:
        print("Payment verification error:", e)

        raise HTTPException(
            status_code=400,
            detail="Payment verification failed"
        )

    if (
        payment.get("status") != "captured"
        or payment.get("order_id") != rental["razorpay_order_id"]
        or payment.get("amount") != paise(rental["total_amount"])
    ):
        raise HTTPException(
            status_code=400,
            detail="Payment was not completed for this rental amount"
        )

    outcome = confirm_payment(
        db,
        rental,
        request.razorpay_order_id,
        request.razorpay_payment_id
    )

    if outcome == "conflict":
        raise HTTPException(
            status_code=409,
            detail=(
                "Payment received, but the booking expired and the dates "
                "were taken. A refund will be issued."
            )
        )

    rental = db.rentals.find_one({"id": rental["id"]})

    return {
        "message": "Payment verified successfully",
        "rental_id": rental["id"],
        "payment_status": rental["payment_status"],
        "status": rental["status"]
    }


# ============================================================
# RAZORPAY WEBHOOK
#
# Razorpay calls this even if the browser is closed after paying.
# Configure it in the Razorpay dashboard (events: payment.captured,
# payment.failed) with the same secret as RAZORPAY_WEBHOOK_SECRET.
# ============================================================

@router.post("/razorpay-webhook")
async def razorpay_webhook(request: Request, db=Depends(get_db)):
    body = (await request.body()).decode("utf-8")
    signature = request.headers.get("X-Razorpay-Signature", "")

    try:
        verify_webhook(body, signature)

    except PaymentConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))

    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event = json.loads(body)
    event_name = event.get("event")

    payment = (
        event.get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )

    order_id = payment.get("order_id")

    rental = (
        db.rentals.find_one({"razorpay_order_id": order_id})
        if order_id else None
    )

    if not rental:
        return {"status": "ignored"}

    if event_name == "payment.captured":
        if payment.get("amount") == paise(rental["total_amount"]):
            confirm_payment(db, rental, order_id, payment.get("id"))

    elif event_name == "payment.failed":
        db.rentals.update_one(
            {"id": rental["id"], "payment_status": {"$ne": "Paid"}},
            {"$set": {
                "last_payment_error": (
                    payment.get("error_description") or "Payment failed"
                )
            }}
        )

    return {"status": "ok"}
