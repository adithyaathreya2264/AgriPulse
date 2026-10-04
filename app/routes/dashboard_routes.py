from fastapi import APIRouter, Depends

from app.db.database import get_db

router = APIRouter()


@router.get("/dashboard-stats")
def dashboard_stats(db=Depends(get_db)):
    return {
        "total_predictions": db.predictions.count_documents({}),
        "total_equipment": db.equipment.count_documents({}),
        "total_rentals": db.rentals.count_documents({}),
        "total_users": db.users.count_documents({})
    }
