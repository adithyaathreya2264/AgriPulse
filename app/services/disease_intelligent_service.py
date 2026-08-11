from app.services.disease_service import predict_disease
from app.services.weather_service import get_weather
from app.ai.agent.disease_agent import generate_disease_report


def analyze_crop(image_path, city):

    prediction = predict_disease(image_path)

    if not prediction:
        return {"error": "No disease detected"}

    result = prediction[0]

    disease = result["disease"]
    confidence = result["confidence"]

    weather = get_weather(city)

    if weather is None:
        weather = {
        "city": city,
        "temperature": "N/A",
        "humidity": "N/A",
        "condition": "Unknown",
        "advice": "Weather data unavailable."
    }

    elif "error" in weather:
        weather = {
        "city": city,
        "temperature": "N/A",
        "humidity": "N/A",
        "condition": "Unknown",
        "advice": weather["error"]
    }

    ai_report = generate_disease_report(
        disease=disease,
        confidence=confidence,
        temperature=weather["temperature"],
        humidity=weather["humidity"]
    )

    return {
        "disease": disease,
        "confidence": confidence,

        "weather": weather,

        "medicine": ai_report["medicine"],
        "estimated_cost": ai_report["estimated_cost"],

        "analysis": ai_report["analysis"]
    }