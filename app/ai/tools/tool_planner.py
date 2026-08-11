import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel("gemini-2.5-flash")


def plan_tool(question):

    prompt = f"""
You are an AI planner.

Your ONLY job is to decide:

1. Which backend tool should be used.
2. Which arguments are required.

Available tools:

weather
price
equipment
history

Return ONLY JSON.

Example

Question:
What's today's weather in Mysuru?

Output:

{{
    "tool":"weather",
    "arguments": {{
        "city":"Mysuru"
    }}
}}

Question:

{question}
"""

    response = model.generate_content(prompt)

    text = response.text.strip()

    text = text.replace("```json", "")
    text = text.replace("```", "").strip()

    return json.loads(text)