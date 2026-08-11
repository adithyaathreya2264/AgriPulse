from fastapi import APIRouter, UploadFile, File, Depends, Form
import shutil
import os

from app.services.disease_service import predict_disease
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.prediction import Prediction
from app.services.prediction_service import save_predictions, get_all_predictions
from app.services.disease_intelligent_service import analyze_crop
router = APIRouter()

UPLOAD_DIR = "uploads"

#db dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/detect-disease")
def detect_disease(
    file: UploadFile = File(...),
    city: str = Form(...),
    db: Session = Depends(get_db)
):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Generate complete AI report
    report = analyze_crop(file_path, city)

    # Save AI report for chat assistant
    from app.services.ai_session_service import save_report
    save_report(db, report)

    # Save prediction history
    save_predictions(db, file.filename, report)

    return {
        "filename": file.filename,
        "report": report
    }
@router.get("/predictions")
def get_predictions(db: Session = Depends(get_db)):
    return get_all_predictions(db)

@router.delete("/predictions")
def delete_predictions(db: Session = Depends(get_db)):
    db.query(Prediction).delete()
    db.commit()
    return {"message": "All predictions deleted"}