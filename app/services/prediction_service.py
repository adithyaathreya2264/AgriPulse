from app.models.prediction import Prediction

def save_predictions(db, filename, report,phone=None):
    record = Prediction(
         image_name=filename,
         disease=report["disease"],
         confidence=report["confidence"],
         treatment=report["medicine"],
         phone=phone
        )
    db.add(record)

    db.commit()


def get_all_predictions(db):
    return db.query(Prediction).all()