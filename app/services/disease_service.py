import os

from app.ai.agent.medicine_database import get_medicine_info
from app.ai.classifier.common import ModelNotFoundError

# Short farmer-facing advice for the classes we know best.
# Other diseases (from a retrained, larger model) use get_medicine_info().
TREATMENT_MAP = {
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


def classify_disease(image_path):
    """
    Run the configured model.

    DISEASE_MODEL=yolo (default) uses YOLOv8-cls and falls back to the
    EfficientNet model when the YOLO weights are not available;
    DISEASE_MODEL=efficientnet uses only EfficientNet.
    """

    backend = os.getenv("DISEASE_MODEL", "yolo").strip().lower()

    if backend != "efficientnet":
        try:
            from app.ai.classifier.yolo_classifier import (
                predict_disease as yolo_predict
            )

            return yolo_predict(image_path)

        except ModelNotFoundError as e:
            print("YOLOv8 unavailable, falling back to EfficientNet:", e)

    from app.ai.classifier.efficientnet_classifier import (
        predict_disease as efficientnet_predict
    )

    return efficientnet_predict(image_path)


def treatment_for(disease):
    if disease in TREATMENT_MAP:
        return TREATMENT_MAP[disease]

    medicine = get_medicine_info(disease)["medicine"]

    if medicine == "Consult Expert":
        return "Consult agricultural expert"

    if medicine == "Not Required":
        return "No treatment needed"

    return f"{medicine} (confirm with your local agriculture officer)"


def predict_disease(image_path: str):

    result = classify_disease(image_path)

    disease = result["disease"]

    confidence = result["confidence"]

    # Below the confidence threshold the classifier returns "Uncertain"

    if disease == "Uncertain":

        return [{
            "disease": "Uncertain prediction",
            "confidence": confidence,
            "treatment": "Please upload a clearer image of a single leaf.",
            "model": result.get("model")
        }]

    return [{

        "disease": disease,

        "confidence": confidence,

        "treatment": treatment_for(disease),

        "model": result.get("model")
    }]
