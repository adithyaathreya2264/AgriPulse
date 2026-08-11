import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from json import JSONDecodeError
from app.schemas.disease_report import Analysis
from app.ai.agent.medicine_database import MEDICINE_DB
from pydantic import ValidationError
load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)


model = genai.GenerativeModel("gemini-2.5-flash")


def generate_disease_report(
    disease,
    confidence,
    temperature,
    humidity
):
    medicine_info = MEDICINE_DB.get(
        disease,
        {
            "medicine": "Consult Expert",
            "cost": "Unknown"
        }
    )

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

    response = model.generate_content(prompt)
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