"""
YOLOv8 classification model (yolov8n-cls) for crop leaf diseases.

Same contract as efficientnet_classifier.predict_disease(); the class
names come from the trained model, so adding crops only needs retraining
(see train_yolo_classifier.py).
"""

import os

from app.ai.classifier.common import (
    CONFIDENCE_THRESHOLD,
    ModelNotFoundError,
    pretty_name
)

MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "app/ai/models/yolov8_disease.pt")

_model = None


def get_model():
    """Load the model on first use so the API can start without weights."""
    global _model

    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise ModelNotFoundError(
                f"YOLOv8 model not found at {MODEL_PATH}. "
                "Train it with train_yolo_classifier.py or copy the file."
            )

        from ultralytics import YOLO

        _model = YOLO(MODEL_PATH)

    return _model


def class_names():
    """Readable class names of the loaded model."""
    return [pretty_name(name) for name in get_model().names.values()]


def predict_disease(image_path):
    model = get_model()

    result = model.predict(image_path, verbose=False)[0]

    top = int(result.probs.top1)
    confidence = round(float(result.probs.top1conf) * 100, 2)

    if confidence < CONFIDENCE_THRESHOLD:
        return {
            "disease": "Uncertain",
            "confidence": confidence,
            "model": "yolov8-cls"
        }

    return {
        "disease": pretty_name(model.names[top]),
        "confidence": confidence,
        "model": "yolov8-cls"
    }
