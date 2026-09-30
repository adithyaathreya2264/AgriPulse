import os
import json
from dotenv import load_dotenv
from app.ai.gemini_client import generate_content

load_dotenv()




def dispatch(question: str):

    prompt = f"""
You are an AI tool planner.

Available tools:

1. weather
Arguments:
- city

2. price
Arguments:
- crop

3. equipment
Arguments:
None

4. history
Arguments:
None

Return ONLY valid JSON.

Examples:

Question:
What's the weather in Mysuru?

Output:
{{
    "tool": "weather",
    "city": "Mysuru"
}}

Question:
Today's rice price

Output:
{{
    "tool": "price",
    "crop": "rice"
}}

Question:
Show available equipment

Output:
{{
    "tool": "equipment"
}}

Question:
Show my history

Output:
{{
    "tool": "history"
}}

Question:
{question}
"""

    response = generate_content(prompt)

    text = response.text.strip()
    text = text.replace("```json", "")
    text = text.replace("```", "").strip()

    try:
        return json.loads(text)
    except Exception:
        return {"tool": None}