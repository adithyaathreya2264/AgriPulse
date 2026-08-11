from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.prediction import Prediction
from app.models.equipment import Equipment
from app.models.rental import Rental
from app.models.user import User

router = APIRouter()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/dashboard-stats")
def dashboard_stats(db: Session = Depends(get_db)):
    return{
    "total_prediction": db.query(Prediction).count(),
    "total_equipment": db.query(Equipment).count(),
    "total_rentals": db.query(Rental).count(),
    "total_users": db.query(User).count()
    }