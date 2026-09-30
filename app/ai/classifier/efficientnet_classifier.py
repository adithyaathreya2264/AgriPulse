import os

import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from torchvision.models import efficientnet_b0

from app.ai.classifier.common import CONFIDENCE_THRESHOLD, ModelNotFoundError

MODEL_PATH = "app/ai/models/efficientnet.pth"

CLASS_NAMES = ["Potato Early Blight",
               "Potato Late Blight",
               "Potato Healthy",
               "Tomato Early Blight",
               "Tomato Late Blight",
               "Tomato Healthy"]

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor()
])

_model = None


def get_model():
    """Load the model on first use so the API can start without the weights."""
    global _model

    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise ModelNotFoundError(
                f"Disease model not found at {MODEL_PATH}. "
                "Train it with train_disease_classifier.py or copy the file."
            )

        model = efficientnet_b0(weights=None)
        model.classifier[1] = nn.Linear(
            model.classifier[1].in_features,
            len(CLASS_NAMES)
        )
        model.load_state_dict(
            torch.load(MODEL_PATH, map_location=device)
        )
        model.to(device)
        model.eval()

        _model = model

    return _model


def predict_disease(image_path):
    model = get_model()

    image = Image.open(image_path).convert("RGB")
    image = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(image)
        probabilities = torch.softmax(outputs, dim=1)
        confidence, predicted = torch.max(probabilities, 1)

    confidence = round(confidence.item() * 100, 2)

    if confidence < CONFIDENCE_THRESHOLD:
        return {
            "disease": "Uncertain",
            "confidence": confidence,
            "model": "efficientnet-b0"
        }

    return {
        "disease": CLASS_NAMES[predicted.item()],
        "confidence": confidence,
        "model": "efficientnet-b0"
    }
