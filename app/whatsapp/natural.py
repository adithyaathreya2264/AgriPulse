"""
Everyday phrases ("tell me the weather in Mysore", "what is the price of
tomato today", "I want to rent a tractor") -> the same commands as the short
forms ("weather Mysore", "price tomato").

Only short messages are treated as commands, so a real question such as
"will the weather affect blight on my tomato leaves" still goes to the
assistant.
"""

import re

WORD = re.compile(r"[^\W\d_]+(?:['\-][^\W\d_]+)*", re.UNICODE)

# Words that are never part of a crop or place name
FILLER = {
    "today", "now", "tomorrow", "please", "like", "currently", "current", "latest",
    "the", "a", "an", "of", "in", "at", "for", "is", "are", "what", "whats", "what's",
    "how", "much", "tell", "me", "show", "give", "check", "market", "mandi", "my",
    "price", "prices", "rate", "rates", "weather", "temperature", "can", "you", "i",
    "want", "to", "know", "about", "get", "need", "and", "its", "it", "s", "do", "does",
}

TRAILING = {"today", "now", "tomorrow", "please", "currently", "tonight", "right"}
PREPOSITIONS = {"in", "at", "for", "of", "near"}

WEATHER_WORDS = {"weather", "temperature", "mausam"}
PRICE_WORDS = {"price", "prices", "rate", "rates", "mandi"}
EQUIPMENT_WORDS = {
    "tractor", "tractors", "harvester", "harvesters", "drone", "drones",
    "rotavator", "rotavators", "cultivator", "sprayer", "equipment", "machine", "machines",
}
EQUIPMENT_INTENT = {"rent", "hire", "book", "borrow", "near", "nearby", "available", "need", "want", "find"}
LOAN_WORDS = {"loan", "loans", "kcc"}
BOOKING_WORDS = {"booking", "bookings", "rental", "rentals"}

MAX_WORDS = {"weather": 8, "price": 10, "equipment": 8, "loan": 8, "language": 5, "bookings": 5}


def _tokens(text):
    return WORD.findall(text)


LEADING_NOISE = {"in", "at", "for", "of", "near", "the", "forecast", "report", "today", "now", "to", "is", "how"}
PLACE_NOISE = {"mandi", "market", "district", "city", "town"}


def clean_place(text):
    """"in Kolar", "forecast for Hassan today", "Kolar mandi" -> "Kolar" """

    tokens = _tokens(text or "")

    while tokens and tokens[0].lower() in LEADING_NOISE:
        tokens = tokens[1:]

    while tokens and tokens[-1].lower() in TRAILING | PLACE_NOISE:
        tokens = tokens[:-1]

    return " ".join(tokens[:3])


def _place_after(tokens, prepositions=PREPOSITIONS, start=0):
    """The words after the last "in / at / for / of" (a city, district or market)."""

    # Drop trailing filler: "... in Mysore today please"
    end = len(tokens)

    while end > start and tokens[end - 1].lower() in TRAILING:
        end -= 1

    for index in range(end - 1, start - 1, -1):
        if tokens[index].lower() in prepositions:
            place = [t for t in tokens[index + 1:end] if t.lower() not in PLACE_NOISE]

            return " ".join(place[:3]) if place else ""

    return ""


def _crop(tokens):
    """The crop in a price question."""

    lowered = [token.lower() for token in tokens]

    for index, word in enumerate(lowered):
        if word not in PRICE_WORDS:
            continue

        # "price of tomato" / "rate for onion in Kolar"
        after = lowered[index + 1:]

        if after and after[0] in ("of", "for"):
            crop = []

            for token, original in zip(after[1:], tokens[index + 2:]):
                if token in PREPOSITIONS or token in TRAILING:
                    break

                crop.append(original)

            if crop:
                return " ".join(crop[:2])

        # "tomato price" / "what is the onion rate today"
        before = [
            original for token, original in zip(lowered[:index], tokens[:index])
            if token not in FILLER
        ]

        if before:
            return " ".join(before[-2:])

    return ""


def natural_command(cased):
    """(command, argument) for an everyday phrase, or None."""

    tokens = _tokens(cased)
    lowered = {token.lower() for token in tokens}
    count = len(tokens)

    if not tokens:
        return None

    if lowered & WEATHER_WORDS and count <= MAX_WORDS["weather"]:
        return "weather", _place_after(tokens)

    if lowered & PRICE_WORDS and count <= MAX_WORDS["price"]:
        crop = _crop(tokens)
        place = _place_after(tokens)

        # "price of tomato in Kolar" -> "tomato, Kolar"
        if crop and place and place.lower() != crop.lower():
            return "price", f"{crop}, {place}"

        return "price", crop

    if lowered & EQUIPMENT_WORDS and lowered & EQUIPMENT_INTENT and count <= MAX_WORDS["equipment"]:
        return "equipment", ""

    if lowered & LOAN_WORDS and count <= MAX_WORDS["loan"]:
        return "loan", ""

    if "language" in lowered and count <= MAX_WORDS["language"]:
        rest = [token for token in tokens if token.lower() not in FILLER | {"language", "change", "switch", "set"}]

        return "language", " ".join(rest)

    if lowered & BOOKING_WORDS and count <= MAX_WORDS["bookings"]:
        return "bookings", ""

    return None
