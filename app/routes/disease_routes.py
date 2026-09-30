from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException
import shutil
import os
import uuid

from app.services.disease_service import predict_disease
from app.db.database import get_db
from app.services.prediction_service import save_predictions, get_all_predictions
from app.services.disease_intelligent_service import analyze_crop
from app.services.translation_service import translate_payload
from app.ai.classifier.common import ModelNotFoundError
router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/detect-disease")
def detect_disease(
    file: UploadFile = File(...),
    city: str = Form(...),
    lang: str = Form("en"),
    db=Depends(get_db)
):
    extension = os.path.splitext(file.filename or "")[1].lower()
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{extension}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Generate complete AI report
    try:
        report = analyze_crop(file_path, city)
    except ModelNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Save AI report for chat assistant
    from app.services.ai_session_service import save_report
    save_report(db, report)

    # Save prediction history
    save_predictions(db, file.filename, report)

    # History and chat memory stay in English; only the response is translated
    return {
        "filename": file.filename,
        "report": translate_payload(report, lang)
    }
@router.get("/predictions")
def get_predictions(db=Depends(get_db)):
    return get_all_predictions(db)

@router.delete("/predictions")
def delete_predictions(db=Depends(get_db)):
    db.predictions.delete_many({})
    return {"message": "All predictions deleted"}