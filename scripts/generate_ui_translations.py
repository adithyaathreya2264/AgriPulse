"""
Fill the UI label files kisanmitra-frontend/src/i18n/<lang>.json.

English (en.json) is the source. For every other supported language the
labels that are missing are translated with the app's translation service
(Sarvam first, Gemini as the fallback), so GEMINI_API_KEY and/or
SARVAM_API_KEY must be in .env.

    python scripts/generate_ui_translations.py                # only missing labels
    python scripts/generate_ui_translations.py --langs ml bn  # some languages
    python scripts/generate_ui_translations.py --force        # redo everything

Machine translations of short UI labels are usually good but not perfect:
have a native speaker skim the generated files before a public release.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.translation_service import (  # noqa: E402
    SUPPORTED_LANGUAGES,
    _translate_list,
)

I18N_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "kisanmitra-frontend", "src", "i18n"
)


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--langs", nargs="*", help="language codes (default: all)")
    parser.add_argument("--force", action="store_true", help="retranslate every label")
    args = parser.parse_args()

    english = load("en")
    languages = args.langs or [code for code in SUPPORTED_LANGUAGES if code != "en"]

    for code in languages:
        if code not in SUPPORTED_LANGUAGES or code == "en":
            print(f"Skipping unknown/English language: {code}")
            continue

        current = load(code)

        keys = [
            key for key in english
            if args.force or not current.get(key)
        ]

        if not keys:
            print(f"{code}: up to date")
            continue

        try:
            translated = _translate_list([english[key] for key in keys], code)
        except Exception as e:
            print(f"{code}: FAILED ({e})")
            continue

        current.update(dict(zip(keys, translated)))

        # Keep the same key order as English
        save(code, {key: current[key] for key in english if key in current})

        print(f"{code} ({SUPPORTED_LANGUAGES[code]}): {len(keys)} labels translated")


if __name__ == "__main__":
    main()
