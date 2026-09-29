import os
from datetime import date
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.equipment import Equipment
from app.models.rental import Rental
from app.services.payment_services import (create_payment_order, verify_payment)

load_dotenv()
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# ADD EQUIPMENT
# ============================================================

@router.post("/equipment")
def add_equipment(
    equipment_name: str,
    owner_name: str,
    price_per_day: float,
    location: str,
    contact_number: str,
    category: str = "Other",
    description: str = "",
    image_url: str = "",
    db: Session = Depends(get_db)
):
    if price_per_day <= 0:
        raise HTTPException(
            status_code=400,
            detail="Price per day must be greater than 0"
        )

    equipment = Equipment(
        equipment_name=equipment_name,
        owner_name=owner_name,
        price_per_day=price_per_day,
        location=location,
        contact_number=contact_number,
        category=category,
        description=description,
        image_url=image_url,
        availability="Available"
    )

    db.add(equipment)
    db.commit()
    db.refresh(equipment)

    return {
        "message": "Equipment added successfully",
        "id": equipment.id
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
    db: Session = Depends(get_db)
):
    query = db.query(Equipment)

    # Search
    if search:
        search_text = f"%{search.lower()}%"

        query = query.filter(
            (
                Equipment.equipment_name.ilike(search_text)
                | Equipment.category.ilike(search_text)
                | Equipment.owner_name.ilike(search_text)
                | Equipment.location.ilike(search_text)
            )
        )

    # Category filter
    if category:
        query = query.filter(
            Equipment.category.ilike(category)
        )

    # Location filter
    if location:
        query = query.filter(
            Equipment.location.ilike(f"%{location}%")
        )

    # Availability filter
    if availability:
        query = query.filter(
            Equipment.availability.ilike(availability)
        )

    equipment = query.order_by(
        Equipment.id.desc()
    ).all()

    return equipment


# ============================================================
# GET SINGLE EQUIPMENT
# ============================================================

@router.get("/equipment/{equipment_id}")
def get_equipment_details(
    equipment_id: int,
    db: Session = Depends(get_db)
):
    equipment = (
        db.query(Equipment)
        .filter(Equipment.id == equipment_id)
        .first()
    )

    if not equipment:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found"
        )

    return equipment


# ============================================================
# RENT EQUIPMENT
# ============================================================

@router.post("/rent-equipment")
def rent_equipment(
    equipment_id: int = Query(
        ...,
        description="ID of the equipment to rent"
    ),
    renter_name: str = Query(
        ...,
        description="Name of the renter"
    ),
    renter_phone: str = Query(
        ...,
        description="Phone number of the renter"
    ),
    start_date: date = Query(
        ...,
        description="Rental start date"
    ),
    end_date: date = Query(
        ...,
        description="Rental end date"
    ),
    db: Session = Depends(get_db)
):
    # --------------------------------------------------------
    # Validate dates
    # --------------------------------------------------------

    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail="End date cannot be before start date"
        )

    # --------------------------------------------------------
    # Find equipment
    # --------------------------------------------------------

    equipment = (
        db.query(Equipment)
        .filter(Equipment.id == equipment_id)
        .first()
    )

    if not equipment:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found"
        )

    if equipment.availability != "Available":
        raise HTTPException(
            status_code=400,
            detail="Equipment is not currently available"
        )

    # --------------------------------------------------------
    # Check for conflicting rental
    # --------------------------------------------------------

    conflicting_rental = (
        db.query(Rental)
        .filter(
            Rental.equipment_id == equipment_id,
            Rental.status.in_(["Pending", "Confirmed", "Active"]),
            Rental.start_date <= end_date,
            Rental.end_date >= start_date
        )
        .first()
    )

    if conflicting_rental:
        raise HTTPException(
            status_code=400,
            detail="Equipment is already booked for the selected dates"
        )

    # --------------------------------------------------------
    # Calculate rental days
    # --------------------------------------------------------

    rental_days = (
        end_date - start_date
    ).days + 1

    total_amount = (
        rental_days * equipment.price_per_day
    )

    # --------------------------------------------------------
    # Create rental
    # --------------------------------------------------------

    rental = Rental(
        equipment_id=equipment_id,
        renter_name=renter_name,
        renter_phone=renter_phone,
        start_date=start_date,
        end_date=end_date,
        total_amount=total_amount,
        status="Pending",
        payment_status="Pending"
    )

    db.add(rental)

    # Do NOT mark equipment as permanently rented here.
    #
    # Payment confirmation will later change the booking status.
    #
    # This is important because an equipment owner should be
    # able to receive bookings for different dates.

    db.commit()
    db.refresh(rental)

    return {
        "message": "Rental request created successfully",
        "rental_id": rental.id,
        "equipment_id": equipment.id,
        "equipment_name": equipment.equipment_name,
        "start_date": start_date,
        "end_date": end_date,
        "rental_days": rental_days,
        "price_per_day": equipment.price_per_day,
        "total_amount": total_amount,
        "status": rental.status,
        "payment_status": rental.payment_status
    }


# ============================================================
# GET RENTAL DETAILS
# ============================================================

@router.get("/rentals/{rental_id}")
def get_rental(
    rental_id: int,
    db: Session = Depends(get_db)
):
    rental = (
        db.query(Rental)
        .filter(Rental.id == rental_id)
        .first()
    )

    if not rental:
        raise HTTPException(
            status_code=404,
            detail="Rental not found"
        )

    return rental

# ============================================================
# CREATE RAZORPAY PAYMENT ORDER
# ============================================================

@router.post("/create-payment-order")
def create_rental_payment_order(
    rental_id: int = Query(...),
    db: Session = Depends(get_db)
):
    rental = (
        db.query(Rental)
        .filter(Rental.id == rental_id)
        .first()
    )

    if not rental:
        raise HTTPException(
            status_code=404,
            detail="Rental not found"
        )

    if rental.payment_status == "Paid":
        raise HTTPException(
            status_code=400,
            detail="Rental has already been paid"
        )

    if not rental.total_amount or rental.total_amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid rental amount"
        )

    try:
        order = create_payment_order(
            rental.total_amount,
            rental.id
        )

        return {
            "message": "Payment order created successfully",
            "rental_id": rental.id,
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key_id": RAZORPAY_KEY_ID
        }

    except Exception as e:
        print("Razorpay order creation error:", e)

        raise HTTPException(
            status_code=500,
            detail="Unable to create payment order"
        )
    # ============================================================
# VERIFY RAZORPAY PAYMENT
# ============================================================

@router.post("/verify-payment")
def verify_rental_payment(
    rental_id: int = Query(...),
    razorpay_order_id: str = Query(...),
    razorpay_payment_id: str = Query(...),
    razorpay_signature: str = Query(...),
    db: Session = Depends(get_db)
):
    rental = (
        db.query(Rental)
        .filter(Rental.id == rental_id)
        .first()
    )

    if not rental:
        raise HTTPException(
            status_code=404,
            detail="Rental not found"
        )

    try:
        verify_payment(
            razorpay_order_id,
            razorpay_payment_id,
            razorpay_signature
        )

        rental.payment_status = "Paid"
        rental.status = "Confirmed"

        db.commit()
        db.refresh(rental)

        return {
            "message": "Payment verified successfully",
            "rental_id": rental.id,
            "payment_status": rental.payment_status,
            "status": rental.status
        }

    except Exception as e:
        print("Payment verification error:", e)

        raise HTTPException(
            status_code=400,
            detail="Payment verification failed"
        )