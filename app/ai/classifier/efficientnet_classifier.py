import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from torchvision.models import efficientnet_b0

CLASS_NAMES = ["Potato Early Blight",
                "Potato Late Blight",
                "Potato Healthy",
                "Tomato Early Blight",
                "Tomato Late Blight",
                "Tomato Healthy"]
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model=efficientnet_b0(weights=None)
model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(CLASS_NAMES))
model.load_state_dict(torch.load("app/ai/models/efficientnet.pth", map_location=device))
model.eval()
transform=transforms.Compose([
    transforms.Resize((224,224)),
    transforms.ToTensor()
])
def predict_disease(image_path):
    image = Image.open(image_path).convert("RGB")

    image = transform(image)

    image = image.unsqueeze(0).to(device)

    with torch.no_grad():

        outputs = model(image)

        probabilities = torch.softmax(outputs, dim=1)

        confidence, predicted = torch.max(probabilities, 1)

    confidence = round(confidence.item() * 100, 2)

    if confidence < 85:
        return {
            "disease": "Uncertain",
            "confidence": confidence
        }

    return {
        "disease": CLASS_NAMES[predicted.item()],
        "confidence": confidence
    }