"""
On-demand translation of the app's UI labels.

The frontend ships hand-written labels for a few languages. For any other
language it sends the missing English labels here; they are translated once
(Sarvam first, Gemini as the fallback) and cached in MongoDB, so every
later farmer gets them instantly.
"""

import hashlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.routes.voice_routes import rate_limit
from app.services.translation_service import (
    SUPPORTED_LANGUAGES,
    _translate_list,
    normalize_language
)

router = APIRouter(prefix="/i18n")

MAX_LABELS = 200
MAX_LABEL_LENGTH = 200


class TranslateRequest(BaseModel):
    lang: str
    labels: dict[str, str] = Field(min_length=1)


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


@router.post("/translate", dependencies=[Depends(rate_limit)])
def translate_labels(request: TranslateRequest, db=Depends(get_db)):
    """
    {lang, labels: {key: english}} -> {lang, labels: {key: translated}}.
    Labels that cannot be translated are left out (the app shows English).
    """

    lang = request.lang.strip().lower()

    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail="Unsupported language")

    lang = normalize_language(lang)

    if lang == "en":
        return {"lang": "en", "labels": request.labels, "cached": 0, "translated": 0}

    if len(request.labels) > MAX_LABELS:
        raise HTTPException(status_code=413, detail=f"At most {MAX_LABELS} labels per request")

    if any(len(text) > MAX_LABEL_LENGTH for text in request.labels.values()):
        raise HTTPException(status_code=413, detail="A label is too long")

    result = {}
    missing = {}

    for key, text in request.labels.items():
        cached = db.ui_translations.find_one({"lang": lang, "hash": text_hash(text)})

        if cached:
            result[key] = cached["translation"]
        else:
            missing[key] = text

    translated_count = 0

    if missing:
        keys = list(missing)

        try:
            translations = _translate_list([missing[key] for key in keys], lang)

            documents = []

            for key, translation in zip(keys, translations):
                if not translation or translation.strip() == missing[key].strip():
                    continue

                result[key] = translation

                documents.append({
                    "lang": lang,
                    "hash": text_hash(missing[key]),
                    "source": missing[key],
                    "translation": translation
                })

            if documents:
                db.ui_translations.insert_many(documents)
                translated_count = len(documents)

        except Exception as e:
            print("UI translation error:", e)

    return {
        "lang": lang,
        "labels": result,
        "cached": len(result) - translated_count,
        "translated": translated_count
    }
