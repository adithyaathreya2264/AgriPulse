import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL_NAME = "gemini-2.5-flash"

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# Each Gemini model has its own free daily quota. When one is used up (429), the next one is tried.
FALLBACK_MODELS = [
    name.strip()
    for name in os.getenv(
        "GEMINI_FALLBACK_MODELS", "gemini-flash-latest,gemini-flash-lite-latest"
    ).split(",")
    if name.strip()
]


def _quota_error(error):
    text = str(error)

    return "429" in text or "RESOURCE_EXHAUSTED" in text or "503" in text or "UNAVAILABLE" in text


def _generate(contents):
    last_error = None

    for model in [MODEL_NAME] + FALLBACK_MODELS:
        try:
            return client.models.generate_content(model=model, contents=contents)
        except Exception as error:
            if not _quota_error(error):
                raise

            last_error = error

    raise last_error


def generate_content(prompt):
    """Send a prompt to Gemini. The result has a .text attribute."""
    return _generate(prompt)


def generate_with_audio(prompt, audio_bytes, mime_type):
    """Send a prompt plus an audio clip (speech understanding)."""
    from google.genai import types

    return _generate([
        prompt,
        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
    ])
