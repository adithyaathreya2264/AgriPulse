import copy
import json

from app.ai.gemini_client import generate_content
from app.services import sarvam_service

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
    "te": "Telugu",
    "ta": "Tamil",
    "ml": "Malayalam",
    "mr": "Marathi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "or": "Odia",
    "ur": "Urdu",
    "as": "Assamese",
    "bho": "Bhojpuri"
}

# Unicode ranges of each script. Scripts shared by several languages
# (Devanagari: Hindi / Marathi / Bhojpuri) are resolved by a hint or Gemini.
SCRIPT_LANGUAGES = [
    ((0x0C80, 0x0CFF), "kn"),
    ((0x0C00, 0x0C7F), "te"),
    ((0x0B80, 0x0BFF), "ta"),
    ((0x0D00, 0x0D7F), "ml"),
    ((0x0A80, 0x0AFF), "gu"),
    ((0x0A00, 0x0A7F), "pa"),
    ((0x0B00, 0x0B7F), "or"),
    ((0x0600, 0x06FF), "ur"),
    ((0x0980, 0x09FF), "bn"),        # also Assamese: resolved by hint
]

DEVANAGARI = (0x0900, 0x097F)

# Keys whose text values are shown to the farmer and should be translated.
# Names, places, numbers and dates are left untouched.
TEXT_KEYS = {
    "disease", "medicine", "cause", "severity", "weather_risk",
    "medicine_usage", "precautions", "recommendation", "condition",
    "advice", "trend", "price_message", "error", "message",
    "verdict", "explanation", "improvement_tips", "missing_documents",
    "interest_note", "disclaimer", "blockers", "notes", "prediction_period"
}


def normalize_language(lang):
    """Return a supported language code, defaulting to English."""
    if not lang:
        return "en"

    lang = lang.strip().lower()

    return lang if lang in SUPPORTED_LANGUAGES else "en"


def _clean_json(text):
    text = text.strip()
    text = text.replace("```json", "").replace("```", "")
    return text.strip()


def detect_script_language(text, hint=None):
    """
    Guess the language from the script. Returns a code, "devanagari"
    (ambiguous: Hindi / Marathi / Bhojpuri) or None (Latin / unknown).
    """

    counts = {}

    for char in text:
        code = ord(char)

        if DEVANAGARI[0] <= code <= DEVANAGARI[1]:
            counts["devanagari"] = counts.get("devanagari", 0) + 1
            continue

        for (low, high), lang in SCRIPT_LANGUAGES:
            if low <= code <= high:
                counts[lang] = counts.get(lang, 0) + 1
                break

    if not counts:
        return None

    winner = max(counts, key=counts.get)

    if winner == "devanagari":
        return hint if hint in ("hi", "mr", "bho") else "devanagari"

    if winner == "bn" and hint == "as":
        return "as"

    return winner


def translate_to_english(text, hint_lang=None):
    """
    Translate a farmer's message to English.

    Returns (english_text, detected_language_code).
    Falls back to the original text when translation fails.
    """

    if not text or not text.strip():
        return text, "en"

    # Plain English / ASCII commands ("price tomato") need no translation
    if text.isascii():
        return text, "en"

    # 1. Sarvam, when the script identifies the language
    script_lang = detect_script_language(text, hint_lang)

    # Devanagari is shared by Hindi / Marathi / Bhojpuri: ask Sarvam which one
    if script_lang == "devanagari" and sarvam_service.configured():
        try:
            script_lang = sarvam_service.identify_language(text) or script_lang

        except sarvam_service.SarvamError as e:
            print("Sarvam language id failed:", e)

    if script_lang and script_lang != "devanagari" and sarvam_service.translation_supported(script_lang, "en"):
        try:
            return sarvam_service.translate(text, script_lang, "en"), script_lang

        except sarvam_service.SarvamError as e:
            print("Sarvam translation failed, using Gemini:", e)

    # 2. Gemini: detects the language and translates
    prompt = f"""
Detect the language of the message and translate it to English.

Supported language codes: {", ".join(SUPPORTED_LANGUAGES)}
Use "en" if the language is not one of the supported ones.

Return ONLY valid JSON, no markdown:
{{"lang": "<code>", "english": "<translation>"}}

Message:
{text}
"""

    try:
        data = json.loads(_clean_json(generate_content(prompt).text))

        return (
            data["english"],
            normalize_language(data.get("lang"))
        )

    except Exception as e:
        print("Translation error:", e)
        return text, "en"


def _gemini_translate(text, target_lang):
    prompt = f"""
Translate the following text to {SUPPORTED_LANGUAGES[target_lang]}.
Keep numbers, units, currency symbols and product names unchanged.
Return ONLY the translation.

Text:
{text}
"""

    return generate_content(prompt).text.strip()


def translate_to_user_language(text, target_lang):
    """Translate English text to the farmer's language."""

    target_lang = normalize_language(target_lang)

    if target_lang == "en" or not text or not str(text).strip():
        return text

    if sarvam_service.translation_supported("en", target_lang):
        try:
            return sarvam_service.translate(str(text), "en", target_lang)

        except sarvam_service.SarvamError as e:
            print("Sarvam translation failed, using Gemini:", e)

    try:
        return _gemini_translate(text, target_lang)

    except Exception as e:
        print("Translation error:", e)
        return text


def _translate_list(texts, target_lang):
    """Translate many strings; Sarvam first, then one Gemini call."""

    if sarvam_service.translation_supported("en", target_lang):
        try:
            return sarvam_service.translate_many(texts, "en", target_lang)

        except sarvam_service.SarvamError as e:
            print("Sarvam translation failed, using Gemini:", e)

    prompt = f"""
Translate each string in this JSON array to {SUPPORTED_LANGUAGES[target_lang]}.
Keep numbers, units, currency symbols and product names unchanged.
Return ONLY a JSON array with exactly {len(texts)} strings, in the same order.

{json.dumps(texts, ensure_ascii=False)}
"""

    translated = json.loads(_clean_json(generate_content(prompt).text))

    if not isinstance(translated, list) or len(translated) != len(texts):
        raise ValueError("Translation count mismatch")

    return [str(item) for item in translated]


def translate_payload(payload, target_lang, keys=TEXT_KEYS):
    """
    Translate the farmer-facing text fields of a JSON-like response
    (dicts / lists) in one call. Returns a translated copy.
    """

    target_lang = normalize_language(target_lang)

    if target_lang == "en" or payload is None:
        return payload

    result = copy.deepcopy(payload)

    # Collect every translatable string as (container, key_or_index)
    slots = []

    def walk(node, translatable=False):
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str):
                    if key in keys:
                        slots.append((node, key))
                else:
                    walk(value, key in keys)

        elif isinstance(node, list):
            for index, value in enumerate(node):
                if isinstance(value, str):
                    if translatable:
                        slots.append((node, index))
                else:
                    walk(value, translatable)

    walk(result)

    if not slots:
        return result

    texts = [container[key] for container, key in slots]

    try:
        translated = _translate_list(texts, target_lang)

        for (container, key), value in zip(slots, translated):
            container[key] = value

    except Exception as e:
        print("Translation error:", e)

    return result
