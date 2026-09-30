from app.services.translation_service import SUPPORTED_LANGUAGES
from app.whatsapp.features.common import as_number
from app.whatsapp.state import end_flow, set_state, update_wa_user
from app.whatsapp.types import Outcome, say

# Shown next to the English name so farmers recognise their language
NATIVE_NAMES = {
    "en": "English", "hi": "हिन्दी", "kn": "ಕನ್ನಡ", "te": "తెలుగు", "ta": "தமிழ்",
    "ml": "മലയാളം", "mr": "मराठी", "bn": "বাংলা", "gu": "ગુજરાતી", "pa": "ਪੰਜਾਬੀ",
    "or": "ଓଡ଼ିଆ", "ur": "اردو", "as": "অসমীয়া", "bho": "भोजपुरी",
}

ORDER = list(SUPPORTED_LANGUAGES)


def find_language(text):
    """A language code from "kn", "Kannada", "kannada please" or "3"."""

    value = (text or "").strip().lower()

    number = as_number(value)

    if number is not None:
        return ORDER[number - 1] if 1 <= number <= len(ORDER) else None

    if value in SUPPORTED_LANGUAGES:
        return value

    for code, name in SUPPORTED_LANGUAGES.items():
        if name.lower() in value.split() or name.lower() == value:
            return code

    for code, name in NATIVE_NAMES.items():
        if name and name in (text or ""):
            return code

    return None


def menu_text():
    lines = [
        f"{index}. {SUPPORTED_LANGUAGES[code]} ({NATIVE_NAMES[code]})"
        for index, code in enumerate(ORDER, start=1)
    ]

    return "🌐 Choose your language (reply with the number):\n" + "\n".join(lines)


def start(ctx, arg=""):
    if arg:
        code = find_language(arg)

        if code:
            return choose(ctx, code)

    set_state(ctx, "language")

    return say(menu_text(), static=True)


def choose(ctx, code):
    update_wa_user(ctx.db, ctx.phone, lang=code)
    ctx.lang = code
    end_flow(ctx)

    outcome = say(
        f"✅ Language set to {SUPPORTED_LANGUAGES[code]}. "
        "Send MENU to see what I can do.",
        static=True
    )

    outcome.lang = code

    return outcome


def on_choice(ctx, text):
    code = find_language(text)

    if not code:
        return say("Please reply with a number from the list, or the language name.", static=True)

    return choose(ctx, code)
