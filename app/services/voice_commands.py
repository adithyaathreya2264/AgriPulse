"""
Voice commands: a spoken sentence -> what the web app should do.

The result is always validated against a fixed list, so a spoken (or
Gemini-invented) command can only navigate / fill known fields.
"""

import json
import re

from app.ai.gemini_client import generate_content

PAGES = {
    "home", "disease", "price", "weather", "marketplace",
    "history", "assistant", "loan", "auth"
}

ACTIONS = {"navigate", "weather", "price", "search_equipment", "ask"}

MAX_PARAM_LENGTH = 60

# Fallback when Gemini is unavailable: keyword rules on the English text
KEYWORD_PAGES = [
    (("weather", "rain", "temperature", "forecast"), "weather"),
    (("price", "rate", "mandi", "market rate", "sell"), "price"),
    (("disease", "leaf", "leaves", "photo", "sick", "blight", "yellow", "spots", "pest", "fungus"), "disease"),
    (("rent", "tractor", "equipment", "drone", "harvester", "marketplace"), "marketplace"),
    (("loan", "credit", "kcc", "bank"), "loan"),
    (("history", "previous"), "history"),
    (("assistant", "chat", "question", "help"), "assistant"),
    (("login", "register", "sign"), "auth"),
    (("home", "main"), "home"),
]

CROP_WORDS = re.compile(r"\b(?:price|rate|of|for|the|what|is|tell|me|show|check)\b", re.I)


def clean_param(value):
    if value is None:
        return None

    value = re.sub(r"[^\w\s\-.,]", "", str(value), flags=re.UNICODE).strip()

    return value[:MAX_PARAM_LENGTH] or None


def validate(command):
    """Force a command into the allowed shape (or a safe 'ask')."""

    if not isinstance(command, dict):
        return {"action": "ask", "page": "assistant", "params": {}}

    action = command.get("action")
    page = command.get("page")

    if action not in ACTIONS:
        action = "navigate" if page in PAGES else "ask"

    if page not in PAGES:
        page = {
            "weather": "weather",
            "price": "price",
            "search_equipment": "marketplace",
            "ask": "assistant",
        }.get(action, "home")

    raw = command.get("params") if isinstance(command.get("params"), dict) else {}

    params = {}

    for key in ("city", "crop", "query", "question"):
        value = clean_param(raw.get(key))

        if value:
            params[key] = value

    return {"action": action, "page": page, "params": params}


def keyword_command(english_text):
    """Deterministic fallback."""

    text = english_text.lower()

    for words, page in KEYWORD_PAGES:
        if any(word in text for word in words):
            command = {"action": "navigate", "page": page, "params": {}}

            if page == "weather":
                match = re.search(r"\b(?:in|at|for)\s+([a-z ]{2,30})$", text.strip())

                if match:
                    command.update(action="weather", params={"city": match.group(1).strip()})

            elif page == "price":
                crop = CROP_WORDS.sub("", text)
                crop = re.sub(r"\b(?:mandi|market|today|now|sell|selling)\b", "", crop).strip()

                if crop and len(crop.split()) <= 3:
                    command.update(action="price", params={"crop": crop})

            elif page == "marketplace":
                match = re.search(r"\b(tractor|harvester|drone|rotavator|cultivator|seeder|sprayer|trailer)\b", text)

                if match:
                    command.update(action="search_equipment", params={"query": match.group(1)})

            return validate(command)

    return {"action": "ask", "page": "assistant", "params": {"question": clean_param(english_text) or ""}}


def interpret(english_text):
    """Turn an English sentence into a validated command."""

    prompt = f"""
You control a farming web app by voice. Turn the farmer's sentence into JSON.

Pages: {", ".join(sorted(PAGES))}
Actions:
- navigate: just open a page
- weather: open weather, params.city = the city
- price: open price prediction, params.crop = the crop name
- search_equipment: open marketplace, params.query = equipment name
- ask: open the assistant, params.question = the question

Return ONLY valid JSON, no markdown:
{{"action": "...", "page": "...", "params": {{}}}}

Sentence: {english_text}
"""

    try:
        text = generate_content(prompt).text
        text = text.replace("```json", "").replace("```", "").strip()

        return validate(json.loads(text))

    except Exception as e:
        print("Voice command fallback:", e)
        return keyword_command(english_text)
