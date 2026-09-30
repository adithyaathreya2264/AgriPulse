import app.services.translation_service as translation


class FakeResponse:
    def __init__(self, text):
        self.text = text


def test_english_text_is_not_translated(monkeypatch):
    def boom(prompt):
        raise AssertionError("Gemini must not be called")

    monkeypatch.setattr(translation, "generate_content", boom)

    assert translation.translate_to_english("price tomato") == ("price tomato", "en")


def test_detects_language(monkeypatch):
    monkeypatch.setattr(
        translation, "generate_content",
        lambda prompt: FakeResponse('{"lang": "hi", "english": "weather Mysuru"}')
    )

    assert translation.translate_to_english("मौसम मैसूर") == ("weather Mysuru", "hi")


def test_translation_failure_falls_back_to_original(monkeypatch):
    def boom(prompt):
        raise RuntimeError("Gemini down")

    monkeypatch.setattr(translation, "generate_content", boom)

    assert translation.translate_to_english("मौसम") == ("मौसम", "en")
    assert translation.translate_to_user_language("Hello", "hi") == "Hello"

    payload = {"advice": "Irrigate", "temperature": 30}
    assert translation.translate_payload(payload, "kn") == payload


def test_translate_payload_only_touches_text_fields(monkeypatch):
    monkeypatch.setattr(
        translation, "generate_content",
        lambda prompt: FakeResponse('["A", "B", "C", "D"]')
    )

    payload = {
        "city": "Mysuru",
        "temperature": 30,
        "advice": "Irrigate crops",
        "analysis": {"cause": "Fungus", "precautions": ["Spray", "Drain"]}
    }

    result = translation.translate_payload(payload, "hi")

    assert result["city"] == "Mysuru"
    assert result["temperature"] == 30
    assert result["advice"] == "A"
    assert result["analysis"]["cause"] == "B"
    assert result["analysis"]["precautions"] == ["C", "D"]
    assert payload["advice"] == "Irrigate crops"  # original untouched


def test_english_target_returns_payload_unchanged():
    payload = {"advice": "x"}

    assert translation.translate_payload(payload, "en") is payload
    assert translation.normalize_language("xx") == "en"
    assert translation.normalize_language("KN") == "kn"
