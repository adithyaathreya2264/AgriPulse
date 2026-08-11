import os
import json

from dotenv import load_dotenv
import google.generativeai as genai

from app.ai.tools.tool_dispatcher import dispatch
from app.ai.tools.tool_executer import execute_tool

load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel("gemini-2.5-flash")


def ask_ai(report, question):
    tool_plan = dispatch(question)

    print("\n========== TOOL PLAN ==========")
    print(tool_plan)

    tool_result = None

    if tool_plan.get("tool"):

        tool_result = execute_tool(tool_plan)

    print("\n========== TOOL RESULT ==========")
    print(tool_result)

    prompt = f"""
You are AgriPulse AI.

You are an expert agricultural advisor.

Current Crop Diagnosis:

{json.dumps(report, indent=2)}

Backend Tool Result:
{json.dumps(tool_result,indent=2,default=str)}

Conversation Style:
- Be conversational.
- Do not repeat previous information.
- Treat this as a follow-up conversation.
- Answer only what the farmer asked.

Farmer Question:

{question}

Rules:

1. Answer ONLY according to the user's question.
2. Use the current crop diagnosis as context.
3. If backend tool data is available, always use it.
4. Never change the detected disease.
5. Never invent medicine names.
6. Never invent crop prices.
7. Never invent marketplace information.
8. Be practical.
9. Keep answer below 150 words.
10. Never invent weather.
11. Use backend tool results only if they are relevant to the question.
12. Do NOT repeat the entire diagnosis unless the user asks.
13. Keep answers concise (2-5 sentences).
14. If the question is about spraying, answer only about spraying.
15. If the question is about medicine, answer only about medicine.
16. If the question is about weather, answer using the weather tool.
17. If the question is about crop price, answer using the price tool.
18. If the question is unrelated to agriculture, politely redirect the conversation.
19. Never repeat disease name, confidence, weather, or cost unless needed.
"""

    response = model.generate_content(prompt)

    return response.text