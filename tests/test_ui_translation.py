import app.db.database as database
import app.routes.i18n_routes as i18n_routes
import app.services.translation_service as translation
from app.routes import voice_routes

LABELS = {"nav_home": "Home", "btn_send": "Send"}


def fake_translate(calls):
    def translate(texts, lang):
        calls.append((list(texts), lang))
        return [f"[{lang}] {text}" for text in texts]

    return translate


def test_labels_are_translated_and_cached(client, monkeypatch):
    voice_routes._hits.clear()
    calls = []
    monkeypatch.setattr(i18n_routes, "_translate_list", fake_translate(calls))

    first = client.post("/i18n/translate", json={"lang": "ml", "labels": LABELS}).json()

    assert first["labels"] == {"nav_home": "[ml] Home", "btn_send": "[ml] Send"}
    assert first["translated"] == 2

    second = client.post("/i18n/translate", json={"lang": "ml", "labels": LABELS}).json()

    assert second["labels"] == first["labels"]
    assert second["cached"] == 2 and second["translated"] == 0
    assert len(calls) == 1                       # the second request never called a translator

    assert database.get_database().ui_translations.count_documents({}) == 2


def test_only_new_labels_are_translated(client, monkeypatch):
    voice_routes._hits.clear()
    calls = []
    monkeypatch.setattr(i18n_routes, "_translate_list", fake_translate(calls))

    client.post("/i18n/translate", json={"lang": "bn", "labels": {"a": "Home"}})
    client.post("/i18n/translate", json={"lang": "bn", "labels": {"a": "Home", "b": "Send"}})

    assert calls[1][0] == ["Send"]


def test_english_and_unknown_languages(client):
    voice_routes._hits.clear()

    english = client.post("/i18n/translate", json={"lang": "en", "labels": LABELS}).json()
    assert english["labels"] == LABELS

    assert client.post("/i18n/translate", json={"lang": "xx", "labels": LABELS}).status_code == 400


def test_failed_translation_returns_nothing_and_caches_nothing(client, monkeypatch):
    voice_routes._hits.clear()

    def boom(texts, lang):
        raise RuntimeError("Gemini and Sarvam are down")

    monkeypatch.setattr(i18n_routes, "_translate_list", boom)

    body = client.post("/i18n/translate", json={"lang": "gu", "labels": LABELS}).json()

    assert body["labels"] == {}
    assert database.get_database().ui_translations.count_documents({}) == 0


def test_unchanged_translations_are_not_cached(client, monkeypatch):
    voice_routes._hits.clear()
    monkeypatch.setattr(i18n_routes, "_translate_list", lambda texts, lang: list(texts))

    body = client.post("/i18n/translate", json={"lang": "ur", "labels": LABELS}).json()

    assert body["labels"] == {}


def test_size_limits(client, monkeypatch):
    voice_routes._hits.clear()

    many = {f"k{i}": "x" for i in range(201)}
    assert client.post("/i18n/translate", json={"lang": "hi", "labels": many}).status_code == 413

    long_label = {"k": "x" * 201}
    assert client.post("/i18n/translate", json={"lang": "hi", "labels": long_label}).status_code == 413

    assert client.post("/i18n/translate", json={"lang": "hi", "labels": {}}).status_code == 422
