"""
Speech in / out for the whole app (web mic button and WhatsApp voice notes).

Speech-to-text, in order:
  1. Sarvam         (Indian languages, detects the language by itself)
  2. Gemini audio   (understands most dialects, detects the language)
  3. Google speech  (SpeechRecognition, last resort)

Text-to-speech: Sarvam voices (11 languages). When it is not available the
caller (browser) uses its own speechSynthesis voice.
"""

import io
import json

from app.ai.gemini_client import generate_with_audio
from app.services import sarvam_service
from app.services.translation_service import (
    SUPPORTED_LANGUAGES,
    normalize_language
)

MAX_AUDIO_BYTES = 10 * 1024 * 1024


class SpeechError(RuntimeError):
    """No provider could understand the audio."""


def to_wav_16k(audio_bytes):
    """Any browser / WhatsApp audio (webm, ogg, mp3, ...) -> 16 kHz mono WAV."""

    from pydub import AudioSegment

    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    audio = audio.set_frame_rate(16000).set_channels(1)

    buffer = io.BytesIO()
    audio.export(buffer, format="wav")

    return buffer.getvalue()


def _sarvam_transcribe(audio_bytes, mime_type):
    """Returns (text, language or None)."""

    try:
        # A clean 16 kHz mono WAV is the safest input
        return sarvam_service.speech_to_text(to_wav_16k(audio_bytes), "audio/wav")

    except sarvam_service.SarvamError:
        raise

    except Exception as e:
        # No ffmpeg (or unreadable audio): let Sarvam try the original file
        print("Audio conversion failed, sending the original:", e)

        return sarvam_service.speech_to_text(audio_bytes, mime_type)


def _gemini_transcribe(audio_bytes, mime_type):
    prompt = f"""
Transcribe this speech exactly as spoken, in its original language.
Detect the language. Supported language codes:
{", ".join(SUPPORTED_LANGUAGES)}. Use "en" if unsure.

Return ONLY valid JSON, no markdown:
{{"lang": "<code>", "text": "<transcription>"}}
"""

    text = generate_with_audio(prompt, audio_bytes, mime_type).text
    text = text.replace("```json", "").replace("```", "").strip()

    data = json.loads(text)

    return data["text"].strip(), normalize_language(data.get("lang"))


def _google_transcribe(audio_bytes, lang):
    import speech_recognition as sr

    wav = to_wav_16k(audio_bytes)

    recognizer = sr.Recognizer()

    with sr.AudioFile(io.BytesIO(wav)) as source:
        audio = recognizer.record(source)

    google_codes = {
        "en": "en-IN", "hi": "hi-IN", "kn": "kn-IN", "te": "te-IN",
        "ta": "ta-IN", "ml": "ml-IN", "mr": "mr-IN", "bn": "bn-IN",
        "gu": "gu-IN", "pa": "pa-IN", "or": "or-IN", "ur": "ur-IN",
    }

    return recognizer.recognize_google(audio, language=google_codes.get(lang, "en-IN"))


def transcribe(audio_bytes, lang=None, mime_type="audio/webm"):
    """
    Returns {"text", "lang", "provider"}.
    Raises SpeechError when nothing could be transcribed.
    """

    if not audio_bytes:
        raise SpeechError("Empty audio")

    lang = normalize_language(lang) if lang else None

    errors = []

    # 1. Sarvam (finds the language itself; `lang` is only a fallback)
    if sarvam_service.configured():
        try:
            text, detected = _sarvam_transcribe(audio_bytes, mime_type)

            if text:
                return {
                    "text": text,
                    "lang": detected or lang or "en",
                    "provider": "sarvam"
                }

        except Exception as e:
            errors.append(f"sarvam: {e}")

    # 2. Gemini
    try:
        text, detected = _gemini_transcribe(audio_bytes, mime_type)

        if text:
            return {"text": text, "lang": detected, "provider": "gemini"}

    except Exception as e:
        errors.append(f"gemini: {e}")

    # 3. Google speech recognition
    try:
        text = _google_transcribe(audio_bytes, lang or "en")

        if text:
            return {"text": text, "lang": lang or "en", "provider": "google"}

    except Exception as e:
        errors.append(f"google: {e}")

    print("Speech errors:", errors)

    raise SpeechError("Could not understand the audio")


def synthesize(text, lang):
    """
    Speech for `text` as WAV bytes, or None when Sarvam cannot do it
    (the browser then uses its own voice).
    """

    lang = normalize_language(lang)

    if not text or not sarvam_service.tts_supported(lang):
        return None

    try:
        return sarvam_service.text_to_speech(text, lang)

    except sarvam_service.SarvamError as e:
        print("Sarvam TTS failed:", e)
        return None


def wav_to_mp3(wav_bytes):
    """WhatsApp plays mp3 voice notes; Sarvam returns WAV."""

    from pydub import AudioSegment

    buffer = io.BytesIO()

    AudioSegment.from_file(io.BytesIO(wav_bytes)).export(buffer, format="mp3")

    return buffer.getvalue()
