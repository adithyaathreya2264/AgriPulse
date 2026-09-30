import os
import re

from dotenv import load_dotenv

load_dotenv()

# Below this confidence the prediction is reported as "Uncertain"
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "90"))


TYPOS = {"Sugercane": "Sugarcane"}


class ModelNotFoundError(RuntimeError):
    """The trained weights file is missing."""


def pretty_name(folder_name):
    """
    PlantVillage folder name -> readable disease name.

      Tomato_Early_blight          -> Tomato Early Blight
      Potato___Late_blight         -> Potato Late Blight
      Tomato__healthy / healthy    -> Tomato Healthy
    """

    words = re.split(r"[_\s]+", folder_name.strip())
    words = [word for word in words if word]

    name = " ".join(word[:1].upper() + word[1:].lower() for word in words)

    # Spelling mistakes in dataset folder names
    for wrong, right in TYPOS.items():
        name = name.replace(wrong, right)

    return name
