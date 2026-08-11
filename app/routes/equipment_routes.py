from fastapi import APIRouter, Depends
from fastapi import Query
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.equipment import Equipment
from app.models.rental import Rental

router=APIRouter()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/equipment")
def add_equipment(
    equipment_name: str,
    owner_name: str,
    price_per_day: float,
    location: str,
    contact_number: str,
    db: Session = Depends(get_db)
):
    equipment = Equipment(
        equipment_name=equipment_name,
        owner_name=owner_name,
        price_per_day=price_per_day,
        location=location,
        contact_number=contact_number
    )
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return {"message": "Equipment added successfully", "id": equipment.id}

@router.get("/equipment")
def get_equipment(db: Session = Depends(get_db)):
    equipment = db.query(Equipment).all()
    return equipment

@router.post("/rent-equipment")
def rent_equipment(
    equipment_id: int=Query(..., description="ID of the equipment to rent"),
    renter_name: str=Query(..., description="Name of the person renting the equipment"),
    renter_phone: str=Query(..., description="Phone number for returning the equipment"),
    db: Session = Depends(get_db)
):
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        return {"message": "Equipment not found"}
    if equipment.availability != 'Available':
        return {"message": "Equipment is not available for rent"}
    
    rental = Rental(
        equipment_id=equipment_id,
        renter_name=renter_name,
        renter_phone=renter_phone
    )
    db.add(rental)
    
    # Update equipment availability
    equipment.availability = 'Rented'
    
    db.commit()
    db.refresh(rental)
    return {"message": "Equipment rented successfully"}