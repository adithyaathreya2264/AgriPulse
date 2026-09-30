"""
Talking to Twilio: sending messages on our own (after the webhook has
answered) and checking that a webhook really comes from Twilio.
"""

import os

from dotenv import load_dotenv
from fastapi import Request

load_dotenv()

# WhatsApp accepts long messages but Twilio limits the body to 1600 characters
MAX_MESSAGE_CHARS = 1500


def account_sid():
    return os.getenv("TWILIO_ACCOUNT_SID")


def auth_token():
    return os.getenv("TWILIO_AUTH_TOKEN")


def sender_number():
    number = os.getenv("TWILIO_WHATSAPP_FROM") or ""

    if number and not number.startswith("whatsapp:"):
        number = f"whatsapp:{number}"

    return number


def rest_configured():
    """Can we send messages without a webhook request to answer?"""
    return bool(account_sid() and auth_token() and sender_number())


def split_message(text, limit=MAX_MESSAGE_CHARS):
    """Cut a long text into parts that fit, at line / sentence ends."""

    text = (text or "").strip()

    if len(text) <= limit:
        return [text] if text else []

    parts, current = [], ""

    for line in text.split("\n"):
        while len(line) > limit:
            cut = max(line.rfind(". ", 0, limit), line.rfind(" ", 0, limit))
            cut = cut if cut > limit // 2 else limit

            if current:
                parts.append(current.strip())
                current = ""

            parts.append(line[:cut + 1].strip())
            line = line[cut + 1:]

        if len(current) + len(line) + 1 > limit:
            parts.append(current.strip())
            current = line
        else:
            current = f"{current}\n{line}" if current else line

    if current.strip():
        parts.append(current.strip())

    return [part for part in parts if part]


def send_messages(phone, texts, media_url=None):
    """
    Send WhatsApp messages through Twilio's REST API.
    The media (a voice note) goes with the last message.
    Returns True when everything was accepted.
    """

    if not rest_configured():
        return False

    from twilio.rest import Client

    parts = [part for text in texts for part in split_message(text)]

    try:
        client = Client(account_sid(), auth_token())

        for index, part in enumerate(parts):
            fields = {"from_": sender_number(), "to": f"whatsapp:{phone}", "body": part}

            if media_url and index == len(parts) - 1:
                fields["media_url"] = [media_url]

            client.messages.create(**fields)

        return True

    except Exception as e:
        print("WhatsApp send error:", e)
        return False


# ------------------------------------------------------------------
# Signature
# ------------------------------------------------------------------

def public_url(request: Request):
    """
    The URL Twilio called (the signature covers it). Behind ngrok or a proxy
    that is PUBLIC_BASE_URL, or the forwarded host.
    """

    base = (os.getenv("PUBLIC_BASE_URL") or "").rstrip("/")

    if not base:
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host", request.headers.get("host", ""))
        base = f"{scheme}://{host}"

    url = base + request.url.path

    if request.url.query:
        url += "?" + request.url.query

    return url


def signature_checking_enabled():
    """
    Requests are checked when the Twilio auth token is known. Set
    TWILIO_VALIDATE_SIGNATURE=false only for local tests with curl.
    """

    if os.getenv("TWILIO_VALIDATE_SIGNATURE", "true").strip().lower() == "false":
        return False

    return bool(auth_token())


def valid_signature(request: Request, form):
    """Did Twilio (and not somebody else) send this request?"""

    if not signature_checking_enabled():
        return True

    from twilio.request_validator import RequestValidator

    return RequestValidator(auth_token()).validate(
        public_url(request),
        {key: form[key] for key in form.keys()},
        request.headers.get("X-Twilio-Signature", "")
    )
