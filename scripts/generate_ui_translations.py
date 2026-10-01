"""
Fill the UI label files kisanmitra-frontend/src/i18n/<lang>.json.

English (en.json) is the source. For every other supported language the labels
that are missing are translated and written back, so GEMINI_API_KEY and/or
SARVAM_API_KEY must be in .env.

    python scripts/generate_ui_translations.py                # only missing labels
    python scripts/generate_ui_translations.py --langs ml bn  # some languages
    python scripts/generate_ui_translations.py --force        # redo everything
    python scripts/generate_ui_translations.py --provider sarvam

Gemini (default) translates about 50 labels per request and is told to keep the
{placeholders}, numbers, units and product names; Sarvam translates one label
per request. Every result is checked: a label whose {placeholders} do not match
the English one is retried and, if it still differs, left out (the app then
shows English for that one label instead of a broken sentence).

Machine translations of short UI labels are usually good but not perfect:
have a native speaker skim the generated files before a public release.
"""

import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.gemini_client import client as gemini  # noqa: E402
from app.services.translation_service import (  # noqa: E402
    SUPPORTED_LANGUAGES,
    _clean_json,
    _translate_list,
)

I18N_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "kisanmitra-frontend", "src", "i18n"
)

# gemini-flash-latest has its own free quota (the app's default model allows only 20 requests a day)
MODEL = os.getenv("UI_TRANSLATION_MODEL", "gemini-flash-latest")
CHUNK = 50
PLACEHOLDER = re.compile(r"\{\w+\}")

# Names and terms that must stay as they are in every language
KEEP = "AgriPulse, KisanMitra AI, Kisan Credit Card, KCC, DigiLocker, UPI, OTP, WhatsApp, Razorpay, GPS, AI, PAN, Aadhaar, RTC, Pahani, pH"


def load(code):
    path = os.path.join(I18N_DIR, f"{code}.json")

    if not os.path.exists(path):
        return {}

    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(code, data):
    path = os.path.join(I18N_DIR, f"{code}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def valid(english, translated):
    """A usable translation: text, and the same {placeholders} as the English."""

    if not isinstance(translated, str) or not translated.strip():
        return False

    return sorted(PLACEHOLDER.findall(english)) == sorted(PLACEHOLDER.findall(translated))


def gemini_chunk(chunk, code):
    prompt = f"""
You translate the user interface of a farming app for Indian farmers into {SUPPORTED_LANGUAGES[code]}.

Rules:
- Natural, short, polite UI wording that a farmer understands. Use the script normally used for {SUPPORTED_LANGUAGES[code]}.
- Keep every {{placeholder}} (for example {{name}}, {{n}}, {{km}}) exactly as written, with its braces.
- Keep numbers, the rupee sign, units (km, m, kg/ha) and symbols unchanged.
- Keep these names unchanged: {KEEP}.
- Keep line breaks (\\n) where they are. Keep trailing colons, dots and ellipses.
- The key shows where the text is used; do not translate keys.

Return ONLY a JSON object with exactly the same keys and the translated texts as values.

{json.dumps(chunk, ensure_ascii=False, indent=1)}
"""

    # the free Gemini quota is per minute: wait and try again when it says so
    for wait in (0, 40, 70):
        time.sleep(wait)

        try:
            data = json.loads(_clean_json(gemini.models.generate_content(model=MODEL, contents=prompt).text))
            return data if isinstance(data, dict) else {}
        except Exception as e:
            if "429" not in str(e) and "RESOURCE_EXHAUSTED" not in str(e):
                raise

    raise RuntimeError("Gemini quota exceeded")


def sarvam_list(chunk, code):
    """One request per label; {placeholders} are hidden behind tokens first."""

    keys = list(chunk)
    hidden = []

    for key in keys:
        tokens = {}

        def hide(match):
            token = f"XQ{len(tokens)}X"
            tokens[token] = match.group(0)
            return token

        hidden.append((PLACEHOLDER.sub(hide, chunk[key]), tokens))

    translated = _translate_list([text for text, _ in hidden], code)
    result = {}

    for key, (_, tokens), text in zip(keys, hidden, translated):
        for token, original in tokens.items():
            text = text.replace(token, original)

        result[key] = text

    return result


def translate_labels(english, keys, code, provider):
    done = {}
    todo = list(keys)

    for attempt in range(2):
        failed = []

        for start in range(0, len(todo), CHUNK):
            chunk = {key: english[key] for key in todo[start:start + CHUNK]}

            try:
                answer = sarvam_list(chunk, code) if provider == "sarvam" else gemini_chunk(chunk, code)
            except Exception as e:
                print(f"    {code}: a request failed ({str(e)[:120]})")
                failed.extend(chunk)
                continue

            for key, text in chunk.items():
                if valid(text, answer.get(key)):
                    done[key] = answer[key].strip() if "\n" not in text else answer[key]
                else:
                    failed.append(key)

        todo = failed

        if not todo:
            break

        # second round: one label at a time through the other provider
        provider = "sarvam" if provider == "gemini" else "gemini"

    return done, todo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--langs", nargs="*", help="language codes (default: all)")
    parser.add_argument("--force", action="store_true", help="retranslate every label")
    parser.add_argument("--provider", choices=["gemini", "sarvam"], default="gemini")
    args = parser.parse_args()

    english = load("en")
    languages = args.langs or [code for code in SUPPORTED_LANGUAGES if code != "en"]

    for code in languages:
        if code not in SUPPORTED_LANGUAGES or code == "en":
            print(f"Skipping unknown/English language: {code}")
            continue

        current = load(code)

        keys = [key for key in english if args.force or not current.get(key)]

        if not keys:
            print(f"{code}: up to date")
            continue

        done, left = translate_labels(english, keys, code, args.provider)

        current.update(done)

        # Keep the same key order as English
        save(code, {key: current[key] for key in english if key in current})

        print(f"{code} ({SUPPORTED_LANGUAGES[code]}): {len(done)} translated, {len(left)} left in English")


if __name__ == "__main__":
    main()
