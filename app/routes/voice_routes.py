import base64
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from app.services import speech_service
from app.services.speech_service import MAX_AUDIO_BYTES, SpeechError
from app.services.translation_service import (
    normalize_language,
    translate_to_english,
    translate_to_user_language
)
from app.services.voice_commands import interpret

router = APIRouter(prefix="/voice")

# The voice endpoints cost Sarvam / Gemini quota and are usable without
# login (the farmer may not have an account), so limit requests per IP.
RATE_LIMIT = 30
RATE_WINDOW_SECONDS = 60

_hits = defaultdict(deque)


def rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    hits = _hits[ip]

    while hits and now - hits[0] > RATE_WINDOW_SECONDS:
        hits.popleft()

    if len(hits) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many voice requests. Please wait a minute."
        )

    hits.append(now)


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    lang: str = "en"


class CommandRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    lang: str | None = None


@router.post("/transcribe", dependencies=[Depends(rate_limit)])
async def transcribe(
    file: UploadFile = File(...),
    lang: str = Form(None)
):
    """Speech -> text. `lang` is the farmer's language (optional)."""

    audio = await file.read()

    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio is too long")

    try:
        result = speech_service.transcribe(
            audio,
            lang,
            mime_type=file.content_type or "audio/webm"
        )

    except SpeechError:
        raise HTTPException(
            status_code=422,
            detail="Could not understand the audio. Please try again."
        )

    return result


@router.post("/speak", dependencies=[Depends(rate_limit)])
def speak(request: SpeakRequest):
    """
    Text -> speech. Returns Sarvam audio (base64 WAV) when available.
    Otherwise provider is "browser": the app uses speechSynthesis.
    """

    lang = normalize_language(request.lang)

    audio = speech_service.synthesize(request.text, lang)

    if audio is None:
        return {"provider": "browser", "lang": lang}

    return {
        "provider": "sarvam",
        "lang": lang,
        "mime": "audio/wav",
        "audio_base64": base64.b64encode(audio).decode("ascii")
    }


@router.post("/command", dependencies=[Depends(rate_limit)])
def command(request: CommandRequest):
    """Spoken sentence -> what the app should do (validated)."""

    english, detected = translate_to_english(request.text, request.lang)
    lang = normalize_language(request.lang or detected)

    result = interpret(english)

    labels = {
        "weather": "Opening weather",
        "price": "Opening price prediction",
        "search_equipment": "Searching equipment",
        "ask": "Opening the assistant",
        "navigate": "Opening the page",
    }

    return {
        **result,
        "heard": english,
        "lang": lang,
        "reply": translate_to_user_language(labels[result["action"]], lang)
    }
