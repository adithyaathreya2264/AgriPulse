"""Translating the bot's English answers into the farmer's language."""

import hashlib

from pymongo.errors import DuplicateKeyError

from app.services.translation_service import _translate_list, translate_to_user_language


def _hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def translate_multiline(text, lang):
    """
    Translate line by line so lists, menus and reports keep their layout
    (translating a whole block at once removes the line breaks).
    """

    lines = text.split("\n")

    # Lines that are only numbers / emoji / spaces stay as they are
    indexes = [i for i, line in enumerate(lines) if any(char.isalpha() for char in line)]

    if not indexes:
        return text

    if len(indexes) == 1:
        lines[indexes[0]] = translate_to_user_language(lines[indexes[0]], lang)

    else:
        translated = _translate_list([lines[i] for i in indexes], lang)

        for index, line in zip(indexes, translated):
            lines[index] = line

    return "\n".join(lines)


def translate_cached(db, text, lang):
    """
    Fixed texts (menu, questions) are translated once and remembered in
    MongoDB, so every farmer after the first gets them instantly.
    """

    cached = db.ui_translations.find_one({"lang": lang, "hash": _hash(text)})

    if cached:
        return cached["translation"]

    translated = translate_multiline(text, lang)

    if translated and translated.strip() != text.strip():
        try:
            db.ui_translations.insert_one({
                "lang": lang, "hash": _hash(text),
                "source": text, "translation": translated
            })
        except DuplicateKeyError:
            pass

    return translated


def localize(db, texts, lang, static=False):
    """English replies -> the farmer's language (failures keep the English)."""

    if lang == "en":
        return list(texts)

    translate = translate_cached if static else (lambda _db, text, code: translate_multiline(text, code))

    result = []

    for text in texts:
        try:
            result.append(translate(db, text, lang))
        except Exception as e:
            print("Localization error:", e)
            result.append(text)

    return result
