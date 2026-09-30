import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL_NAME = "gemini-2.5-flash"

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def generate_content(prompt):
    """Send a prompt to Gemini. The result has a .text attribute."""
    return client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )


def generate_with_audio(prompt, audio_bytes, mime_type):
    """Send a prompt plus an audio clip (speech understanding)."""
    from google.genai import types

    return client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            prompt,
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        ]
    )
