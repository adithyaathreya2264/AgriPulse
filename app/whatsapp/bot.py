"""
Understands a farmer's WhatsApp message and decides what to do.

Order of things for every message:
  1. who is this?  (their AgriPulse account, language, what we were waiting for)
  2. what is it?   a photo, a voice note, a shared location, or text
  3. text: a command (weather, price ...), an answer to our last question,
     a menu number, or a free question for the assistant

Everything here is English: the webhook translates in and out.
"""

import re

from app.services import speech_service
from app.services.auth_service import normalize_phone
from app.services.speech_service import SpeechError
from app.services.translation_service import (
    normalize_language,
    translate_to_english
)
from app.whatsapp import assistant, media
from app.whatsapp.natural import natural_command
from app.whatsapp.features import account, disease, equipment, language, loan, price, weather
from app.whatsapp.features.common import as_number, need_account
from app.whatsapp.state import (
    end_flow,
    get_session,
    get_wa_user,
    update_wa_user
)
from app.whatsapp.types import Context, Incoming, Outcome, say

MENU = (
    "🌾 *AgriPulse* — reply with a number:\n"
    "1. 🌿 Crop disease (send a leaf photo)\n"
    "2. 🌦 Weather\n"
    "3. 📈 Mandi prices & forecast\n"
    "4. 🤔 Ask a farming question\n"
    "5. 🚜 Rent equipment near me\n"
    "6. 💰 Loan (Kisan Credit Card) check\n"
    "7. 🔔 My alerts & bookings\n"
    "8. 🌐 Language\n\n"
    "You can also send a photo, a voice note, or type things like "
    "'weather Mysuru' or 'price tomato'. Send STOP to stop messages."
)

WELCOME = (
    "👋 Welcome to AgriPulse, your farming assistant on WhatsApp! "
    "I use your messages only to answer you. Photos are deleted after "
    "the diagnosis unless you tell me the correct disease."
)

RATE_LIMITED = "You are sending messages very fast. Please wait a few minutes and try again."

# States where the farmer types an answer (a name, a label), so only global
# commands interrupt. In the open conversation with the assistant ("question")
# short commands such as "language en" or "weather Hassan" still work.
FREE_TEXT_STATES = {
    "feedback_label", "weather_city", "price_crop",
    "digest_district", "loan_district", "loan_crops",
}

# In the assistant conversation only messages this short count as commands
MAX_COMMAND_WORDS_IN_CONVERSATION = 4

GLOBAL_COMMANDS = {"menu", "cancel", "stop", "start"}

MENU_WORDS = {
    "hi", "hii", "hiii", "hello", "hey", "hai", "namaste", "namaskar", "menu",
    "help", "options", "start over", "main menu", "home", "good morning",
}
STOP_WORDS = {"stop", "unsubscribe", "opt out", "optout", "stop messages"}
START_WORDS = {"start", "subscribe", "resume", "opt in", "optin"}
CANCEL_WORDS = {"cancel", "exit", "quit", "back", "reset"}

# (command, pattern on the cleaned lower-case text, first group = arguments)
COMMANDS = [
    ("alert_remove", r"(?:stop|remove|delete|cancel)\s+alert\s*(\d*)"),
    ("alerts", r"(?:my\s+)?alerts"),
    ("alert", r"alert\b(.*)"),
    ("weather", r"(?:weather|mausam|climate|forecast)\b(.*)"),
    ("price", r"(?:price|prices|rate|rates|mandi)\b(.*)"),
    ("digest", r"(?:daily\s+)?(?:digest|morning\s+message)\b\s*(.*)"),
    ("language", r"(?:language|lang|bhasha)\b\s*(.*)"),
    ("ask", r"(?:ask|question|advice)\b\s*(.*)"),
    ("bookings", r"(?:my\s+)?(?:bookings?|rentals?)"),
    ("equipment", r"(?:equipment|rent|tractor|drone|harvester|machines?)\b.*"),
    ("loan", r"(?:loan|kcc|kisan\s+credit(?:\s+card)?)\b.*"),
    ("disease", r"(?:disease|diagnos\w*|photo|leaf|scan)\b.*"),
]


# ------------------------------------------------------------------
# Text -> command
# ------------------------------------------------------------------

def clean(text, lower=True):
    """No emoji / odd symbols (commas and dots stay); lower case unless told not to."""

    text = re.sub(r"[^\w\s,.\-']", " ", text or "", flags=re.UNICODE)
    text = " ".join(text.split())

    return text.lower() if lower else text


def parse_command(text):
    """(command, argument) or (None, "")"""

    cased = clean(text, lower=False)      # what the farmer typed (Kolar, not kolar)
    cleaned = cased.lower()               # used to recognise commands

    if cleaned in MENU_WORDS:
        return "menu", ""

    if cleaned in STOP_WORDS:
        return "stop", ""

    if cleaned in START_WORDS:
        return "start", ""

    if cleaned in CANCEL_WORDS:
        return "cancel", ""

    for command, pattern in COMMANDS:
        match = re.fullmatch(pattern, cleaned)

        if match:
            # The argument keeps the farmer's spelling
            argument = cased[match.start(1):match.end(1)].strip() if match.groups() else ""

            return command, argument

    # Everyday phrases: "tell me the weather in Mysore"
    natural = natural_command(cased)

    if natural:
        return natural

    return None, ""


# ------------------------------------------------------------------
# Routing
# ------------------------------------------------------------------

def _price_done(ctx, text):
    """The farmer went on to something else: treat it as a new message."""
    end_flow(ctx)

    return None


STATE_HANDLERS = {
    "weather_city": weather.on_city,
    "price_crop": price.on_crop,
    "price_choose": price.on_choice,
    "price_done": _price_done,
    "feedback": disease.on_feedback,
    "feedback_label": disease.on_label,
    "language": language.on_choice,
    "question": assistant.on_question,
    "digest_district": account.on_digest_district,
    "location": lambda ctx, text: say(
        "Please share your location with 📎 → Location → Send your current location, or send MENU.",
        static=True
    ),
    "loan_district": loan.on_district,
    "loan_acres": loan.on_acres,
    "loan_ownership": loan.on_ownership,
    "loan_crops": loan.on_crops,
    "loan_outstanding": loan.on_outstanding,
    "loan_default": loan.on_default,
    "loan_docs": loan.on_docs,
}


def _menu(ctx):
    end_flow(ctx)

    return say(MENU, static=True)


def _stop(ctx):
    update_wa_user(ctx.db, ctx.phone, subscribed=False, digest=False)
    end_flow(ctx)

    return say(
        "You will get no more alerts or morning messages. I will still answer if you write to me. "
        "Send START to turn them back on.",
        static=True
    )


def _start(ctx):
    update_wa_user(ctx.db, ctx.phone, subscribed=True)

    return say("Welcome back! Alerts are on again. Send MENU to see what I can do.", static=True)


def _cancel(ctx):
    end_flow(ctx)

    return say("Okay, cancelled. Send MENU to see what I can do.", static=True)


def _alerts_and_bookings(ctx):
    if not ctx.account:
        return need_account()

    first = account.alerts_list(ctx)
    second = account.bookings(ctx)

    return Outcome(replies=first.replies + second.replies)


MENU_CHOICES = {
    1: lambda ctx: disease.start(ctx),
    2: lambda ctx: weather.start(ctx),
    3: lambda ctx: price.start(ctx),
    4: lambda ctx: assistant.ask(ctx, ""),
    5: lambda ctx: equipment.start(ctx),
    6: lambda ctx: loan.start(ctx),
    7: _alerts_and_bookings,
    8: lambda ctx: language.start(ctx),
}


def _alert_command(ctx, argument):
    crop, district, market = price.parse_args(argument)

    if crop and district and market:
        return price.create(ctx, crop, district, market)

    return price.alert_from_context(ctx)


def run_command(ctx, command, argument):
    if command == "menu":
        return _menu(ctx)

    if command == "cancel":
        return _cancel(ctx)

    if command == "stop":
        return _stop(ctx)

    if command == "start":
        return _start(ctx)

    if command == "weather":
        return weather.start(ctx, argument)

    if command == "price":
        return price.start(ctx, argument)

    if command == "alerts":
        return account.alerts_list(ctx)

    if command == "alert":
        return _alert_command(ctx, argument)

    if command == "alert_remove":
        return account.alert_remove(ctx, argument)

    if command == "digest":
        return account.digest(ctx, argument)

    if command == "language":
        return language.start(ctx, argument)

    if command == "ask":
        return assistant.ask(ctx, argument)

    if command == "bookings":
        return account.bookings(ctx)

    if command == "equipment":
        return equipment.start(ctx)

    if command == "loan":
        return loan.start(ctx)

    if command == "disease":
        return disease.start(ctx)

    return None


def route_text(ctx, english):
    """A text message (typed, or a transcribed voice note)."""

    if not english.strip():
        return _menu(ctx)

    command, argument = parse_command(english)

    # 1. Global commands always work, even in the middle of a question
    if command in GLOBAL_COMMANDS:
        return run_command(ctx, command, argument)

    # 2. What we were waiting for ("which crop?", "1 or 2?", ...)
    if ctx.state:
        interrupts = command and ctx.state not in FREE_TEXT_STATES

        if interrupts and ctx.state == "question":
            interrupts = len(english.replace(",", " ").split()) <= MAX_COMMAND_WORDS_IN_CONVERSATION

        if not interrupts:
            handler = STATE_HANDLERS.get(ctx.state)

            if handler:
                outcome = handler(ctx, english)

                if outcome is not None:
                    return outcome

            else:
                end_flow(ctx)

    # 3. A command
    if command:
        outcome = run_command(ctx, command, argument)

        if outcome is not None:
            return outcome

    # 4. A menu number
    number = as_number(english)

    if number in MENU_CHOICES and not ctx.state:
        return MENU_CHOICES[number](ctx)

    # 5. Anything else is a question for the assistant
    if len(clean(english)) < 3:
        return _menu(ctx)

    return assistant.ask(ctx, english)


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def _account_for(db, phone10):
    if not phone10:
        return None

    return db.users.find_one({"phone": phone10}, {"_id": 0, "password_hash": 0})


def handle(db, incoming: Incoming, rate_limited=False):
    """
    The bot's answer to one message (an Outcome, in English).
    """

    phone10 = normalize_phone(incoming.phone)
    account_doc = _account_for(db, phone10)

    wa_user, first_contact = get_wa_user(db, incoming.phone)

    lang = normalize_language(
        wa_user.get("lang")
        or (account_doc.get("language") if account_doc and account_doc.get("onboarded") else None)
        or "en"
    )

    ctx = Context(
        db=db,
        incoming=incoming,
        phone=incoming.phone,
        phone10=phone10,
        account=account_doc,
        wa_user=wa_user,
        session=get_session(db, incoming.phone),
        lang=lang,
    )

    if rate_limited:
        outcome = say(RATE_LIMITED, static=True)
        outcome.lang = ctx.lang

        return outcome

    voice = False
    heard_prefix = ""

    # ---- what kind of message? -------------------------------------
    if incoming.latitude is not None and incoming.longitude is not None:
        outcome = equipment.nearby(ctx, incoming.latitude, incoming.longitude)

    elif incoming.media_url and incoming.media_type.startswith("image"):
        outcome = disease.diagnose(ctx, incoming.media_url)

    elif incoming.media_url and incoming.media_type.startswith("audio"):
        voice = True
        outcome, heard_prefix = _voice_note(ctx, incoming)

    elif incoming.media_url:
        outcome = say("I can read photos, voice notes and shared locations. Send MENU to see what I can do.", static=True)

    else:
        # No letters (only emoji, digits, punctuation): nothing to translate
        if any(char.isalpha() for char in incoming.body):
            english, detected = translate_to_english(incoming.body, hint_lang=ctx.lang)
        else:
            english, detected = incoming.body, "en"

        if detected != "en":
            ctx.lang = normalize_language(detected)
            update_wa_user(db, incoming.phone, lang=ctx.lang)

        outcome = route_text(ctx, english)

    # ---- finishing touches ------------------------------------------
    outcome.lang = ctx.lang
    outcome.voice = voice

    outcome.prefix = heard_prefix

    if first_contact:
        outcome.replies.insert(0, WELCOME)

    # Remember the language the first time we see it
    if not wa_user.get("lang"):
        update_wa_user(db, incoming.phone, lang=ctx.lang)

    return outcome


def _voice_note(ctx, incoming):
    """Transcribe a voice note and answer it like text. Returns (outcome, "You said: ...")."""

    audio = media.download_media(incoming.media_url)

    if not audio:
        return say("I could not download that voice note. Please send it again.", static=True), ""

    try:
        heard = speech_service.transcribe(audio, ctx.lang, mime_type=incoming.media_type)

    except SpeechError:
        return say(
            "Sorry, I could not understand the voice message. "
            "Please try again, or type your question.",
            static=True
        ), ""

    if heard["lang"] != "en":
        ctx.lang = normalize_language(heard["lang"])
        update_wa_user(ctx.db, ctx.phone, lang=ctx.lang)

    english, _ = translate_to_english(heard["text"], hint_lang=heard["lang"])

    # Show what the farmer said, in their own words
    return route_text(ctx, english), f"🎤 “{heard['text']}”\n\n"
