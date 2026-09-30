import base64

import pytest
import requests

from app.services import sarvam_service


class FakeResponse:
    def __init__(self, status=200, data=None, text=""):
        self.status_code = status
        self._data = data
        self.text = text or str(data)

    def json(self):
        if self._data is None:
            raise ValueError("no json")

        return self._data


@pytest.fixture(autouse=True)
def sarvam_env(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    monkeypatch.delenv("SARVAM_TRANSLATE_MODEL", raising=False)
    monkeypatch.delenv("SARVAM_TTS_MODEL", raising=False)
    monkeypatch.delenv("SARVAM_TTS_SPEAKER", raising=False)
    monkeypatch.setattr(sarvam_service.time, "sleep", lambda seconds: None)


def fake_post(calls, responder):
    def post(url, headers=None, json=None, files=None, data=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json, "files": files, "data": data})

        return responder(url, json)

    return post


# ---------------------------------------------------------------- configuration

def test_not_configured_without_a_key(monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY")

    assert sarvam_service.configured() is False
    assert sarvam_service.translation_supported("hi") is False

    with pytest.raises(sarvam_service.SarvamError, match="not configured"):
        sarvam_service.translate("Hello", "en", "hi")


def test_language_coverage():
    assert sarvam_service.translation_supported("kn", "en")
    assert sarvam_service.translation_supported("ur", "en")          # via sarvam-translate
    assert sarvam_service.translation_supported("as", "en")
    assert not sarvam_service.translation_supported("bho")           # Gemini handles Bhojpuri

    assert sarvam_service.tts_supported("ta")
    assert not sarvam_service.tts_supported("ur")                    # no Urdu voice
    assert not sarvam_service.tts_supported("bho")


def test_language_codes_are_mapped():
    assert sarvam_service.SARVAM_CODES["or"] == "od-IN"              # Sarvam spells Odia "od"
    assert sarvam_service.FROM_SARVAM["od-IN"] == "or"
    assert sarvam_service.FROM_SARVAM["kn-IN"] == "kn"


# ---------------------------------------------------------------- translation

def test_translate_sends_the_documented_request(monkeypatch):
    calls = []
    monkeypatch.setattr(
        requests, "post",
        fake_post(calls, lambda url, body: FakeResponse(data={"translated_text": "ನಮಸ್ಕಾರ"}))
    )

    assert sarvam_service.translate("Hello", "en", "kn") == "ನಮಸ್ಕಾರ"

    call = calls[0]
    assert call["url"] == "https://api.sarvam.ai/translate"
    assert call["headers"] == {"api-subscription-key": "test-key"}
    assert call["json"] == {
        "input": "Hello",
        "source_language_code": "en-IN",
        "target_language_code": "kn-IN",
        "model": "mayura:v1",
    }


def test_model_is_chosen_per_language(monkeypatch):
    assert sarvam_service.translate_model("en", "hi") == "mayura:v1"
    assert sarvam_service.translate_model("en", "ur") == "sarvam-translate:v1"
    assert sarvam_service.translate_model("as", "en") == "sarvam-translate:v1"

    monkeypatch.setenv("SARVAM_TRANSLATE_MODEL", "sarvam-translate:v1")
    assert sarvam_service.translate_model("en", "hi") == "sarvam-translate:v1"


def test_unsupported_pair_is_refused_without_a_request(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("no request expected")

    monkeypatch.setattr(requests, "post", boom)

    with pytest.raises(sarvam_service.SarvamError):
        sarvam_service.translate("Hello", "en", "bho")

    assert sarvam_service.translate("Hello", "en", "en") == "Hello"
    assert sarvam_service.translate("  ", "en", "hi") == "  "


def test_long_text_is_split_at_sentence_ends(monkeypatch):
    calls = []
    monkeypatch.setattr(
        requests, "post",
        fake_post(calls, lambda url, body: FakeResponse(data={"translated_text": f"<{len(body['input'])}>"}))
    )

    sentence = "Water the crop in the evening. "
    text = sentence * 60                                           # ~1860 characters

    result = sarvam_service.translate(text.strip(), "en", "hi")

    assert len(calls) == 2                                          # mayura limit is 1000
    assert all(len(call["json"]["input"]) <= 1000 for call in calls)
    assert all(call["json"]["input"].endswith(".") for call in calls)
    assert result.count("<") == 2


def test_split_text_edge_cases():
    assert sarvam_service.split_text("short", 100) == ["short"]

    hard = sarvam_service.split_text("x" * 250, 100)

    assert [len(piece) for piece in hard] == [100, 100, 50]


def test_translate_many_keeps_the_order(monkeypatch):
    monkeypatch.setattr(
        requests, "post",
        fake_post([], lambda url, body: FakeResponse(data={"translated_text": body["input"].upper()}))
    )

    assert sarvam_service.translate_many(["one", "two", "three", "four", "five"], "en", "hi") == [
        "ONE", "TWO", "THREE", "FOUR", "FIVE"
    ]


# ---------------------------------------------------------------- errors and retries

def test_api_error_message_is_reported_without_the_key(monkeypatch):
    error = {"error": {"message": "Language 'ur-IN' is not supported in mayura:v1", "code": "invalid_request_error"}}
    monkeypatch.setattr(requests, "post", fake_post([], lambda url, body: FakeResponse(400, error)))

    with pytest.raises(sarvam_service.SarvamError) as info:
        sarvam_service.translate("Hello", "en", "hi")

    assert "not supported" in str(info.value)
    assert "test-key" not in str(info.value)


def test_rate_limit_is_retried_once(monkeypatch):
    responses = iter([FakeResponse(429, {"error": {"message": "slow down"}}),
                      FakeResponse(200, {"translated_text": "ok"})])
    calls = []
    monkeypatch.setattr(requests, "post", fake_post(calls, lambda url, body: next(responses)))

    assert sarvam_service.translate("Hello", "en", "hi") == "ok"
    assert len(calls) == 2


def test_client_errors_are_not_retried(monkeypatch):
    calls = []
    monkeypatch.setattr(
        requests, "post",
        fake_post(calls, lambda url, body: FakeResponse(403, {"error": {"message": "invalid key"}}))
    )

    with pytest.raises(sarvam_service.SarvamError, match="403"):
        sarvam_service.translate("Hello", "en", "hi")

    assert len(calls) == 1


def test_network_failure_becomes_sarvam_error(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.ConnectionError("no internet")

    monkeypatch.setattr(requests, "post", boom)

    with pytest.raises(sarvam_service.SarvamError, match="request failed"):
        sarvam_service.translate("Hello", "en", "hi")


def test_invalid_json_becomes_sarvam_error(monkeypatch):
    monkeypatch.setattr(requests, "post", fake_post([], lambda url, body: FakeResponse(200, None, "<html>")))

    with pytest.raises(sarvam_service.SarvamError, match="invalid response"):
        sarvam_service.translate("Hello", "en", "hi")


# ---------------------------------------------------------------- language id

def test_identify_language(monkeypatch):
    monkeypatch.setattr(
        requests, "post",
        fake_post([], lambda url, body: FakeResponse(data={"language_code": "mr-IN", "script_code": "Deva"}))
    )

    assert sarvam_service.identify_language("आज हवामान कसे आहे") == "mr"

    monkeypatch.setattr(
        requests, "post",
        fake_post([], lambda url, body: FakeResponse(data={"language_code": None, "script_code": None}))
    )

    assert sarvam_service.identify_language("???") is None


# ---------------------------------------------------------------- speech to text

def test_speech_to_text_uploads_the_file_and_maps_the_language(monkeypatch):
    calls = []
    monkeypatch.setattr(
        requests, "post",
        fake_post(calls, lambda url, body: FakeResponse(
            data={"transcript": "  ಹವಾಮಾನ ಮೈಸೂರು  ", "language_code": "kn-IN"}))
    )

    text, lang = sarvam_service.speech_to_text(b"RIFFwav", "audio/wav")

    assert (text, lang) == ("ಹವಾಮಾನ ಮೈಸೂರು", "kn")

    call = calls[0]
    assert call["url"] == "https://api.sarvam.ai/speech-to-text"
    assert call["files"]["file"][0] == "voice.wav"
    assert call["files"]["file"][1] == b"RIFFwav"
    assert call["data"]["language_code"] == "unknown"                # auto-detect


def test_speech_to_text_names_the_file_after_its_type(monkeypatch):
    calls = []
    monkeypatch.setattr(
        requests, "post",
        fake_post(calls, lambda url, body: FakeResponse(data={"transcript": "hi", "language_code": "en-IN"}))
    )

    sarvam_service.speech_to_text(b"x", "audio/webm;codecs=opus")

    assert calls[0]["files"]["file"][0] == "voice.webm"


def test_unknown_detected_language_is_none(monkeypatch):
    monkeypatch.setattr(
        requests, "post",
        fake_post([], lambda url, body: FakeResponse(data={"transcript": "x", "language_code": "xx-YY"}))
    )

    assert sarvam_service.speech_to_text(b"x") == ("x", None)


# ---------------------------------------------------------------- text to speech

def test_text_to_speech_returns_wav_bytes(monkeypatch):
    calls = []
    audio = base64.b64encode(b"RIFFWAVE").decode()
    monkeypatch.setattr(requests, "post", fake_post(calls, lambda url, body: FakeResponse(data={"audios": [audio]})))

    assert sarvam_service.text_to_speech("नमस्ते", "hi") == b"RIFFWAVE"

    body = calls[0]["json"]
    assert calls[0]["url"] == "https://api.sarvam.ai/text-to-speech"
    assert body == {"text": "नमस्ते", "target_language_code": "hi-IN"}


def test_tts_model_and_speaker_can_be_chosen(monkeypatch):
    calls = []
    audio = base64.b64encode(b"x").decode()
    monkeypatch.setattr(requests, "post", fake_post(calls, lambda url, body: FakeResponse(data={"audios": [audio]})))
    monkeypatch.setenv("SARVAM_TTS_MODEL", "bulbul:v2")
    monkeypatch.setenv("SARVAM_TTS_SPEAKER", "anushka")

    sarvam_service.text_to_speech("hello", "en")

    assert calls[0]["json"]["model"] == "bulbul:v2"
    assert calls[0]["json"]["speaker"] == "anushka"


def test_tts_long_text_is_cut_at_a_sentence(monkeypatch):
    calls = []
    audio = base64.b64encode(b"x").decode()
    monkeypatch.setattr(requests, "post", fake_post(calls, lambda url, body: FakeResponse(data={"audios": [audio]})))

    sarvam_service.text_to_speech(("Spray in the morning. " * 100).strip(), "en")

    sent = calls[0]["json"]["text"]

    assert len(sent) <= sarvam_service.TTS_LIMIT
    assert sent.endswith(".")


def test_tts_refuses_languages_without_a_voice(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("no request expected")

    monkeypatch.setattr(requests, "post", boom)

    with pytest.raises(sarvam_service.SarvamError, match="no ur voice"):
        sarvam_service.text_to_speech("سلام", "ur")


def test_empty_audio_list_is_an_error(monkeypatch):
    monkeypatch.setattr(requests, "post", fake_post([], lambda url, body: FakeResponse(data={"audios": []})))

    with pytest.raises(sarvam_service.SarvamError):
        sarvam_service.text_to_speech("hello", "en")
