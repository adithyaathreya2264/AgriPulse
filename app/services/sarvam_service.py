"""
Sarvam AI client (https://docs.sarvam.ai): translation, speech-to-text and
text-to-speech for Indian languages.

Credentials go in .env:   SARVAM_API_KEY=...
Optional overrides:       SARVAM_TRANSLATE_MODEL, SARVAM_STT_MODEL,
                          SARVAM_TTS_MODEL, SARVAM_TTS_SPEAKER, SARVAM_BASE_URL

Every failure raises SarvamError; callers fall back to Gemini (text) or the
browser voice (speech), so the app keeps working without Sarvam.

Language coverage (checked against the live API):
  translation  the 11 major languages with mayura:v1, plus Urdu and Assamese
               with sarvam-translate:v1. Bhojpuri is not supported.
  speech-to-text  automatic language detection
  text-to-speech  the 11 major languages (not Urdu / Assamese / Bhojpuri)
"""

import base64
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT_SECONDS = 40
RETRY_STATUSES = {429, 500, 502, 503, 504}

# Our language code -> Sarvam language code
SARVAM_CODES = {
    "en": "en-IN", "hi": "hi-IN", "kn": "kn-IN", "te": "te-IN", "ta": "ta-IN",
    "ml": "ml-IN", "mr": "mr-IN", "bn": "bn-IN", "gu": "gu-IN", "pa": "pa-IN",
    "or": "od-IN", "ur": "ur-IN", "as": "as-IN",
}

FROM_SARVAM = {code: ours for ours, code in SARVAM_CODES.items()}

# The 11 languages mayura:v1 and the voice models serve
MAJOR_LANGUAGES = {"en", "hi", "kn", "te", "ta", "ml", "mr", "bn", "gu", "pa", "or"}

# Translation: the major ones plus Urdu and Assamese (sarvam-translate:v1)
TRANSLATE_LANGUAGES = MAJOR_LANGUAGES | {"ur", "as"}

# Voice output
TTS_LANGUAGES = MAJOR_LANGUAGES

# Characters accepted per request
TRANSLATE_LIMITS = {"mayura:v1": 1000, "sarvam-translate:v1": 2000}
TTS_LIMIT = 1500


class SarvamError(RuntimeError):
    """Sarvam is not configured, or a request failed."""


def api_key():
    return os.getenv("SARVAM_API_KEY")


def base_url():
    return os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai").rstrip("/")


def configured():
    return bool(api_key())


def translation_supported(*languages):
    return configured() and all(lang in TRANSLATE_LANGUAGES for lang in languages)


def tts_supported(lang):
    return configured() and lang in TTS_LANGUAGES


# ------------------------------------------------------------------
# HTTP
# ------------------------------------------------------------------

def _request(path, json=None, files=None, data=None):
    if not configured():
        raise SarvamError("SARVAM_API_KEY is not configured")

    last_error = None

    for attempt in range(2):
        try:
            response = requests.post(
                f"{base_url()}{path}",
                headers={"api-subscription-key": api_key()},
                json=json,
                files=files,
                data=data,
                timeout=TIMEOUT_SECONDS
            )

        except requests.RequestException as e:
            last_error = f"Sarvam request failed: {e}"
            continue

        if response.status_code == 200:
            try:
                return response.json()
            except ValueError as e:
                raise SarvamError("Sarvam returned an invalid response") from e

        # The error body never contains our key; keep the message only
        try:
            message = response.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            message = response.text[:200]

        last_error = f"Sarvam error {response.status_code}: {message}"

        if response.status_code not in RETRY_STATUSES:
            break

        time.sleep(1.0 + attempt)

    raise SarvamError(last_error or "Sarvam request failed")


# ------------------------------------------------------------------
# Translation
# ------------------------------------------------------------------

def translate_model(source, target):
    forced = os.getenv("SARVAM_TRANSLATE_MODEL")

    if forced:
        return forced

    if source in MAJOR_LANGUAGES and target in MAJOR_LANGUAGES:
        return "mayura:v1"

    return "sarvam-translate:v1"


def split_text(text, limit):
    """Split long text at sentence ends so each piece fits `limit` characters."""

    text = text.strip()

    if len(text) <= limit:
        return [text]

    sentences = re.split(r"(?<=[.!?।؟])\s+", text)

    pieces, current = [], ""

    for sentence in sentences:
        # A single sentence longer than the limit: cut it hard
        while len(sentence) > limit:
            if current:
                pieces.append(current)
                current = ""

            pieces.append(sentence[:limit])
            sentence = sentence[limit:]

        if len(current) + len(sentence) + 1 > limit:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()

    if current:
        pieces.append(current)

    return pieces


def _translate_piece(text, source, target, model):
    data = _request("/translate", json={
        "input": text,
        "source_language_code": SARVAM_CODES[source],
        "target_language_code": SARVAM_CODES[target],
        "model": model,
    })

    try:
        return data["translated_text"]
    except (KeyError, TypeError) as e:
        raise SarvamError("Unexpected translation response") from e


def translate(text, source, target):
    """Translate one text. Long texts are split at sentence ends."""

    if source == target or not text or not text.strip():
        return text

    if not (source in TRANSLATE_LANGUAGES and target in TRANSLATE_LANGUAGES):
        raise SarvamError(f"Sarvam cannot translate {source} -> {target}")

    model = translate_model(source, target)
    limit = TRANSLATE_LIMITS.get(model, 1000)

    pieces = split_text(text, limit)

    return " ".join(_translate_piece(piece, source, target, model) for piece in pieces)


def translate_many(texts, source, target, workers=4):
    """
    Translate a list of strings (same order back). Sarvam has no batch
    endpoint, so a few requests run in parallel.
    """

    texts = list(texts)

    if source == target or not texts:
        return texts

    if len(texts) == 1:
        return [translate(texts[0], source, target)]

    with ThreadPoolExecutor(max_workers=min(workers, len(texts))) as pool:
        return list(pool.map(lambda text: translate(text, source, target), texts))


def identify_language(text):
    """
    Which language is `text` written in? Returns our language code or None.
    Useful for scripts shared by several languages (Devanagari: Hindi /
    Marathi). Bhojpuri comes back as Hindi.
    """

    data = _request("/text-lid", json={"input": text[:500]})

    return FROM_SARVAM.get(data.get("language_code"))


# ------------------------------------------------------------------
# Speech to text
# ------------------------------------------------------------------

def speech_to_text(audio_bytes, mime_type="audio/wav"):
    """
    Transcribe an audio clip. The language is detected automatically.
    Returns (text, our_language_code or None).
    """

    extension = {
        "audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3",
        "audio/ogg": "ogg", "audio/webm": "webm", "audio/mp4": "mp4",
        "audio/aac": "aac", "audio/flac": "flac",
    }.get(mime_type.split(";")[0].strip().lower(), "wav")

    data = _request(
        "/speech-to-text",
        files={"file": (f"voice.{extension}", audio_bytes, mime_type)},
        data={
            "model": os.getenv("SARVAM_STT_MODEL", "saarika:v2.5"),
            "language_code": "unknown",
        }
    )

    try:
        text = (data["transcript"] or "").strip()
    except (KeyError, TypeError) as e:
        raise SarvamError("Unexpected speech response") from e

    return text, FROM_SARVAM.get(data.get("language_code"))


# ------------------------------------------------------------------
# Text to speech
# ------------------------------------------------------------------

def text_to_speech(text, lang):
    """Speech for `text` as WAV bytes (long text is cut at a sentence end)."""

    if lang not in TTS_LANGUAGES:
        raise SarvamError(f"Sarvam has no {lang} voice")

    text = split_text(text, TTS_LIMIT)[0]

    body = {"text": text, "target_language_code": SARVAM_CODES[lang]}

    if os.getenv("SARVAM_TTS_MODEL"):
        body["model"] = os.getenv("SARVAM_TTS_MODEL")

    if os.getenv("SARVAM_TTS_SPEAKER"):
        body["speaker"] = os.getenv("SARVAM_TTS_SPEAKER")

    data = _request("/text-to-speech", json=body)

    try:
        return base64.b64decode(data["audios"][0])
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise SarvamError("Unexpected text-to-speech response") from e
