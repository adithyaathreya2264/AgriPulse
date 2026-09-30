MEDICINE_DB = {
    "Tomato Late Blight": {
        "medicine": "Mancozeb 75% WP",
        "cost": "₹350-450 per acre"
    },

    "Tomato Early Blight": {
        "medicine": "Chlorothalonil",
        "cost": "₹300-400 per acre"
    },

    "Potato Late Blight": {
        "medicine": "Metalaxyl + Mancozeb",
        "cost": "₹450-600 per acre"
    },

    "Potato Early Blight": {
        "medicine": "Copper Oxychloride",
        "cost": "₹300-500 per acre"
    },

    "Tomato Healthy": {
        "medicine": "Not Required",
        "cost": "₹0"
    },

    "Potato Healthy": {
        "medicine": "Not Required",
        "cost": "₹0"
    }
}


DEFAULT_MEDICINE = {
    "medicine": "Consult Expert",
    "cost": "Unknown"
}

_generated = {}


def get_medicine_info(disease):
    """
    Curated entry when we have one; otherwise ask Gemini (cached), so new
    crops/diseases from a retrained model still get advice.
    """

    if disease in MEDICINE_DB:
        return MEDICINE_DB[disease]

    if disease in _generated:
        return _generated[disease]

    if not disease or disease.lower().startswith("uncertain"):
        return DEFAULT_MEDICINE

    try:
        import json

        from app.ai.gemini_client import generate_content

        prompt = f"""
You are an Indian agricultural expert. Crop disease: {disease}

Return ONLY valid JSON, no markdown:
{{"medicine": "<common fungicide/pesticide or management practice>",
  "cost": "<approximate cost in rupees per acre, e.g. ₹300-450 per acre>"}}

If the plant is healthy, use "Not Required" and "₹0".
"""

        text = generate_content(prompt).text
        text = text.replace("```json", "").replace("```", "").strip()

        data = json.loads(text)

        info = {
            "medicine": str(data["medicine"]),
            "cost": str(data["cost"])
        }

    except Exception as e:
        print("Medicine lookup error:", e)
        return DEFAULT_MEDICINE

    _generated[disease] = info

    return info
