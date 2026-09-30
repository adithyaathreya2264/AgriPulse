import os
import json
from dotenv import load_dotenv
from app.ai.gemini_client import generate_content
from json import JSONDecodeError
from app.schemas.disease_report import Analysis
from app.ai.agent.medicine_database import get_medicine_info
from pydantic import ValidationError
load_dotenv()





def generate_disease_report(
    disease,
    confidence,
    temperature,
    humidity
):
    medicine_info = get_medicine_info(disease)

    prompt = f"""
You are an agricultural expert.

Disease: {disease}
Confidence: {confidence}%
Temperature: {temperature}°C
Humidity: {humidity}%

Medicine:
{medicine_info['medicine']}

Estimated Cost:
{medicine_info['cost']}

Return ONLY valid JSON.
Do not include markdown.
Do not include explanation.
Do not include backticks.

Return exactly in this format:
{{
"cause": "...",
"severity":"...",
"weather_risk": "...",
"medicine_usage": "...",
"precautions": [
    "...",
    "...",
    "..."
],
"recommendation":"..."
}}

Keep the answer practical and concise.
"""

    response = generate_content(prompt)
    text=response.text.strip()
    text=text.replace("```json","")
    text=text.replace("```","").strip()
    try:
        analysis= Analysis.model_validate(
        json.loads(text)
        )
    except (JSONDecodeError,ValidationError):
        analysis={
            "cause":"Unable to generate AI analysis.",
            "severity":"Unknown",
            "weather_risk":"Unknown",
            "medicine_usage": "...",
            "precautions": [
                "Consult an agricultural officer."
            ],
            "recommendation":
            "Upload another clear image"
        }

    return {
        "medicine": medicine_info["medicine"],
        "estimated_cost": medicine_info["cost"],
        "analysis": analysis.model_dump()
    }