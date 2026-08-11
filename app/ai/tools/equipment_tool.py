from app.db.database import SessionLocal
from app.models.equipment import Equipment
def execute():

    db = SessionLocal()

    try:

        equipment = db.query(Equipment).filter(
            Equipment.availability == "Available"
        ).all()

        return [
            {
                "name": item.equipment_name,
                "owner": item.owner_name,
                "location": item.location,
                "price": item.price_per_day
            }
            for item in equipment
        ]

    finally:

        db.close()