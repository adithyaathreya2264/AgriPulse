"""Photos and voice notes: downloading them and making voice replies."""

import os
import time
import uuid

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from app.services import speech_service

load_dotenv()

UPLOAD_DIR = "uploads"
TTS_DIR = os.path.join(UPLOAD_DIR, "tts")
FEEDBACK_DIR = os.path.join(UPLOAD_DIR, "feedback")

for folder in (TTS_DIR, FEEDBACK_DIR):
    os.makedirs(folder, exist_ok=True)

VOICE_REPLY_MAX_CHARS = 600
TTS_KEEP_SECONDS = 24 * 3600

# Photos that were not confirmed / corrected are removed after this long
PHOTO_KEEP_SECONDS = 24 * 3600


def public_base_url():
    return (os.getenv("PUBLIC_BASE_URL") or "").rstrip("/")


def download_media(media_url):
    """The bytes of a photo / voice note Twilio holds for us, or None."""

    try:
        response = requests.get(
            media_url,
            auth=HTTPBasicAuth(
                os.getenv("TWILIO_ACCOUNT_SID") or "",
                os.getenv("TWILIO_AUTH_TOKEN") or ""
            ),
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30
        )

        if response.status_code == 200:
            return response.content

        print("Media download failed. Status:", response.status_code)

    except Exception as e:
        print("Media download error:", e)

    return None


def _remove_old_files(folder, max_age_seconds):
    now = time.time()

    for name in os.listdir(folder):
        path = os.path.join(folder, name)

        if os.path.isfile(path) and now - os.path.getmtime(path) > max_age_seconds:
            os.remove(path)


def save_photo(image_bytes):
    """Store a photo for the diagnosis. Returns its path."""

    _remove_old_files(UPLOAD_DIR, PHOTO_KEEP_SECONDS)

    path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.jpg")

    with open(path, "wb") as f:
        f.write(image_bytes)

    return path


def keep_photo_for_training(path):
    """Move a photo the farmer corrected into the folder for retraining."""

    if not path or not os.path.exists(path):
        return None

    target = os.path.join(FEEDBACK_DIR, os.path.basename(path))
    os.replace(path, target)

    return target


def delete_photo(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def save_voice_reply(text, lang):
    """
    Speak `text` (Sarvam) and return the public URL of an mp3, or None when
    voice replies are not possible (no Sarvam voice / no public URL).
    """

    base = public_base_url()

    if not base:
        return None

    audio = speech_service.synthesize(text[:VOICE_REPLY_MAX_CHARS], lang)

    if audio is None:
        return None

    try:
        mp3 = speech_service.wav_to_mp3(audio)
    except Exception as e:
        print("Voice reply conversion failed:", e)
        return None

    _remove_old_files(TTS_DIR, TTS_KEEP_SECONDS)

    name = f"{uuid.uuid4().hex}.mp3"

    with open(os.path.join(TTS_DIR, name), "wb") as f:
        f.write(mp3)

    return f"{base}/media/tts/{name}"
