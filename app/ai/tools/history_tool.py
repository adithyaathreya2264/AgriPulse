from unittest import result

from app.db.database import SessionLocal
from app.models.prediction import Prediction


def execute():

    db = SessionLocal()

    try:

        history = db.query(Prediction).order_by(
            Prediction.id.desc()
        ).limit(5).all()

        result=[]
        for item in history:
            result.append({
            "id":item.id,
            "image_name":item.image_name,
            "disease":item.disease,
            "confidence":item.confidence,
            "treatment":item.treatment
            })
        return result
        
    finally:

        db.close()