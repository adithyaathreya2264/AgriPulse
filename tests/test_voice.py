import base64

import pytest
import requests

import app.routes.voice_routes as voice_routes
import app.services.translation_service as translation
from app.services import sarvam_service, speech_service, voice_commands
from app.services.speech_service import SpeechError


class FakeResponse:
    def __init__(self, data=None, text=""):
        self._data = data
        self.text = text

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    voice_routes._hits.clear()

    monkeypatch.delenv("SARVAM_API_KEY", raising=False)


@pytest.fixture
def sarvam_env(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")


# ---------------------------------------------------------------- languages

def test_at_least_twelve_languages():
    assert len(translation.SUPPORTED_LANGUAGES) >= 12

    for code in ("kn", "te", "mr", "bho", "pa"):
        assert code in translation.SUPPORTED_LANGUAGES


@pytest.mark.parametrize("text,expected", [
    ("ಹವಾಮಾನ ಮೈಸೂರು", "kn"),
    ("వాతావరణం", "te"),
    ("வானிலை", "ta"),
    ("കാലാവസ്ഥ", "ml"),
    ("ਮੌਸਮ", "pa"),
    ("હવામાન", "gu"),
    ("मौसम", "devanagari"),
    ("weather", None),
])
def test_script_detection(text, expected):
    assert translation.detect_script_language(text) == expected


def test_devanagari_uses_the_hint():
    assert translation.detect_script_language("मौसम", hint="mr") == "mr"
    assert translation.detect_script_language("মৌসুম", hint="as") == "as"


# ---------------------------------------------------------------- translation providers

def test_sarvam_is_used_first_and_gemini_is_not_called(sarvam_env, monkeypatch):
    monkeypatch.setattr(
        sarvam_service, "translate", lambda text, src, tgt: f"[{src}->{tgt}] {text}"
    )

    def boom(prompt):
        raise AssertionError("Gemini must not be called")

    monkeypatch.setattr(translation, "generate_content", boom)

    assert translation.translate_to_english("ಹವಾಮಾನ") == ("[kn->en] ಹವಾಮಾನ", "kn")
    assert translation.translate_to_user_language("Rain", "ta") == "[en->ta] Rain"


def test_gemini_takes_over_when_sarvam_fails(sarvam_env, monkeypatch):
    def failing(*args):
        raise sarvam_service.SarvamError("down")

    monkeypatch.setattr(sarvam_service, "translate", failing)
    monkeypatch.setattr(sarvam_service, "translate_many", failing)
    monkeypatch.setattr(
        translation, "generate_content", lambda prompt: FakeResponse(text="GEMINI OUTPUT")
    )

    assert translation.translate_to_user_language("Rain", "ta") == "GEMINI OUTPUT"


def test_bhojpuri_goes_to_gemini_even_with_sarvam(sarvam_env, monkeypatch):
    def boom(*args):
        raise AssertionError("Sarvam does not serve Bhojpuri")

    monkeypatch.setattr(sarvam_service, "translate", boom)
    monkeypatch.setattr(
        translation, "generate_content", lambda prompt: FakeResponse(text="भोजपुरी")
    )

    assert translation.translate_to_user_language("Rain", "bho") == "भोजपुरी"


def test_payload_translation_uses_one_sarvam_call(sarvam_env, monkeypatch):
    calls = []

    def many(texts, src, tgt):
        calls.append(list(texts))
        return [f"{tgt}:{text}" for text in texts]

    monkeypatch.setattr(sarvam_service, "translate_many", many)

    result = translation.translate_payload(
        {"city": "Mysuru", "advice": "Irrigate", "analysis": {"cause": "Fungus"}}, "kn"
    )

    assert calls == [["Irrigate", "Fungus"]]
    assert result["advice"] == "kn:Irrigate"
    assert result["city"] == "Mysuru"


# ---------------------------------------------------------------- speech providers

def test_transcribe_prefers_sarvam(sarvam_env, monkeypatch):
    monkeypatch.setattr(speech_service, "_sarvam_transcribe", lambda audio, mime: ("ಹವಾಮಾನ", "kn"))

    def boom(*args):
        raise AssertionError("Gemini must not run when Sarvam worked")

    monkeypatch.setattr(speech_service, "_gemini_transcribe", boom)

    result = speech_service.transcribe(b"audio")

    assert result == {"text": "ಹವಾಮಾನ", "lang": "kn", "provider": "sarvam"}


def test_transcribe_falls_back_to_gemini_then_google(sarvam_env, monkeypatch):
    def failing(*args):
        raise RuntimeError("down")

    monkeypatch.setattr(speech_service, "_sarvam_transcribe", failing)
    monkeypatch.setattr(speech_service, "_gemini_transcribe", lambda audio, mime: ("hello", "en"))

    assert speech_service.transcribe(b"audio", "kn")["provider"] == "gemini"

    monkeypatch.setattr(speech_service, "_gemini_transcribe", failing)
    monkeypatch.setattr(speech_service, "_google_transcribe", lambda audio, lang: "hello")

    assert speech_service.transcribe(b"audio", "kn")["provider"] == "google"


def test_transcribe_without_sarvam_uses_gemini_and_detects_language(monkeypatch):
    monkeypatch.setattr(
        speech_service, "_gemini_transcribe", lambda audio, mime: ("मौसम", "hi")
    )

    assert speech_service.transcribe(b"audio") == {
        "text": "मौसम", "lang": "hi", "provider": "gemini"
    }


def test_transcribe_raises_when_everything_fails(monkeypatch):
    def failing(*args):
        raise RuntimeError("down")

    monkeypatch.setattr(speech_service, "_gemini_transcribe", failing)
    monkeypatch.setattr(speech_service, "_google_transcribe", failing)

    with pytest.raises(SpeechError):
        speech_service.transcribe(b"audio", "en")

    with pytest.raises(SpeechError):
        speech_service.transcribe(b"")


def test_synthesize_needs_sarvam(monkeypatch):
    assert speech_service.synthesize("hello", "hi") is None


def test_synthesize_uses_sarvam(sarvam_env, monkeypatch):
    monkeypatch.setattr(sarvam_service, "text_to_speech", lambda text, lang: b"WAV")

    assert speech_service.synthesize("नमस्ते", "hi") == b"WAV"
    assert speech_service.synthesize("x", "bho") is None       # unsupported language


# ---------------------------------------------------------------- voice commands

@pytest.mark.parametrize("sentence,page,action,params", [
    ("what is the weather in Mysuru", "weather", "weather", {"city": "mysuru"}),
    ("price of tomato", "price", "price", {"crop": "tomato"}),
    ("I want to rent a tractor", "marketplace", "search_equipment", {"query": "tractor"}),
    ("show my loan options", "loan", "navigate", {}),
    ("open history", "history", "navigate", {}),
    ("my crop has yellow leaves what to do", "disease", "navigate", {}),
])
def test_keyword_fallback_commands(sentence, page, action, params):
    command = voice_commands.keyword_command(sentence)

    assert command["page"] == page
    assert command["action"] == action
    assert command["params"] == params


def test_unknown_sentence_goes_to_the_assistant():
    command = voice_commands.keyword_command("how do I improve my soil")

    assert command["action"] == "ask"
    assert command["page"] == "assistant"


def test_commands_are_validated(monkeypatch):
    dangerous = {
        "action": "delete_everything", "page": "admin",
        "params": {"city": "<script>alert(1)</script>Mysuru", "evil": "x", "crop": "a" * 500}
    }

    command = voice_commands.validate(dangerous)

    assert command["page"] in voice_commands.PAGES
    assert command["action"] in voice_commands.ACTIONS
    assert set(command["params"]) <= {"city", "crop", "query", "question"}
    assert "<" not in command["params"]["city"]
    assert len(command["params"]["crop"]) <= voice_commands.MAX_PARAM_LENGTH


def test_interpret_uses_gemini_then_falls_back(monkeypatch):
    monkeypatch.setattr(
        voice_commands, "generate_content",
        lambda prompt: FakeResponse(text='{"action": "weather", "page": "weather", "params": {"city": "Hassan"}}')
    )

    assert voice_commands.interpret("weather Hassan")["params"] == {"city": "Hassan"}

    def boom(prompt):
        raise RuntimeError("down")

    monkeypatch.setattr(voice_commands, "generate_content", boom)

    assert voice_commands.interpret("weather in Hassan")["params"] == {"city": "hassan"}


# ---------------------------------------------------------------- routes

def test_transcribe_route(client, monkeypatch):
    monkeypatch.setattr(
        speech_service, "transcribe",
        lambda audio, lang, mime_type: {"text": "hello", "lang": "en", "provider": "gemini"}
    )

    response = client.post(
        "/voice/transcribe",
        files={"file": ("voice.webm", b"fake-audio", "audio/webm")},
        data={"lang": "kn"}
    )

    assert response.status_code == 200
    assert response.json()["text"] == "hello"


def test_transcribe_route_reports_unintelligible_audio(client, monkeypatch):
    def fail(audio, lang, mime_type):
        raise SpeechError("nothing")

    monkeypatch.setattr(speech_service, "transcribe", fail)

    response = client.post(
        "/voice/transcribe", files={"file": ("v.webm", b"x", "audio/webm")}
    )

    assert response.status_code == 422


def test_transcribe_route_rejects_huge_audio(client, monkeypatch):
    monkeypatch.setattr(voice_routes, "MAX_AUDIO_BYTES", 10)

    response = client.post(
        "/voice/transcribe", files={"file": ("v.webm", b"x" * 50, "audio/webm")}
    )

    assert response.status_code == 413


def test_speak_route_uses_sarvam_audio_or_browser(client, monkeypatch):
    monkeypatch.setattr(speech_service, "synthesize", lambda text, lang: b"WAV")

    sarvam = client.post("/voice/speak", json={"text": "नमस्ते", "lang": "hi"}).json()
    assert sarvam["provider"] == "sarvam"
    assert base64.b64decode(sarvam["audio_base64"]) == b"WAV"

    monkeypatch.setattr(speech_service, "synthesize", lambda text, lang: None)

    browser = client.post("/voice/speak", json={"text": "ನಮಸ್ಕಾರ", "lang": "kn"}).json()
    assert browser == {"provider": "browser", "lang": "kn"}


def test_command_route(client, monkeypatch):
    monkeypatch.setattr(
        voice_routes, "interpret",
        lambda english: {"action": "weather", "page": "weather", "params": {"city": "Kolar"}}
    )

    response = client.post("/voice/command", json={"text": "weather in Kolar", "lang": "en"})

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == "weather"
    assert body["params"] == {"city": "Kolar"}
    assert body["heard"] == "weather in Kolar"


def test_voice_endpoints_are_rate_limited(client, monkeypatch):
    monkeypatch.setattr(voice_routes, "RATE_LIMIT", 3)
    monkeypatch.setattr(speech_service, "synthesize", lambda text, lang: None)

    codes = [
        client.post("/voice/speak", json={"text": "hi", "lang": "en"}).status_code
        for _ in range(5)
    ]

    assert codes == [200, 200, 200, 429, 429]


# ---------------------------------------------------------------- Sarvam specifics

def test_devanagari_text_is_resolved_with_sarvam_language_id(sarvam_env, monkeypatch):
    monkeypatch.setattr(sarvam_service, "identify_language", lambda text: "mr")
    monkeypatch.setattr(
        sarvam_service, "translate", lambda text, src, tgt: f"[{src}->{tgt}]"
    )

    def boom(prompt):
        raise AssertionError("Gemini must not be called")

    monkeypatch.setattr(translation, "generate_content", boom)

    assert translation.translate_to_english("आज हवामान कसे आहे") == ("[mr->en]", "mr")


def test_language_id_failure_falls_back_to_gemini(sarvam_env, monkeypatch):
    def failing(text):
        raise sarvam_service.SarvamError("down")

    monkeypatch.setattr(sarvam_service, "identify_language", failing)
    monkeypatch.setattr(
        translation, "generate_content",
        lambda prompt: FakeResponse(text='{"lang": "hi", "english": "weather"}')
    )

    assert translation.translate_to_english("मौसम") == ("weather", "hi")


def test_audio_is_sent_as_is_when_conversion_fails(sarvam_env, monkeypatch):
    sent = {}

    def no_ffmpeg(audio):
        raise FileNotFoundError("ffmpeg not found")

    def fake_stt(audio, mime):
        sent["audio"], sent["mime"] = audio, mime
        return "hello", "en"

    monkeypatch.setattr(speech_service, "to_wav_16k", no_ffmpeg)
    monkeypatch.setattr(sarvam_service, "speech_to_text", fake_stt)

    assert speech_service._sarvam_transcribe(b"webm-bytes", "audio/webm") == ("hello", "en")
    assert sent == {"audio": b"webm-bytes", "mime": "audio/webm"}


def test_converted_wav_is_sent_when_ffmpeg_works(sarvam_env, monkeypatch):
    sent = {}

    monkeypatch.setattr(speech_service, "to_wav_16k", lambda audio: b"WAV16K")
    monkeypatch.setattr(
        sarvam_service, "speech_to_text",
        lambda audio, mime: (sent.update(audio=audio, mime=mime) or ("ok", "hi"))
    )

    speech_service._sarvam_transcribe(b"webm-bytes", "audio/webm")

    assert sent == {"audio": b"WAV16K", "mime": "audio/wav"}


def test_language_is_detected_by_sarvam_not_taken_from_the_hint(sarvam_env, monkeypatch):
    monkeypatch.setattr(speech_service, "_sarvam_transcribe", lambda audio, mime: ("ಹವಾಮಾನ", "kn"))

    # The web app says the UI is English, but the farmer spoke Kannada
    assert speech_service.transcribe(b"audio", "en")["lang"] == "kn"


def test_urdu_and_bhojpuri_have_no_sarvam_voice(sarvam_env, monkeypatch):
    def boom(text, lang):
        raise AssertionError("no voice expected")

    monkeypatch.setattr(sarvam_service, "text_to_speech", boom)

    assert speech_service.synthesize("سلام", "ur") is None
    assert speech_service.synthesize("नमस्कार", "bho") is None
