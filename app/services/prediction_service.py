from app.db.database import next_id, clean


def save_predictions(db, filename, report, phone=None):
    record = {
        "id": next_id("predictions"),
        "image_name": filename,
        "disease": report["disease"],
        "confidence": report["confidence"],
        "treatment": report["medicine"],
        "model": report.get("model"),
        "phone": phone
    }

    db.predictions.insert_one(record)


def get_all_predictions(db):
    return [clean(item) for item in db.predictions.find().sort("id", 1)]
