import os

import torch
torch.set_num_threads(2)
import torch.nn as nn
import torch.optim as optim

from torchvision import transforms, datasets
from torchvision.models import efficientnet_b0
from torch.utils.data import DataLoader, random_split

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("Using:", device)

# Lightweight transforms

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.ToTensor(),
])

# Dataset

dataset = datasets.ImageFolder(
    "app/ai/datasets/PlantVillage",
    transform=transform
)

print(dataset.classes)

train_size = int(0.8 * len(dataset))
val_size = len(dataset) - train_size

train_dataset, val_dataset = random_split(
    dataset,
    [train_size, val_size]
)

# Small batch size to save RAM

train_loader = DataLoader(
    train_dataset,
    batch_size=4,
    shuffle=True,
    num_workers=0,
    pin_memory=False
)

val_loader = DataLoader(
    val_dataset,
    batch_size=4,
    num_workers=0,
    pin_memory=False
)

# Pretrained model

model = efficientnet_b0(weights="DEFAULT")

# Freeze feature extractor

for param in model.features.parameters():
    param.requires_grad = False

num_classes = len(dataset.classes)

model.classifier[1] = nn.Linear(
    model.classifier[1].in_features,
    num_classes
)

model = model.to(device)

criterion = nn.CrossEntropyLoss()

optimizer = optim.Adam(
    model.classifier.parameters(),
    lr=0.001
)

epochs = 5
best_accuracy = 0
os.makedirs("app/ai/models", exist_ok=True)

for epoch in range(epochs):

    model.train()

    running_loss = 0

    for images, labels in train_loader:

        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()

        outputs = model(images)

        loss = criterion(outputs, labels)

        loss.backward()

        optimizer.step()

        running_loss += loss.item()

    # Validation

    model.eval()

    correct = 0
    total = 0

    with torch.no_grad():

        for images, labels in val_loader:

            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)

            _, predicted = torch.max(outputs, 1)

            total += labels.size(0)

            correct += (predicted == labels).sum().item()

    accuracy = 100 * correct / total

    print(
        f"Epoch {epoch+1}/{epochs} | "
        f"Loss: {running_loss:.2f} | "
        f"Accuracy: {accuracy:.2f}%"
    )

    # Keep only the best-performing epoch
    if accuracy > best_accuracy:
        best_accuracy = accuracy

        torch.save(
            model.state_dict(),
            "app/ai/models/efficientnet.pth"
        )

        print(f"Best model saved ({best_accuracy:.2f}%)")

print(f"Training finished. Best accuracy: {best_accuracy:.2f}%")
