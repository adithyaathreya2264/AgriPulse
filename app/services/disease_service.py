from app.ai.classifier.efficientnet_classifier import (
    predict_disease as classify_disease
)


def predict_disease(image_path: str):

    result = classify_disease(image_path)

    disease = result["disease"]

    confidence = result["confidence"]

    # Confidence threshold

    if confidence < 85:

        return [{
            "disease": "Uncertain prediction",
            "confidence": confidence,
            "treatment":"Please upload a clearer image."
        }]

    treatment_map = {

        "Tomato Early Blight":
            "Apply chlorothalonil or mancozeb fungicide",

        "Tomato Late Blight":
            "Apply mancozeb immediately and remove infected leaves",

        "Tomato Healthy":
            "No treatment needed",

        "Potato Early Blight":
            "Use recommended fungicide and monitor leaf spots",

        "Potato Late Blight":
            "Apply fungicide immediately and avoid excess moisture",

        "Potato Healthy":
            "No treatment needed"
    }

    return [{

        "disease": disease,

        "confidence": confidence,

        "treatment": treatment_map.get(
            disease,
            "Consult agricultural expert"
        )
    }]