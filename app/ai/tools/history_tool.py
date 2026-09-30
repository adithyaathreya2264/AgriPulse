from app.db.database import get_database


def execute():

    history = get_database().predictions.find().sort("id", -1).limit(5)

    result = []

    for item in history:
        result.append({
            "id": item["id"],
            "image_name": item["image_name"],
            "disease": item["disease"],
            "confidence": item["confidence"],
            "treatment": item["treatment"]
        })

    return result
